---
name: publishing-screenshots-to-play
description: Uploads store listing screenshots (phone, 7-inch and 10-inch tablet, TV, Wear) and the feature graphic from a fastlane-style folder to the Google Play listing with the gplay CLI, replacing what is there for each image type it uploads. Shows a preview of every image it will upload and asks the user before committing. Use when the user asks to upload, publish, push or update screenshots, store images or the feature graphic on Google Play, even if they do not mention gplay. Not for making screenshots, editing listing texts, or publishing a build.
---

# Publishing screenshots to Play

Uploads the images in `<dir>/<locale>/images/<type>/` to Play in one edit, then commits it. Images are the user's own; the skill only uploads them.

Run every `gplay` command with `GPLAY_NO_UPDATE=1 GPLAY_NO_STAR_PROMPT=1` set.

## 1. Inputs

- **gplay**: `gplay auth status`. Not found: the user installs it (`brew install tamtom/tap/gplay`). Not authenticated: the user runs `gplay auth login --service-account <key.json>`. Stop in both cases.
- **Package**: the one the user named, else `applicationId` of the app module's `build.gradle(.kts)`. Unclear: ask.
- **Folder**: the one the user gave, else `fastlane/metadata/android`, else `metadata`. It holds `<locale>/images/` with `phoneScreenshots/`, `sevenInchScreenshots/`, `tenInchScreenshots/`, `tvScreenshots/`, `wearScreenshots/` and `featureGraphic.png`. Files of one type are uploaded in name order, which becomes their order on Play.
- **No images at all**: say so. If the `making-store-screenshots` skill is available, offer it to make the series; otherwise tell the user the folder layout above. Stop.
- Skip `icon.png`, `promoGraphic.png` and `tvBanner.png` unless the user asked for them.

## 2. Plan

```bash
gplay edits create --package <pkg>            # note "id"
```

The plan output is long JSON, so save it and read only the counts, one locale at a time:

```bash
gplay images plan --package <pkg> --edit <id> --dir <dir> --locale <locale> --pretty > <tmp>/plan-<locale>.json
grep -E '"(type|action)":' <tmp>/plan-<locale>.json | paste - - | tr -d ' ",' | sort | uniq -c
grep -o "Listing for language '[^']*' not found" <tmp>/plan-<locale>.json | sort -u
```

Each line reads `<count> type:<type> action:<action>`: `upload` is a local file Play does not have, `keep` one it has, `remote-only` an image on Play with no local copy. Errors:

- `Listing for language '<locale>' not found`: that locale has no listing on Play. Skip it and tell the user to add the listing in Play Console first.
- Errors about `promoGraphic`: ignore.

A type is uploaded only if it has local files and they differ from Play (any `upload` in it). Types with only `keep` are left alone.

## 3. Preview

Run `file <image>` on each file to upload (it prints the size, e.g. `PNG image data, 1080 x 1920`). Play limits: PNG or JPEG, sides 320–3840 px, long side at most 2× the short one, 2–8 per type; feature graphic exactly 1024 x 500. Report files that break a limit and leave them out.

Write `preview.html` to a temp folder: one section per locale and type, the heading `<locale> · <type> · <W>x<H> · <N> new, replaces <M> on Play`, then the images in upload order (`<img src="file:///abs/path" style="height:240px">`, number under each). Open it for the user (`open` on macOS, `xdg-open` on Linux) and give its path.

## 4. Confirm

Show this and wait for an explicit yes; the images go live on the public listing:

```
Package:   com.example.app
en-US:     phoneScreenshots 5 (replaces 5), tenInchScreenshots 5 (replaces 5)
ru-RU:     skipped, no listing on Play
Untouched: wearScreenshots, featureGraphic, icon
Preview:   /tmp/.../preview.html
```

No: `gplay edits delete --package <pkg> --edit <id> --confirm` and stop. Any change: a new summary and a new yes.

## 5. Upload and commit

For each locale and type being uploaded, in the same edit:

```bash
gplay images delete-all --package <pkg> --edit <id> --locale <locale> --type <type> --confirm
gplay images upload --package <pkg> --edit <id> --locale <locale> --type <type> --file <file>   # each file, in name order
```

`featureGraphic` takes one `upload` (it replaces the old one), no `delete-all`.

Then `gplay edits commit --package <pkg> --edit <id>`.

If any command fails before the commit, delete the edit: Play is unchanged. Show the error and stop; do not retry on your own. If the commit fails because another edit was committed meanwhile (for example in Play Console), start again from step 2.

## 6. Report

Say what was uploaded per locale and type and what was skipped. Listing changes can wait for Play review before users see them.
