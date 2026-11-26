---
name: publishing-bundle-to-rustore
description: Publishes an already-built Android App Bundle (.aab) update to RuStore with the rustore-publisher CLI and sends it to moderation, with release notes from the project's metadata tree and a manual or automatic release after approval. Runs a dry run and confirms with the user before anything is created in the store. Use when the user asks to upload, ship, publish, or release an AAB or a new Android build to RuStore or RuStore Console, even if they do not mention rustore-publisher. Not for building the bundle, the app's first publication, APK files, partial rollout, or releasing a version that already passed moderation.
---

# Publishing a bundle to RuStore

Publishes one signed `.aab` that is already built as an update of an app that is already live in RuStore, with `rustore-publisher publish`. The first publication of an app, APK files, partial rollout and the release after moderation are done in RuStore Console: say so and stop.

RuStore has no testing tracks: every publish goes to moderation and then to all users. A version that reached moderation cannot be taken back with this tool, and a failed run can leave a draft that only the console can remove. So the order is: dry-run, inspect, confirm, then publish.

Copy this checklist and tick it off as you go:

```
- [ ] 1. rustore-publisher installed and credentials set
- [ ] 2. Inputs resolved: bundle, release notes, metadata dir, screenshots, publish type
- [ ] 3. Dry run passes
- [ ] 4. Current state of the app in RuStore inspected
- [ ] 5. User confirmed the summary
- [ ] 6. Sent to moderation
- [ ] 7. Version checked in RuStore
```

## 1. Check the tool and credentials

```bash
rustore-publisher version
echo "${RUSTORE_CREDENTIALS_FILE:-not set}"
```

- Not found: tell the user to install it (`go install github.com/vyachin/rustore-publisher/cmd/rustore-publisher@latest`, or a release archive from github.com/vyachin/rustore-publisher) and stop. Do not install it yourself.
- No credentials: the user creates an API key in RuStore Console (company owner or admin, with access to this app) and saves `{"keyId": ..., "privateKey": ...}` to a file, then sets `RUSTORE_CREDENTIALS_FILE` or passes `--credentials <file>` on every command. Never print, read aloud or commit that file.

## 2. Resolve inputs

| Input | Rule |
|---|---|
| Bundle | The path the user gave. Otherwise run `find . -path '*/build/outputs/bundle/*' -name '*.aab' -not -path '*ebug*' -exec ls -lt {} +` (newest first). If the project has a RuStore flavor (`*rustore*` in the path), use that one: Play builds may carry Google Play Billing. One match: use it, and mention if it is older than the latest source change. Several: show them and ask. None: tell the user to build first and stop. |
| Release notes | RuStore takes only Russian notes: `ru-RU/changelogs/<versionCode>.txt`, up to 5000 characters, in the metadata tree (`fastlane/metadata/android/` or `metadata/`). To learn the versionCode, run the dry run from step 3 once: even when it fails, its JSON has `version_code`. If the file is missing, ask the user for the text or offer to write it. |
| Metadata dir | Never pass the project's tree itself. The tool also sends any `ru-RU` title, descriptions, icon, screenshots and `developer-contacts.json` it finds there, replacing the RuStore listing, and it rejects a `changelogs/default.txt` (which gplay writes). Build a temporary directory with only the notes: `M=$(mktemp -d) && mkdir -p "$M/ru-RU/changelogs" && cp <tree>/ru-RU/changelogs/<code>.txt "$M/ru-RU/changelogs/"`. Copy card files into it only when the user asked to update the listing. |
| Screenshots | If `<tree>/ru-RU/images/` has `phoneScreenshots/`, `tenInchScreenshots/` or `tvScreenshots/` with files, ask whether to update the RuStore screenshots in this release (they go to moderation with it). No answer or no: leave them out. Yes: copy those folders into `"$M/ru-RU/images/"`, run `file` on each image and check: PNG or JPEG, sides 320–3840 px, 16:9 or 9:16, one orientation per folder, 3–10 files, up to 5 MB; order is by file name. Write `preview.html` to a temp folder (one section per type with its size and count, the images as `<img src="file:///abs/path" style="height:240px">` in order) and open it (`open` / `xdg-open`). Only `ru-RU` is used; other locales and `sevenInchScreenshots` are ignored. |
| Publish type | `manual` (the default): after approval the user releases in the console. `instantly` only if the user asked for the version to go live on approval. |

Package name and versionCode are not inputs: the tool reads them from the bundle. If the user named either, pass `-p <package>` or `--version-code <N>` so the tool refuses a bundle that does not match.

## 3. Dry run

```bash
rustore-publisher publish -f <bundle> --metadata-dir "$M" [--publish-type instantly] [-p <package>] --dry-run --json
```

It reads the bundle, checks the notes and card files, authenticates and reads the app's versions, all without writing anything. Stdout is one JSON object with `package` and `version_code` from the bundle; on success `outcome` is `dry_run`.

- `error.code` `INVALID_CHANGELOG`: no notes file for this versionCode, or it is empty or too long. Go back to step 2.
- `error.code` `INVALID_CREDENTIALS`: the credentials file is wrong. Checked before any network call, like the bundle and the notes.
- Any other `error`: read [references/troubleshooting.md](references/troubleshooting.md). The common ones here are no active version (first publication), an existing draft, and a versionCode that is not higher than the live one.

The dry run does not check signing, permissions or moderation: those fail only in the real call.

## 4. Inspect the app in RuStore

```bash
rustore-publisher status -p <package>
```

It shows the latest release (code, status, notes) and any draft. If the latest release is still in moderation (`MODERATION`, `TAKEN_FOR_MODERATION`, `AUTO_CHECK`) or `READY_FOR_PUBLICATION`, a new version will compete with it: show it and ask.

## 5. Confirm

Show this summary and wait for an explicit yes, even when the user already said "publish": the version goes to every RuStore user after moderation.

```
Package:        com.example.app
Bundle:         app/build/outputs/bundle/rustoreRelease/app-rustore-release.aab
Version code:   42 (live now: 41)
Release notes:  ru-RU, 312 characters (shown below)
Listing:        unchanged / title, short description
Screenshots:    unchanged / phone 5 (1080x1920), tablet 5 (2560x1440), preview: /tmp/.../preview.html
After approval: released by you in RuStore Console (manual)
```

Show the release notes text in full under the summary. Any change after the summary needs a new dry run, a new summary and a new yes.

## 6. Publish

Run the dry-run command without `--dry-run`. It creates a draft, uploads the bundle, waits for RuStore to process it and sends the version to moderation; this can take a few minutes. On success `outcome` is `submitted`, with `version_id` (RuStore's ID, not the versionCode) and `version_status`.

If it fails, or the user asks to retry, read [references/troubleshooting.md](references/troubleshooting.md) before doing anything else: a failed run can leave a draft or a version already in moderation, and a blind rerun fails or doubles the work.

## 7. Check the version

```bash
rustore-publisher status -p <package> --version-id <version_id>
```

Report the versionCode, the RuStore version ID, the status and the publish type. Say plainly that the version is in moderation and not live yet: with `manual` the user releases it in RuStore Console after approval, with `instantly` RuStore releases it on approval. The same command later shows the moderator's comment if the version is rejected.
