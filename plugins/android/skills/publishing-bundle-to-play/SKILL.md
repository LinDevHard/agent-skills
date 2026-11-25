---
name: publishing-bundle-to-play
description: Publishes an already-built Android App Bundle (.aab) to a Google Play track (internal testing, closed testing/alpha, open testing/beta, production, or a custom closed track) with the gplay CLI, with optional release notes and staged rollout. Runs offline checks and a dry run, then confirms with the user before anything is committed. Use when the user asks to upload, ship, publish, deploy, or release an AAB or a new Android build to Google Play or the Play Console, or to push a build to Play testers or production, even if they do not mention gplay. Not for building the bundle, promoting an existing release between tracks, or changing an existing rollout.
---

# Publishing a bundle to Play

Publishes one signed `.aab` that is already built to one Play track with `gplay release`. Building, promoting between tracks, and changing an existing rollout are out of scope: say so and stop.

Publishing is mostly one-way: a committed version code can never be used again, and users who updated cannot be downgraded. So the order is: check offline, inspect Play, dry-run, confirm, then publish.

Copy this checklist and tick it off as you go:

```
- [ ] 1. gplay installed and authenticated
- [ ] 2. Inputs resolved: bundle, track, rollout, release notes
- [ ] 3. Offline checks pass (preflight, signature)
- [ ] 4. Current state of the app on Play inspected
- [ ] 5. Dry run succeeds
- [ ] 6. User confirmed the summary
- [ ] 7. Published
- [ ] 8. Release verified on the track
```

Run every `gplay` command with these set, so stderr only carries the command's own output:

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

## 2. Resolve inputs

| Input | Rule |
|---|---|
| Bundle | The path the user gave. Otherwise run `find . \( -path '*/build/outputs/bundle/*' -o -path '*/release/*' \) -name '*.aab' -not -path '*ebug*' -not -path '*/intermediates/*' -exec ls -lt {} +` (newest first, debug variants dropped). Gradle writes to `build/outputs/bundle/`, which is unsigned when the module has no release signing config; Android Studio's Generate Signed App Bundle writes to `<module>/release/`. One match: use it, and mention if it is older than the latest source change. Several: show them and ask. None: tell the user to build first (for example `./gradlew :app:bundleRelease`) and stop. |
| Track | From the user's words: `internal`, `alpha` (closed testing), `beta` (open testing), `production`, or a custom track name. If the user did not name one, ask. Never rely on gplay's default. |
| Rollout | A fraction greater than `0` and below `1` makes a staged rollout ("5%" means `0.05`); leaving it out releases to everyone on the track. For `production`, if the user gave no rollout, ask whether to stage it. |
| Release notes | Optional. Plain text is stored as `en-US`, so for any other language, or several, write a JSON array to a temp file and pass `@file`: `[{"language": "ru-RU", "text": "..."}]`. Play rejects notes over 500 characters per language. |

Package name and version are not inputs: they come from the bundle in step 3. Gradle files are unreliable for this because of flavors and suffixes.

## 3. Offline checks

```bash
gplay preflight --file <bundle> --fail-on error
```

It decodes the bundle's manifest with no network or credentials. Its output starts with `App: <package> (<versionName>, versionCode <N>)`; use these values from here on.

- Exit code 1 means at least one `error` finding (for example a debuggable build, a leaked secret, target SDK too low). Stop, show the findings and ask the user how to proceed.
- Report `warning` findings in the summary; they do not block.
- If the user named a package or version, or `GPLAY_PACKAGE` is set, and the bundle differs: stop and ask. It is the wrong bundle or the wrong app.

Preflight does not look at the signature, and the dry run does not either: an unsigned bundle or one signed with the wrong key is rejected only by the real upload. Check it here:

```bash
keytool -printcert -jarfile <bundle>
```

`keytool` comes with any JDK; if it is not on `PATH`, use the one in `$JAVA_HOME/bin` or Android Studio's bundled JBR. Do not use `gplay android signing verify`: it reports an unsigned bundle as `"verified": true` and fails on a correctly signed one with a self-signed upload certificate.

- `Not a signed jar file`: the bundle is unsigned. Stop. Gradle builds a release bundle unsigned when the module has no `signingConfig` for `release`. The user signs it with the upload key (Android Studio's Generate Signed App Bundle, or a signing config fed from a gitignored properties file). Never handle the keystore or its passwords yourself.
- `Owner: CN=Android Debug`: signed with the debug key. Stop, as above.
- Otherwise note the signer's `Owner` and `SHA256` fingerprint. If the expected upload certificate is known (the user gave it, the project documents it, or an earlier bundle of the same app that Play accepted is on disk: run the same command on it), compare the SHA-256 fingerprints; a mismatch means the wrong key, so stop and ask. If nothing to compare against is known, show the fingerprint in the summary so the user can check it against Play Console (Test and release, App integrity, Upload key certificate).

## 4. Inspect the app on Play

```bash
gplay status --package <package> --pretty
```

A read: it opens a temporary edit and deletes it again. Look at `tracks.tracks[].releases[]` (`status`, `version_codes`, `user_fraction`); ignore vitals errors in `sources`.

- **Version code** not higher than every code listed: stop, the user bumps `versionCode` and rebuilds.
- **No releases on any track**: the app has never been published. Add `--status draft` and tell the user they finish the first release in Play Console.
- **Target track has an `inProgress` release**: publishing replaces it. Show it and ask.

## 5. Dry run

```bash
gplay --dry-run release --package <package> --track <track> --bundle <bundle> \
  [--rollout <fraction>] [--release-notes <text-or-@file>] [--status draft]
```

`--dry-run` is a global flag and goes before `release`. It checks flags, bundle path and release notes, and prints the requests it would send. It does not check permissions, version code, signing or the track on Play: those fail only in the real call.

## 6. Confirm

Show this summary:

```
Package:        com.example.app
Track:          production
Bundle:         app/build/outputs/bundle/release/app-release.aab
Version:        2.3.0 (versionCode 20300)
Rollout:        5% (staged)
Release notes:  en-US, ru-RU
Preflight:      0 errors, 2 warnings (listed above)
Signed by:      CN=Example, SHA-256 2A:29:…:44:15 (matches the previous upload / not compared)
Replaces:       nothing / 2.2.1 at 20% (inProgress)
```

- `internal` and `alpha`: a request like "publish it to internal" is the yes, as long as the summary matches what the user asked for.
- `production` and `beta`: wait for an explicit yes after the summary. Production reaches real users, and anyone can join open testing.
- Any change after the summary needs a new summary and a new yes.

## 7. Publish

Run the dry-run command without `--dry-run`. On success, stdout is JSON with `editId`, `track`, `versionCode`, `status` and `rolloutFraction`; progress goes to stderr.

If it fails, or the user asks to retry, read [references/troubleshooting.md](references/troubleshooting.md) before doing anything else: some failures happen after the release is already live, and a blind rerun can make things worse.

## 8. Verify

```bash
gplay status --package <package> --pretty
gplay tracks releases list --package <package> --track <track> --output table
```

The first shows the version code on the track with `status` and `user_fraction`. The second shows the review state (`releaseLifecycleState`, for example `IN_REVIEW` or `PUBLISHED`). Report track, version, status, rollout and review state. Internal testing is usually available within minutes; other tracks may wait for review.
