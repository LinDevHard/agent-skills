#!/usr/bin/env python3
"""Copy rendered frames into the project's listing tree.

    place.py <series.json | workdir> [--project-root DIR] [--layout auto|fastlane|triple-t] [--force] [--dry-run]

<workdir> holds out/ from render.py. Android goes to fastlane/metadata/android/<locale>/images/ (or Triple-T
<module>/src/main/play/listings/<locale>/graphics/ when the project has one), iOS to
fastlane/screenshots/<locale>/ where deliver tells devices apart by pixel size. Existing files are never
overwritten without --force, and files the series did not write are never deleted. Exit 0 ok, 1 conflicts,
2 nothing to place.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

FASTLANE_ANDROID = {
    "android-phone": "phoneScreenshots",
    "android-tablet-7": "sevenInchScreenshots",
    "android-tablet-7-landscape": "sevenInchScreenshots",
    "android-tablet-10": "tenInchScreenshots",
    "android-tablet-10-landscape": "tenInchScreenshots",
}
TRIPLE_T = {
    "android-phone": "phone-screenshots",
    "android-tablet-7": "tablet-screenshots",
    "android-tablet-7-landscape": "tablet-screenshots",
    "android-tablet-10": "large-tablet-screenshots",
    "android-tablet-10-landscape": "large-tablet-screenshots",
}
MANUAL = {"android-foldable", "android-foldable-outer"}  # no folder in fastlane or Triple-T


def _plan(out: Path, root: Path, layout: str) -> tuple[list[tuple[Path, Path]], list[str], list[str]]:
    """(copies, conflicts-of-structure, notes)."""
    copies, problems, notes = [], [], []
    module = None
    if layout in ("auto", "triple-t"):
        found = sorted(root.glob("*/src/main/play/listings"))
        if found:
            module = found[0].parents[3]
        elif layout == "triple-t":
            problems.append("no <module>/src/main/play/listings found for --layout triple-t")
    used_dirs: dict[tuple[str, str], str] = {}
    # Only what the last render wrote (and check.py saw): stale folders in out/ are ignored.
    report = json.loads((out / "render-report.json").read_text(encoding="utf-8"))
    groups: dict[tuple[str, str, str], list[Path]] = {}
    for fr in report["frames"]:
        key = (fr["target"], f'{fr["size"][0]}x{fr["size"][1]}', fr["locale"])
        groups.setdefault(key, []).append(out / fr["file"])
    for (target, size_name, locale), files in sorted(groups.items()):
        loc_dir = out / target / size_name / locale
        frames = sorted(f for f in files if f.is_file())
        if not frames:
            problems.append(f"{loc_dir}: the report lists files that are gone; re-render")
            continue
        if target in MANUAL:
            notes.append(f"{target} {size_name} {locale}: no listing folder exists for foldables; "
                         f"upload {loc_dir} by hand in Play Console (Store listing > Foldables)")
            continue
        if target.startswith("ios-"):
            dest = root / "fastlane/screenshots" / locale
            copies += [(f, dest / f"{f.stem}_{size_name}{f.suffix}") for f in frames]
            continue
        if target == "feature-graphic":
            if module:
                dest = module / "src/main/play/listings" / locale / "graphics/feature-graphic"
                copies += [(frames[0], dest / f"1{frames[0].suffix}")]
            else:
                dest = root / "fastlane/metadata/android" / locale / "images"
                copies += [(frames[0], dest / f"featureGraphic{frames[0].suffix}")]
            continue
        folder = (TRIPLE_T if module else FASTLANE_ANDROID).get(target)
        if not folder:
            notes.append(f"{target}: no listing folder known; left in {loc_dir}")
            continue
        key = (folder, locale)
        if key in used_dirs and used_dirs[key] != target:
            problems.append(f"{used_dirs[key]} and {target} both go to {folder} ({locale}); Play takes one "
                            "set per device type: keep one orientation (drop the other target or its out/ folder)")
            continue
        used_dirs[key] = target
        if module:
            dest = module / "src/main/play/listings" / locale / "graphics" / folder
        else:
            dest = root / "fastlane/metadata/android" / locale / "images" / folder
        copies += [(f, dest / f"{int(f.stem)}{f.suffix}") for f in frames]
    return copies, problems, notes


def _slot_files(dest: Path) -> list[Path]:
    """Existing files in the same numbered slot, whatever their extension (1.jpg blocks 1.png)."""
    if not dest.parent.is_dir():
        return []
    return [p for p in dest.parent.iterdir() if p.stem == dest.stem and p.suffix.lower() in (".png", ".jpg", ".jpeg")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Copy rendered frames into the listing tree.")
    ap.add_argument("workdir", help="the series.json (preferred) or the folder holding out/")
    ap.add_argument("--project-root", help="default: the nearest folder above the workdir with settings.gradle, "
                    "*.xcodeproj, fastlane or .git")
    ap.add_argument("--layout", choices=("auto", "fastlane", "triple-t"), default="auto")
    ap.add_argument("--force", action="store_true", help="replace files in the slots this series fills")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import series

    workdir = Path(args.workdir)
    root = None
    if workdir.suffix == ".json" and workdir.is_file():  # the series file: its output.workdir and project_root
        workdir, root = series.output_dirs(series.load(workdir), workdir)
    out = workdir / "out"
    if args.project_root:
        root = Path(args.project_root).resolve()
    root = root or series.find_project_root(workdir)
    print(f"project root: {root}")
    if not (out / "render-report.json").is_file():
        print(f"no {out / 'render-report.json'}: run render.py first", file=sys.stderr)
        return 2

    copies, problems, notes = _plan(out, root, args.layout)
    for p in problems:
        print(f"FAIL {p}")
    conflicts = [(src, dest, old) for src, dest in copies for old in _slot_files(dest)]
    if conflicts and not args.force:
        for _src, dest, old in conflicts:
            print(f"FAIL {old.relative_to(root)} already exists (slot of {dest.name})")
        print("nothing copied: look at the existing files, then rerun with --force to replace those slots")
        return 1
    if problems:
        print("nothing copied")
        return 1

    for src, dest, old in conflicts:
        if not args.dry_run:
            old.unlink()
    written_dirs = set()
    for src, dest in copies:
        verb = "would copy" if args.dry_run else "copy"
        print(f"{verb} {src.relative_to(out.parent)} -> {dest.relative_to(root)}")
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        written_dirs.add(dest.parent)
    ours = {dest for _, dest in copies}
    for d in sorted(written_dirs):
        if not d.is_dir():
            continue
        extra = sorted(p.name for p in d.iterdir()
                       if p.suffix.lower() in (".png", ".jpg", ".jpeg") and p not in ours)
        if extra and d.name != "images":
            print(f"note {d.relative_to(root)} also has {', '.join(extra)} from before; they will upload too "
                  "unless you delete them")
    for n in notes:
        print(f"note {n}")
    print(f"{'planned' if args.dry_run else 'placed'} {len(copies)} files; nothing committed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
