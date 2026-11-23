---
name: writing-store-changelogs
description: Writes the app-store release notes ("What's new") for one Android version as a changelog file named after its versionCode in every locale of a fastlane-style metadata tree (fastlane/metadata/android), matching the style of earlier entries and the limits and content rules of Google Play, F-Droid, RuStore and Huawei AppGallery. Use when preparing an Android release and the user asks for release notes, what's new, a store changelog, or "что нового" for the stores. Not for CHANGELOG.md, GitHub release notes, or store descriptions.
---

# Writing store changelogs

Writes `<locale>/changelogs/<versionCode>.txt` for one version, in every locale the project already has. Google Play tools, F-Droid and RuStore tools all read these files, and the same text can be pasted into AppGallery, so one set of texts serves every store.

Out of scope: changing `versionCode`, editing `CHANGELOG.md` or GitHub releases, editing titles or descriptions, publishing, committing.

```
- [ ] 1. Metadata tree, locales and versionCode found
- [ ] 2. No existing changelog for this versionCode (or the user chose to revise it)
- [ ] 3. User-facing changes collected
- [ ] 4. Style read from earlier entries
- [ ] 5. Drafts written, primary locale first
- [ ] 6. Check script passes
- [ ] 7. User approved the texts
- [ ] 8. Files reported to the user
```

## 1. Find the tree, locales and versionCode

- **Tree:** the first that exists of `fastlane/metadata/android/`, `metadata/`, `src/*/fastlane/metadata/android/`. If none exists, read [references/new-metadata-tree.md](references/new-metadata-tree.md) before going on.
- **Locales:** the directories inside the tree (`en-US`, `ru-RU`, ...). Write for exactly these; do not add locales the project does not have.
- **versionCode:** what the user said; otherwise `versionCode` in `gradle.properties` or the app module's `build.gradle(.kts)`. If it is computed (from git, CI or a script), ask the user for the number.

## 2. Check for an existing changelog

If `changelogs/<versionCode>.txt` already exists in any locale, the version was probably released with it. Do not overwrite it. Show it and ask: revise this text, or will the user bump `versionCode` first?

## 3. Collect the changes

```bash
git describe --tags --abbrev=0          # last release tag
git describe --tags --abbrev=0 HEAD^    # previous tag, when HEAD itself is tagged
```

If there are no tags, ask which commit to start from.

Keep only what a user of the app would notice: features, visible fixes, behaviour changes. Drop refactoring, CI, dependency bumps and tests unless the user asks for them. Add anything the user mentions that is not in git.

Read the range in two passes, so a large one (hundreds of commits) stays cheap:

1. Subjects only, one line per commit: `git log --no-merges --format='%h %s' <tag>..HEAD`. Pick the candidates by reading the subjects yourself; do not filter them with keyword greps, which drop real fixes such as "Update grid spacing to fix #732".
2. Full message only for the candidates: `git show --no-patch <hash>`.

Before naming a feature, make sure it ships in this release: it is wired into the app (navigation, the production build, not a debug or demo flavor), not only added as code. If nothing user-facing is left, say so and offer a short neutral line ("Stability improvements"), instead of inventing features.

## 4. Read the style

Read the 2-3 most recent changelogs of each locale and its `short_description.txt` (skip it if it does not exist). Note length, tone, sentence or bullet form, verb form ("Added ...", "Добавлены ..."), and how features are named. The new entry should read as if the same person wrote it.

## 5. Write the drafts

Write `en-US` first if the project has it, otherwise the locale with the most history. Write each other locale from the same facts in that locale's own earlier style: not a word-for-word translation. A locale with no earlier entries follows the primary locale's style; mention that in the summary.

Store moderation has a few content rules. They hold in every store, so follow them even for a store the user did not name:

- **Concrete, user-visible changes.** "Fixed a crash on Android 12 at startup", not "bug fixes and stability improvements" in every release. RuStore asks for this explicitly.
- **No issue numbers or tracker keys** (`#123`, `APP-45`). Commit messages are full of them; strip them. RuStore moderation rejects internal codes.
- **No promotion or calls to action**: no sales, "rate us", "update now". Google Play forbids using release notes for promotion or to solicit user actions.
- **No links**, except one to a detailed changelog if the user wants it. RuStore rejects links unrelated to the update.
- **Plain text only**: no HTML or Markdown. Stores show the text as is.
- **Only this release.** No notes for moderators, no text carried over from an earlier version.

When a draft is too long, drop the least important points; never cut a sentence in the middle.

## 6. Check

Write the drafts to their final paths, then run:

```bash
python3 <skill-dir>/scripts/check_changelogs.py <tree> <versionCode> [--stores play,fdroid,rustore,appgallery]
```

`<skill-dir>` is this skill's directory. Pass `--stores` only when the user named the stores; by default every known store is checked, which means the strictest limit (500 characters per language). The script counts characters, not bytes, so Cyrillic is measured correctly, and it flags HTML, issue numbers and links.

Fix every `FAIL` and run it again until it exits with 0. For each `warn` line, fix it or tell the user why it stays (for example, a tracker-like word that is really a product name).

If `python3` is missing, count lengths with a tool that counts characters (not `wc -m` in the C locale, which counts bytes) and say the script did not run.

## 7. Show and confirm

Show every locale's text with its length from the script output. Apply the user's edits and run the check again. Only an approved text stays on disk; if the user drops the change, delete the files you created.

## 8. Report

List the files written. Remind the user to commit them; release tooling and the publishing skills read them from there.
