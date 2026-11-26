#!/usr/bin/env python3
"""Check rendered frames against store rules.

    check.py <series.json | workdir>

Give the series file (or the folder holding out/render-report.json from render.py). Prints one line per finding and a summary; exit 0 when there is no FAIL, 1 with FAILs,
2 when there is nothing to check. Store rules: references/store-rules.md.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from targets import STORE_LIMITS, TARGETS  # noqa: E402

CAPTION_AREA_MAX = 0.20  # Play: taglines should not take up more than 20 % of the image.
CONTRAST_FAIL, CONTRAST_WARN = 3.0, 4.5  # WCAG large text / normal text.
CUTOFF = 0.05  # Store UI may cover the top and bottom 5 % of an image.
UPSCALE_WARN = 1.5  # Beyond this a shot looks soft.
ALT_MAX = 140  # Play: alt text of 140 characters or less.
TEXT_PIXEL_DISTANCE = 60  # RGB distance under which a pixel counts as caption text, not background.
STORE_NAMES = {"appstore": "App Store", "play": "Play", "rustore": "RuStore", "appgallery": "AppGallery",
               "fdroid": "F-Droid"}

# Play metadata policy and App Store 2.3: no ranking, price, promotion, "new" or calls to action.
# FAIL: claims that are almost never innocent. warn: words that are often innocent ("new note", "on top of").
BANNED_FAIL = [
    r"\bbest\b", r"#\s?1\b", r"\bno\.?\s?1\b", r"№\s?1\b", r"\bsale\b", r"\bdiscount", r"\bmillions?\b",
    r"\b(download|install|play|try|get it|get the app)\s+(now|today)\b", r"\beditor'?s choice\b",
    r"\bapp of the year\b", r"\baward", r"\blimited time\b", r"\d+\s?%\s?off\b",
    r"\bлучш", r"\bбесплатн", r"\bскидк", r"\bраспродаж", r"\bмиллион",
    r"\b(скача|установи|загрузи)\w*\s+(сейчас|сегодня|бесплатно)\b", r"\bвыбор редакции\b",
]
# "free" is a price claim except in fixed phrases.
FREE = re.compile(r"(?<![-\w])free\b(?!\s+(up|of|from)\b)")
BANNED_WARN = [r"\bnew\b", r"\btop\b(?!\s+of\b)", r"\bнов(ый|ая|ое|ые|инк)\w*", r"\bтоп\b"]
PRICE = re.compile(r"\d+([.,]\d+)?\s?(₽|\$|€|£|руб)|[₽$€£]\s?\d")
RTL_OR_COMPLEX = ("ar", "he", "fa", "ur", "zh", "ja", "ko", "th", "hi")


@dataclass
class Finding:
    level: str  # "FAIL" or "warn"
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level} {self.where}: {self.message}"


def file_size(path: Path) -> int:
    return path.stat().st_size


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _contrast(a: tuple, b: tuple) -> float:
    def lum(rgb):
        def ch(v):
            c = v / 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b_ = (ch(v) for v in rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _background_under(img, box, text_rgb) -> tuple[int, int, int] | None:
    x, y, w, h = (int(v) for v in box)
    region = img.convert("RGB").crop((max(0, x), max(0, y), min(img.width, x + w), min(img.height, y + h)))
    region.thumbnail((120, 120))
    raw = region.tobytes()
    pixels = [p for p in (tuple(raw[i : i + 3]) for i in range(0, len(raw), 3))
              if sum((a - b) ** 2 for a, b in zip(p, text_rgb)) ** 0.5 > TEXT_PIXEL_DISTANCE]
    if not pixels:
        return None
    return tuple(int(statistics.median(p[i] for p in pixels)) for i in range(3))


def _caption_findings(text: str, locale: str, where: str) -> list[Finding]:
    """Captions mix languages, so every language's patterns apply to every caption."""
    low = text.lower()
    m = next((m for m in (re.search(p, low) for p in BANNED_FAIL) if m), None) or FREE.search(low)
    if m:
        return [Finding("FAIL", where, f'caption "{text}" has "{m.group(0)}": stores forbid ranking, price, promotion '
                                       "and calls to action; rewrite it as a benefit")]
    if PRICE.search(text):
        return [Finding("FAIL", where, f'caption "{text}" has a price (App Store 2.3.7, Play metadata policy)')]
    m = next((m for m in (re.search(p, low) for p in BANNED_WARN) if m), None)
    if m:
        return [Finding("warn", where, f'caption "{text}" has "{m.group(0)}": fine as a feature ("new note"), '
                                       'not as a claim ("New!", "Top app"); check the context')]
    return []


