#!/usr/bin/env python3
"""Check store changelogs for one versionCode in a fastlane-style metadata tree.

Usage:
    python3 check_changelogs.py <metadata-dir> <versionCode> [--stores play,fdroid,rustore]

For every locale directory in <metadata-dir> it checks that
<locale>/changelogs/<versionCode>.txt exists, is UTF-8, is not empty,
contains no HTML tags, and fits the release-notes limit of every selected
store. Lengths are counted in characters, not bytes, so Cyrillic and other
non-ASCII text is measured correctly.

Exit codes:
    0  every locale passes
    1  at least one locale fails a check
    2  bad input (missing directory, bad versionCode, unknown store)

Standard library only.
"""

import argparse
import re
import sys
from pathlib import Path

# Release-notes ("What's new") limits in characters, per store.
STORE_LIMITS = {
    # Google Play Console: release notes are limited to 500 characters per language.
    "play": ("Google Play", 500),
    # F-Droid docs (All About Descriptions, Graphics, and Screenshots): changelogs max 500 chars.
    "fdroid": ("F-Droid", 500),
    # RuStore API, create draft version: whatsNew is limited to 5000 characters.
    "rustore": ("RuStore", 5000),
}

# A "<" followed by an optional "/" and a letter: catches <b>, </p>, <br/>,
# but not plain text such as "<5%" or "a < b".
HTML_TAG = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("metadata_dir", type=Path, help="e.g. fastlane/metadata/android")
    parser.add_argument("version_code", help="Android versionCode, e.g. 6")
    parser.add_argument(
        "--stores",
        default=",".join(STORE_LIMITS),
        help="comma-separated stores to check against (default: all known: %(default)s)",
    )
    return parser.parse_args(argv)


def fail_input(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def main(argv):
    args = parse_args(argv)

    if not args.version_code.isdigit() or int(args.version_code) <= 0:
        fail_input(f"versionCode must be a positive integer, got '{args.version_code}'")
    # Changelog files are named by the literal versionCode, with no zero padding.
    version_code = str(int(args.version_code))

    stores = [s.strip().lower() for s in args.stores.split(",") if s.strip()]
    unknown = [s for s in stores if s not in STORE_LIMITS]
    if unknown or not stores:
        fail_input(
            f"unknown store(s): {', '.join(unknown) or '(none given)'}. "
            f"Known stores: {', '.join(STORE_LIMITS)}"
        )

    root = args.metadata_dir
    if not root.is_dir():
        fail_input(f"metadata directory not found: {root}")

    locales = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not locales:
        fail_input(f"no locale directories (such as en-US) in {root}")

    limits = [STORE_LIMITS[s] for s in stores]
    strictest = min(limit for _, limit in limits)
    print(f"versionCode {version_code}, stores: {', '.join(name for name, _ in limits)}")

    failed = False
    for locale_dir in locales:
        path = locale_dir / "changelogs" / f"{version_code}.txt"
        rel = path.relative_to(root)
        problems = []

        if not path.is_file():
            print(f"{locale_dir.name}: FAIL missing {rel}")
            failed = True
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            print(f"{locale_dir.name}: FAIL {rel} is not valid UTF-8 ({exc.reason} at byte {exc.start})")
            failed = True
            continue

        # Trailing whitespace and the final newline are not shown by the stores.
        body = text.rstrip()
        length = len(body)

        if length == 0:
            problems.append("empty")
        for name, limit in limits:
            if length > limit:
                over = length - limit
                problems.append(f"{over} character{'s' if over != 1 else ''} over the {name} limit of {limit}")
        tag = HTML_TAG.search(body)
        if tag:
            problems.append(f"contains an HTML tag '{tag.group(0)}'; stores show release notes as plain text")

        status = "FAIL " + "; ".join(problems) if problems else "ok"
        print(f"{locale_dir.name}: {length}/{strictest} {status}")
        failed = failed or bool(problems)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
