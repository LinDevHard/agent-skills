---
name: writing-store-changelogs
description: Writes the app-store release notes ("What's new") for one Android version as changelog files named after its versionCode in a fastlane-style metadata tree (fastlane/metadata/android), matching the style of earlier entries and the limits and content rules of Google Play, F-Droid, RuStore and Huawei AppGallery. Use when preparing an Android release and the user asks for release notes, what's new, a store changelog, or "что нового" for the stores. Not for editing CHANGELOG.md, GitHub release notes, or store descriptions.
---

# Writing store changelogs

Writes `<locale>/changelogs/<versionCode>.txt` for one release. Google Play tools, F-Droid and RuStore tools all read these files, and the same text can be pasted into AppGallery, so one set of texts serves every store.

Out of scope: changing `versionCode`, editing `CHANGELOG.md` or GitHub releases, editing titles or descriptions, publishing, committing.

```
- [ ] 1. Metadata tree, versionCode(s) and locales found
- [ ] 2. No existing changelog for this release (or the user chose to revise it)
- [ ] 3. User-facing changes collected
- [ ] 4. Style read from earlier entries
- [ ] 5. Drafts written, primary locale first
- [ ] 6. Check script passes
- [ ] 7. User approved the texts
- [ ] 8. Files reported to the user
```

## 1. Find the tree, versionCode(s) and locales

**Tree:** the first that exists of `fastlane/metadata/android/`, `metadata/`, `src/*/fastlane/metadata/android/`. If none exists, read [references/new-metadata-tree.md](references/new-metadata-tree.md) before going on.

**versionCode:** what the user said; otherwise the app module's `versionCode`. When the build file assigns a name rather than a number (`versionCode = baseVersionCode`, `NEWPIPE_VERSION_CODE`), follow it to where it is defined: often `VERSION_CODE` in `gradle.properties`, or a constant in `buildSrc/` or `build-logic/`. If it is computed from git, CI or a script, ask the user for the number.

**Files per release:** look at the files of the previous release, not only its number. Some projects write one identical file per ABI or flavor code: Fossify writes `40.txt` ... `44.txt` for base code 40 plus ABI offsets. Confirm the offsets in the build file (`abiCodes`, `versionCodeOverride`, a flavor's `versionCode`) and write the same set for this release. A tree that holds two apps (a phone and a Wear OS app with separate code ranges) gets files only for the app being released.

**Locales:** write the primary locale (`en-US` if present, otherwise the one with the most history) plus every locale that has a changelog for the previous release. Projects translated in Weblate or Crowdin add the other locales after the release, so leave those to the translators. If the user asks for more locales, write them too.

## 2. Check for an existing changelog

If the file for this versionCode already exists in any locale, the version was probably released with it. Do not overwrite it. Show it and ask: revise this text, or will the user bump `versionCode` first?

## 3. Collect the changes

**First look for notes the project already wrote.** If `CHANGELOG.md`, `docs/` or a release-notes file has a section for this version, take the facts and wording from there, and use git only to check them. Earlier store changelogs that copy `CHANGELOG.md` word for word mean the project wants the same text.

Otherwise read git. Find the previous release tag of the same series, since some repos tag several apps (`v2.46.0` for the phone, `v1.1.0-wearos` for the watch):

```bash
git describe --tags --abbrev=0                      # last tag; HEAD's own tag if HEAD is tagged
git tag --sort=-v:refname --list '<pattern>'        # e.g. 'v2.*': pick the one before this release
```

If there are no tags, ask which commit to start from.

Read the range in two passes, so a large one (hundreds of commits) stays cheap:

1. Subjects only: `git log --first-parent --format='%h %s%n    %b' <prev-tag>..HEAD | grep -v '^\s*$'`. `--first-parent` shows one entry per merged pull request instead of every commit inside it, and the body line carries the PR title that GitHub's "Merge pull request #N from …" subjects leave out. Pick the candidates by reading the list yourself; do not filter it with keyword greps, which drop real fixes such as "Update grid spacing to fix #732".
2. Full message only for the candidates: `git show --no-patch <hash>`.

Keep only what a user of the app would notice: features, visible fixes, behaviour changes. Drop refactoring, CI, tests, translations-only commits and the release commit itself. Add anything the user mentions that is not in git.

Two cases need more than git:

- **The release is mostly a dependency update** of a library the app is built on (an extractor, an engine, an SDK). That update is the release. Read the library's release notes if you have network access, or ask the user what it fixes; do not drop it as a routine bump.
- **Nothing user-facing is left.** If only translations changed, "Updated translations" is a true and normal entry. Otherwise say so and offer a short neutral line ("Stability improvements"), instead of inventing features.

Before naming a feature, make sure it ships in this release: it is wired into the app (navigation, the production build, not a debug or demo flavor), not only added as code.

## 4. Read the style

For each locale you will write, read its 2-3 most recent changelogs and its `short_description.txt` (skip it if it does not exist). Note length, tone, sentence or bullet form and the bullet character, verb form ("Added ...", "Добавлены ..."), how features are named, and whether files end with a newline. The new entry should read as if the same person wrote it.

## 5. Write the drafts

Write the primary locale first. Write each other locale from the same facts in that locale's own earlier style: not a word-for-word translation. Write every file of the release (step 1) with the same text per locale. Keep the earlier files' trailing newline, or its absence.

Store moderation has a few content rules. They hold in every store, so follow them even for a store the user did not name:

- **Concrete, user-visible changes.** "Fixed a crash on Android 12 at startup", not "bug fixes and stability improvements" in every release. RuStore asks for this explicitly.
- **No issue numbers or tracker keys** (`#123`, `APP-45`). Commit messages are full of them; strip them. RuStore moderation rejects internal codes.
- **No promotion or calls to action**: no sales, "rate us", "update now". Google Play forbids using release notes for promotion or to solicit user actions.
- **No links**, except one to a detailed changelog if the user wants it. RuStore rejects links unrelated to the update.
- **Plain text only**: no HTML or Markdown. Stores show the text as is.
- **Only this release.** No notes for moderators, no text carried over from an earlier version (a repeated "Updated translations" is fine when it is true again).

When a draft is too long, drop the least important points; never cut a sentence in the middle.

## 6. Check

Write the drafts to their final paths, then run:

```bash
python3 <skill-dir>/scripts/check_changelogs.py <tree> <code>[,<code>...] --locales <the locales you wrote> [--stores play,fdroid,rustore,appgallery]
```

- `<skill-dir>` is this skill's directory.
- Pass every versionCode of the release (`50,51,52,53,54`); the script also warns when their texts differ.
- Pass `--locales` with exactly the locales you wrote, so a missing file in one of them fails.
- Pass `--stores` only when the user named the stores. By default every known store is checked, which means the strictest limit (500 characters per language).

The script counts characters, not bytes, so Cyrillic is measured correctly, and it flags HTML, issue numbers and links. Fix every `FAIL` and run it again until it exits with 0. For each `warn` line, fix it or tell the user why it stays (for example, a tracker-like word that is really a product name).

If `python3` is missing, count lengths with a tool that counts characters (not `wc -m` in the C locale, which counts bytes) and say the script did not run.

## 7. Show and confirm

Show every locale's text with its length from the script output, and the list of files. Ask about the locales you left to translators if the project has many. Apply the user's edits and run the check again. Only an approved text stays on disk; if the user drops the change, delete the files you created.

## 8. Report

List the files written and the locales left to translators. Remind the user to commit the files; release tooling and the publishing skills read them from there.
