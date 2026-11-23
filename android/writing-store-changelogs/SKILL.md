---
name: writing-store-changelogs
description: Writes the app-store release notes ("What's new") for one Android version as a changelog file named after its versionCode in every locale of a fastlane-style metadata tree (fastlane/metadata/android), matching the style of earlier entries and the limits of Google Play, F-Droid and RuStore. Use when preparing an Android release and the user asks for release notes, what's new, a store changelog, or "что нового" for the stores. Not for CHANGELOG.md, GitHub release notes, or store descriptions.
---

# Writing store changelogs

Writes `<locale>/changelogs/<versionCode>.txt` for one version, in every locale the project already has. Google Play, F-Droid and RuStore all read these files, so one set of texts serves every store.

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
git log --no-merges --format='%s%n%b' <tag>..HEAD
```

If HEAD itself is the tag, use the range from the previous tag. If there are no tags, ask which commit to start from.

Keep only what a user of the app would notice: features, visible fixes, behaviour changes. Drop refactoring, CI, dependency bumps and tests unless the user asks for them. Add anything the user mentions that is not in git. If nothing user-facing is left, say so and offer a short neutral line ("Stability improvements"), instead of inventing features.

## 4. Read the style

Read the 2-3 most recent changelogs of each locale and its `short_description.txt`. Note length, tone, sentence or bullet form, verb form ("Added ...", "Добавлены ..."), and how features are named. The new entry should read as if the same person wrote it.

## 5. Write the drafts

Write `en-US` first if the project has it, otherwise the locale with the most history. Write each other locale from the same facts in that locale's own earlier style: not a word-for-word translation. A locale with no earlier entries follows the primary locale's style; mention that in the summary.

When a draft is too long, drop the least important points; never cut a sentence in the middle.

## 6. Check

Write the drafts to their final paths, then run:

```bash
python3 <skill-dir>/scripts/check_changelogs.py <tree> <versionCode> [--stores play,fdroid,rustore]
```

`<skill-dir>` is this skill's directory. Pass `--stores` only when the user named the stores; by default every known store is checked, which means the strictest limit (500 characters). The script counts characters, not bytes, so Cyrillic is measured correctly. Fix every `FAIL` and run it again until it exits with 0.

If `python3` is missing, count lengths with a tool that counts characters (not `wc -m` in the C locale, which counts bytes) and say the script did not run.

## 7. Show and confirm

Show every locale's text with its length from the script output. Apply the user's edits and run the check again. Only an approved text stays on disk; if the user drops the change, delete the files you created.

## 8. Report

List the files written. Remind the user to commit them; release tooling and the publishing skills read them from there.
