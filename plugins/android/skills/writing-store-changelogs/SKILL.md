---
name: writing-store-changelogs
description: Writes the app-store release notes ("What's new") for one Android version as changelog files named after its versionCode in a fastlane-style metadata tree (fastlane/metadata/android), within the limits and content rules of Google Play, F-Droid, RuStore and Huawei AppGallery. Use when preparing an Android release and the user asks for release notes, what's new, a store changelog, or "что нового" for the stores. Not for editing CHANGELOG.md, GitHub release notes, or store descriptions.
---

# Writing store changelogs

Store release notes live in `fastlane/metadata/android/<locale>/changelogs/<versionCode>.txt`. Google Play tools, F-Droid and RuStore tools all read this one tree, and AppGallery gets the same text pasted in, so write there and never make a per-store copy. If the project has no such tree yet, read [references/new-metadata-tree.md](references/new-metadata-tree.md).

Find the version, the changes and the style as usual: earlier entries, CHANGELOG.md, git log since the previous release tag of the same series. These points are easy to miss:

- **Notes that already exist.** If CHANGELOG.md or a release-notes file covers this version, take the facts and wording from it. If a CI workflow generates the changelog files from it (a script in `.github/workflows/` that writes `changelogs/`), tell the user the bot will write them; if they still want the files now, match the generator's output exactly.
- **Several files per release.** ABI splits or flavors can give one release several versionCodes (Fossify writes `40.txt` ... `44.txt` for base code 40). Repeat the previous release's set of files with the same text.
- **Locales.** Write only the locales the maintainers write by hand. If `git log` shows that earlier files in other locales came from Weblate or Crowdin ("Translated using Weblate"), leave those locales to the translators and say so.
- **Dependency releases.** When a release is mostly an update of a library the app is built on (an extractor, an engine), that update is the release: read the library's release notes or ask the user, instead of dropping it as a routine bump.
- **Existing file.** If the file for this versionCode already exists, the version probably shipped with it: ask before overwriting.
- **Formatting.** Keep the bullet character and the trailing newline (or its absence) of the most recent entry.

## Store rules

- **Length:** 500 characters per language in Google Play, F-Droid and AppGallery; 5000 in RuStore.
- **Concrete, user-visible changes.** RuStore asks for this explicitly and questions repeated generic text; "Updated translations" is fine when it is true.
- **No issue numbers or tracker keys** (`#123`, `APP-45`): RuStore moderation rejects internal codes.
- **No promotion or calls to action** ("rate us", sales): Google Play forbids them in release notes.
- **No links,** except one to a detailed changelog: RuStore rejects unrelated links.
- **Plain text only:** stores show HTML and Markdown as is.

## Check

```bash
python3 <skill-dir>/scripts/check_changelogs.py <tree> <code>[,<code>...] --locales <locales written> [--stores play,fdroid,rustore,appgallery]
```

`<skill-dir>` is this skill's directory. The script counts characters, not bytes (`wc -m` in the C locale counts bytes and doubles Cyrillic), and flags HTML, issue numbers and links. Fix every `FAIL`; fix each `warn` or tell the user why it stays. Show the texts to the user for approval; do not commit.
