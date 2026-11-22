---
name: publishing-to-google-play
description: Publishes an already-built Android App Bundle (.aab) to a Google Play track (internal testing, closed testing/alpha, open testing/beta, production, or a custom closed track) with the gplay CLI, with optional release notes and staged rollout. Runs offline checks and a dry run, then confirms with the user before anything is committed. Use when the user asks to upload, ship, publish, deploy, or release an AAB or a new Android build to Google Play or the Play Console, or to push a build to Play testers or production, even if they do not mention gplay. Not for building the bundle, promoting an existing release between tracks, or changing an existing rollout.
---

# Publishing a bundle to Google Play

Publishes one signed `.aab` that is already built to one Play track with `gplay release`. Building, promoting between tracks, and changing an existing rollout are out of scope: say so and stop.

Publishing is mostly one-way. A committed version code can never be used again, and users who updated cannot be downgraded. Testing tracks can get a new release and a staged rollout can be halted, but neither undoes the upload. So the order is: check offline, inspect Play, dry-run, confirm, then publish.

Copy this checklist and tick it off as you go:

```
- [ ] 1. gplay installed and authenticated
- [ ] 2. Bundle picked, package and version read from it
- [ ] 3. Offline checks pass (preflight)
- [ ] 4. Current state of the app on Play inspected
- [ ] 5. Dry run succeeds
- [ ] 6. User confirmed the summary
- [ ] 7. Published
- [ ] 8. Release verified on the track
```

Run every `gplay` command in this skill with these set, so stderr only carries the command's own output:

```bash
export GPLAY_NO_UPDATE=1 GPLAY_NO_STAR_PROMPT=1
```

## 1. Check gplay and auth

```bash
gplay --version
gplay auth status
```

- `gplay` not found: tell the user to install it with `brew install tamtom/tap/gplay` and stop. Do not install it yourself.
- Not authenticated: run `gplay auth doctor` and show the result. The user sets up the service account (`gplay auth login --service-account <key.json>`). Do not run `gplay setup --auto`: it creates Google Cloud resources and changes account permissions.

## 2. Pick the bundle

Use the path the user gave. Otherwise list release bundles, newest first:

```bash
find . -path '*/build/outputs/bundle/*' -name '*.aab' -not -path '*ebug*' -exec ls -lt {} +
```

The `-not -path '*ebug*'` drops debug variants only; a debuggable release build still gets through and is caught by preflight in step 3.

- One match: use it, but if it is older than the latest source change, mention that it may be stale.
- Several matches (flavors, modules): show them with their times and ask which one.
- None: tell the user to build first (for example `./gradlew :app:bundleRelease`) and stop.

The package name and version come from the bundle itself, in step 3. Do not derive them from Gradle files: flavors and suffixes make that unreliable.

## 3. Offline checks

`preflight` decodes the bundle's manifest and runs compliance checks with no network and no credentials:

```bash
gplay preflight --file <bundle> --fail-on error
```

Its output starts with `App: <package> (<versionName>, versionCode <N>)`; use these values from here on.

- Exit code 1 means at least one `error` finding (for example a debuggable build, missing 16 KB alignment, a leaked secret, target SDK too low). Stop: show the findings and ask the user how to proceed.
- Report `warning` findings in the summary; they do not block.
- If the user gave a package (or `GPLAY_PACKAGE` is set) and it differs from the bundle's package, stop and ask: it is the wrong bundle or the wrong app.
- If the user named a version ("ship 2.3.0") and the bundle's `versionName` differs, stop and ask.

## 4. Inspect the app on Play

```bash
gplay status --package <package> --pretty
```

This read opens a temporary edit and deletes it again. Its JSON has `tracks.tracks[].releases[]` with `status`, `version_codes` and `user_fraction`. It also includes a vitals summary; if `sources` reports an error for vitals only, ignore it. Check:

- **Version code.** Play only accepts a version code that was never used for this app. If the bundle's code is not higher than every code listed, stop: the user needs to bump `versionCode` and rebuild. Play has the final say at upload.
- **Draft app.** No track has any release: the app has never been published. Plan `--status draft` for the release (rollout is then ignored) and say in the summary that the user finishes the first release in Play Console.
- **Running rollout.** The target track already has an `inProgress` release: publishing replaces it. Show it and ask before going on.
- **Track name.** A custom closed track must already exist in Play Console, with exactly that name. If it does not appear here, ask the user to check the name in Console; do not create tracks.

## 5. Resolve the remaining inputs