def run(workdir: Path) -> list[Finding]:
    from PIL import Image

    out = Path(workdir) / "out"
    report = json.loads((out / "render-report.json").read_text(encoding="utf-8"))
    findings: list[Finding] = []
    groups: dict[tuple, list[dict]] = {}
    for fr in report["frames"]:
        groups.setdefault((fr["target"], tuple(fr["size"]), fr["locale"]), []).append(fr)

    locales = sorted({fr["locale"] for fr in report["frames"]})
    for loc in locales:
        lang = loc.split("-")[0].lower()
        if lang not in ("en", "ru"):
            findings.append(Finding("warn", loc, "the banned-word list covers en and ru only; check captions by eye"))
        if lang in RTL_OR_COMPLEX:
            findings.append(Finding("warn", loc, "right-to-left or complex script: check glyphs and alignment by eye"))

    for (target_name, size, locale), frames in groups.items():
        target = TARGETS[target_name]
        w, h = size
        where_group = f"{target_name}/{w}x{h}/{locale}"
        if target_name != "feature-graphic":
            n = len(frames)
            low = [s for s in target.stores if n < max(STORE_LIMITS[s].min_frames, target.min_frames)]
            high = [s for s in target.stores if n > min(STORE_LIMITS[s].max_frames, target.max_frames)]
            if low:
                findings.append(Finding("FAIL", where_group, f"{n} frames; " + " and ".join(
                    STORE_NAMES[s] for s in low) + f" need at least {target.min_frames}"))
            if high:
                findings.append(Finding("FAIL", where_group, f"{n} frames; " + " and ".join(
                    STORE_NAMES[s] for s in high) + f" allow at most {target.max_frames}"))

        slices = []
        for fr in frames:
            path = out / fr["file"]
            where = fr["file"]
            with Image.open(path) as img:
                img.load()
                if img.size != (w, h):
                    findings.append(Finding("FAIL", where, f"is {img.size[0]}x{img.size[1]}, {target_name} needs {w}x{h}"))
                if img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info:
                    findings.append(Finding("FAIL", where, "has an alpha channel; stores reject transparency "
                                                           "(re-render: render.py saves RGB)"))
                for store in target.stores:
                    lim = STORE_LIMITS[store]
                    side_lo, side_hi = min(img.size), max(img.size)
                    if side_lo < lim.min_side or side_hi > lim.max_side or side_hi / side_lo > lim.max_ratio:
                        findings.append(Finding("FAIL", where, f"{img.size[0]}x{img.size[1]} is outside "
                                                               f"{STORE_NAMES[store]}'s size or ratio limits"))
                size_b = file_size(path)
                if size_b > target.max_bytes:
                    findings.append(Finding("FAIL", where, f"{size_b // 1024} KB is over {target.max_bytes // 1024} KB "
                                                           f"({', '.join(STORE_NAMES[s] for s in target.stores)})"))
                rgb = img.convert("RGB")
                slices.append(rgb)
                for cap in fr["captions"]:
                    findings += _caption_findings(cap["text"], locale, where)
                    cx, cy, cw, ch = cap["box"]
                    if cw * ch > CAPTION_AREA_MAX * w * h:
                        findings.append(Finding("FAIL", where, f"caption covers {cw * ch / (w * h):.0%} of the image; "
                                                               "Play allows 20 % — shorten it"))
                    if target_name != "feature-graphic" and (cy < CUTOFF * h or cy + ch > (1 - CUTOFF) * h):
                        findings.append(Finding("warn", where, "caption reaches into the top or bottom 5 %, which "
                                                               "store UI may cover"))
                    text_rgb = _hex_rgb(cap["color"])
                    bg = _background_under(rgb, cap["box"], text_rgb)
                    if bg:
                        ratio = _contrast(text_rgb, bg)
                        if ratio < CONTRAST_FAIL:
                            findings.append(Finding("FAIL", where, f"caption contrast {ratio:.1f}:1 is below 3:1"))
                        elif ratio < CONTRAST_WARN:
                            findings.append(Finding("warn", where, f"caption contrast {ratio:.1f}:1 is below 4.5:1"))
                    if cap.get("max_bottom") is not None and cy + ch > cap["max_bottom"] + 1:
                        findings.append(Finding("FAIL", where, f'caption "{cap["text"]}" runs into the devices; '
                                                               "shorten it"))
                    if cap.get("overflow"):
                        findings.append(Finding("FAIL", where, f'caption "{cap["text"]}" does not fit its box'))
                    elif cap.get("broken_word"):
                        findings.append(Finding("warn", where, f'a word in "{cap["text"]}" is broken across lines; '
                                                               "use a shorter word"))
                if target_name != "feature-graphic" and not fr["shots"]:
                    findings.append(Finding("FAIL", where, "no shot on this frame; every frame must show the app's UI"))
                for shot in fr["shots"]:
                    if shot.get("scale", 1) > UPSCALE_WARN:
                        findings.append(Finding("warn", where, f"{shot['path']} is upscaled {shot['scale']:.1f}x and "
                                                               "will look soft; capture it at a higher resolution"))
                    if target.platform == "ios" and shot.get("platform") == "android":
                        findings.append(Finding("FAIL", where, f"{shot['path']} is an Android shot in an App Store "
                                                               "set (Apple 2.3.10)"))

        canvas_path = out / target_name / f"{w}x{h}" / locale / "canvas.png"
        if canvas_path.is_file() and slices:
            with Image.open(canvas_path) as canvas:
                joined = Image.new("RGB", (w * len(slices), h))
                for i, s in enumerate(slices):
                    joined.paste(s, (i * w, 0))
                lossless = all(str(fr["file"]).endswith(".png") for fr in frames)
                if lossless and (canvas.size != joined.size or canvas.convert("RGB").tobytes() != joined.tobytes()):
                    findings.append(Finding("FAIL", where_group, "frames do not tile the canvas: borders will not "
                                                                 "meet in the store; re-render"))

    for loc in locales:
        alt = out / f"alt-text.{loc}.txt"
        if not alt.is_file():
            findings.append(Finding("warn", loc, "no alt text file; Play asks for alt text of up to 140 characters"))
            continue
        for line in alt.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            num, _, text = line.partition(":")
            text = text.strip()
            if len(text) > ALT_MAX:
                findings.append(Finding("FAIL", f"{alt.name}:{num}", f"alt text is {len(text)} characters; Play "
                                                                     "allows 140"))
            if re.match(r"(image|photo|picture) of\b", text, re.I):
                findings.append(Finding("FAIL", f"{alt.name}:{num}", 'alt text starts with "image of"/"photo of"'))
    return findings


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    workdir = Path(args[0])
    if workdir.suffix == ".json" and workdir.is_file():  # the series file: its output.workdir
        import series

        try:
            workdir, _root = series.output_dirs(series.load(workdir), workdir)
        except series.SeriesError as e:
            print(f"FAIL {e}", file=sys.stderr)
            return 2
    if not (workdir / "out/render-report.json").is_file():
        print(f"no {workdir / 'out/render-report.json'}: run render.py first (the workdir is the series' "
              "output.workdir, e.g. store/screenshots)", file=sys.stderr)
        return 2
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow is missing: .venv/bin/pip install pillow", file=sys.stderr)
        return 2
    findings = run(workdir)
    for f in sorted(findings, key=lambda f: (f.level != "FAIL", f.where)):
        print(f)
    fails = sum(f.level == "FAIL" for f in findings)
    print(f"{fails} FAIL, {len(findings) - fails} warn")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
