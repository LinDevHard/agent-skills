#!/usr/bin/env python3
"""Check store changelogs for one versionCode in a fastlane-style metadata tree.

Usage:
    python3 check_changelogs.py <metadata-dir> <versionCode> [--stores play,fdroid,rustore,appgallery]

For every locale directory in <metadata-dir> it checks that
<locale>/changelogs/<versionCode>.txt exists, is UTF-8, is not empty,
contains no HTML tags, and fits the release-notes limit of every selected
store. Lengths are counted in characters, not bytes, so Cyrillic and other
non-ASCII text is measured correctly.

It also flags content that store moderation rejects or questions:
issue references such as "#123" (a FAIL when RuStore is selected, a warning
otherwise), tracker keys such as "APP-123", and links (warnings: a link to a
detailed changelog is allowed, anything else is not).

Exit codes:
    0  every locale passes (warnings may still be printed)
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
    # Google Play Console Help, "Prepare and roll out a release" (answer/9859348):
    # "up to 500 Unicode characters per language".
    "play": ("Google Play", 500),
    # F-Droid docs, "All About Descriptions, Graphics, and Screenshots":
    # changelogs/<versionCode>.txt, "max 500 chars".
    "fdroid": ("F-Droid", 500),
    # RuStore API, "Create draft version": whatsNew "Maximum length — 5000 characters".
    "rustore": ("RuStore", 5000),
    # AppGallery Connect Help, "Releasing an App (APK)": New features
    # "with up to 500 characters", set per language.
    "appgallery": ("Huawei AppGallery", 500),
}

# A "<" followed by an optional "/" and a letter: catches <b>, </p>, <br/>,
# but not plain text such as "<5%" or "a < b".
HTML_TAG = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")

# "#123": an issue or pull request number. RuStore moderation rejects internal
# codes like "исправили ошибку #21134" (RuStore developer blog on "Что нового").
ISSUE_NUMBER = re.compile(r"(?<![\w&])#\d+\b")

# "APP-123": a tracker key. Two or more digits, so "UTF-8" and "H-2" do not match.
TRACKER_KEY = re.compile(r"\b[A-Z][A-Z0-9]+-\d{2,}\b")

# Links. RuStore allows only a link to the developer's detailed changelog.
LINK = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)


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


def check_text(body, limits, stores):
    """Return (problems, warnings) for one changelog text."""
    problems, warnings = [], []
    length = len(body)

    if length == 0:
        problems.append("empty")
    # Group stores that share a limit, so one overflow is reported once.
    stores_by_limit = {}
    for name, limit in limits:
        stores_by_limit.setdefault(limit, []).append(name)
    for limit in sorted(stores_by_limit):
        if length > limit:
            over = length - limit
            names = ", ".join(stores_by_limit[limit])
            problems.append(f"{over} character{'s' if over != 1 else ''} over the {limit}-character limit ({names})")

    tag = HTML_TAG.search(body)
    if tag:
        problems.append(f"HTML tag '{tag.group(0)}': stores show release notes as plain text")

    issue = ISSUE_NUMBER.search(body)
    if issue:
        message = f"issue number '{issue.group(0)}': internal codes mean nothing to users"
        if "rustore" in stores:
            problems.append(message + " and RuStore moderation rejects them")
        else:
            warnings.append(message)

    key = TRACKER_KEY.search(body)
    if key:
        warnings.append(f"looks like a tracker key '{key.group(0)}': remove it unless it is a product name")

    link = LINK.search(body)
    if link:
        warnings.append(f"link '{link.group(0)}': keep it only if it points to a detailed changelog")

    return problems, warnings


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
        problems, warnings = check_text(body, limits, stores)

        status = "FAIL " + "; ".join(problems) if problems else "ok"
        print(f"{locale_dir.name}: {len(body)}/{strictest} {status}")
        for warning in warnings:
            print(f"{locale_dir.name}: warn {warning}")
        failed = failed or bool(problems)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