| Input | Rule |
|---|---|
| Track | From the user's words: `internal`, `alpha` (closed testing), `beta` (open testing), `production`, or a custom track name. If the user did not name one, ask. Never rely on gplay's default. |
| Rollout | A fraction greater than `0` and below `1` makes a staged rollout ("5%" means `0.05`); leaving it out releases to everyone on the track. For `production`, if the user gave no rollout, ask whether to stage it. |
| Release notes | Optional. Plain text is stored as `en-US`, so for text in any other language, or several languages, write a JSON array to a temp file and pass `@file`. Play rejects notes over 500 characters per language. |

Release notes JSON format:

```json
[
  {"language": "en-US", "text": "Bug fixes and performance improvements"},
  {"language": "ru-RU", "text": "Исправления ошибок и улучшения производительности"}
]
```

## 6. Dry run

```bash
gplay --dry-run release --package <package> --track <track> --bundle <bundle> \
  [--rollout <fraction>] [--release-notes <text-or-@file>] [--status draft]
```

`--dry-run` is a global flag: it goes before `release` (after it, gplay fails with exit code 2). It checks the flags, the bundle path and the release notes, and prints the requests it would send. It does not check permissions, version code, signing or the track on Play: those fail only in the real call.

## 7. Confirm, then publish

Show this summary:

```
Package:        com.example.app
Track:          production
Bundle:         app/build/outputs/bundle/release/app-release.aab
Version:        2.3.0 (versionCode 20300)
Rollout:        5% (staged)
Release notes:  en-US, ru-RU
Preflight:      0 errors, 2 warnings (listed above)
Replaces:       nothing / 2.2.1 at 20% (inProgress)
```

- `internal` and `alpha`: a request like "publish it to internal" is the yes, as long as the summary matches what the user asked for.
- `production` and `beta`: wait for an explicit yes after the summary. Production reaches real users, and anyone can join open testing.
- Any change after the summary (another status, another flag) needs a new summary and a new yes.

Then run the dry-run command without `--dry-run`. On success, stdout is JSON with `editId`, `track`, `versionCode`, `status` and `rolloutFraction`; progress lines go to stderr.

## 8. Verify

```bash
gplay status --package <package> --pretty
gplay tracks releases list --package <package> --track <track> --output table
```

The first shows the new version code on the track with its `status` and `user_fraction`. The second shows the review state (`releaseLifecycleState`, for example `IN_REVIEW` or `PUBLISHED`). Report track, version, status, rollout and review state. Internal testing is usually available within minutes; other tracks may wait for review.

## When the release fails

gplay errors start with the step that failed. Show the user the exact error text.

| Error starts with | Meaning |
|---|---|
| `failed to create edit:`, `failed to upload bundle`, `failed to update track:`, `validation failed:` | Nothing was published. Fix the cause (table below) and go back to step 6. |
| `commit failed:`, or the connection dropped during commit | The release may or may not be live. Run step 8 first. If the version code is on the track, it shipped: report it and do not rerun. |

A failed run can leave an open edit. It expires on its own. Delete it only if you have its ID from the stderr line `Edit created: <id>`: `gplay edits delete --package <package> --edit <id> --confirm`. Never delete an edit you did not create.

When the user says "just retry", do step 8 first, then rerun the same command only if the version code is not on Play.

| Error mentions | Cause and fix |
|---|---|
| `Version code ... has already been used` | Right after a failed attempt: that attempt went through, verify with step 8. Otherwise the user bumps `versionCode` and rebuilds. |
| Signed with the wrong key / upload certificate | The bundle is not signed with the app's upload key. The user rebuilds with the right keystore. |
| `Only releases with status draft may be created on draft app` | The app has never been published. Add `--status draft` and go back to step 6 (new dry run, new summary). |
| `Changes cannot be sent for review automatically` | The app uses managed publishing or has other pending changes. With `--changes-not-sent-for-review`, nothing goes to review until the user clicks "Send for review" in Console, so the release is not live yet. Add the flag, go back to step 6, and say this in the summary. |
| Staged rollout not allowed | The app's first production release cannot be staged. Ask whether to release to 100%. |
| Exit code 3, 13 (403), or `Package not found` | Auth failed, or the service account has no access to this app (Play Console, Users and permissions). |
| `Track ... not found` | The custom track name does not match Play Console. Ask the user for the exact name. |
| Exit code 5 (409), another edit open | Someone else is editing the app in Console or another job. Wait and retry from step 6. |

For anything else, run `gplay release --help` to check the flags and stop rather than guessing.
