---
name: making-store-screenshots
description: Builds a styled series of 5-8 store screenshots (a cover plus one feature per frame, with a composition that continues across frames) for the App Store, Google Play, RuStore, Huawei AppGallery and F-Droid from an app's own screenshots, which it captures from an emulator, simulator or browser with a clean status bar, finds in the project, or takes from a folder. Writes ASO captions per locale, renders phone, tablet, foldable and iPad sizes plus the Play feature graphic, checks them against store rules and places them into the fastlane or Triple-T tree. Use when asked for store screenshots, App Store or Play listing images, ASO screenshots, a feature graphic, or "скриншоты для стора". Not for uploading to a store or taking a single plain screenshot.
---

# Making store screenshots

The scripts render HTML through Chrome, so layout, checks and output are the same on every run. You choose the
shots, write the captions and pick a style; the scripts handle sizes, layout, store limits and file placement.
Run the scripts, don't read them. `<skill>` below is this skill's directory.

## Setup

```bash
PY=python3; $PY -c "import playwright, PIL" 2>/dev/null || { python3 -m venv .venv && .venv/bin/pip install playwright pillow; PY=.venv/bin/python; }
```

Run every script below with that `$PY` (or with a Python the user already set up). Google Chrome is used when
installed; otherwise run `.venv/bin/playwright install chromium`. Never install globally. Keep any scratch files
(previews, side-by-side sheets) inside the series folder.

## Workflow

Copy this checklist and tick it off:

```
- [ ] 1. Targets and locales
- [ ] 2. Shots, one set per form and platform
- [ ] 3. Captions approved by the user
- [ ] 4. Style chosen
- [ ] 5. series.json written; render.py --validate clean
- [ ] 6. Rendered
- [ ] 7. check.py 0 FAIL; every contact sheet looked at
- [ ] 8. Placed; summary to the user
```

**1. Targets and locales.** From the project: an Android app → `android-phone` (one 9:16 set serves Play, RuStore,
AppGallery and F-Droid) plus `feature-graphic`, which Play requires; an iOS app → `ios-phone`, plus `ios-ipad` when
`TARGETED_DEVICE_FAMILY` includes 2. Add tablets (`android-tablet-7`, `android-tablet-10`, their `-landscape`
variants, `ios-ipad-landscape`) and foldables (`android-foldable` for the inner screen, `android-foldable-outer`)
when the user wants them or the app is built for them. Sizes and per-store limits live in the scripts; don't pick
them from memory. If the user asks for a store whose platform has no app or no shots here (the App Store for an
Android-only project), say so and offer what is possible: capture from the other platform's build if it exists,
or the set for the stores the shots do fit. Locales: the folders of the existing listing (`fastlane/metadata/android/<locale>`,
`fastlane/metadata/<locale>`, Triple-T `listings/<locale>`); ask if there are none.

**2. Shots.** In this order: a folder the user gave → screenshots already in the project (`fastlane/`, `store/`,
`screenshots/`, `docs/`; show what you found and ask whether to use them) → capture them. For capture, the clean
status bar and getting to a screen, see [references/capturing.md](references/capturing.md). Look at every shot.
Android shots have Android status-bar icons and a gesture pill or three-button bar, and are often 1080 wide; iOS
shots have the Dynamic Island or notch area, a home indicator, and widths such as 1179, 1206, 1290 or 1320. When
you restyle shots that already sit in the listing tree, copy them to `store/screenshots/shots/` first and point
the series there: placing the new set replaces those files. One series takes one set of shots for all locales;
when the UI is localized, make a series per locale.

Each target takes shots of its own platform and form. An App Store set takes only iOS shots, or web shots without
Android chrome. A tablet, iPad or foldable set takes only shots from that kind of device. **If the right shots are
missing, stop and say so.** Offer to capture them, or drop that target. Never build the set from the wrong shots:
Apple rejects Android imagery (2.3.10) and phone shots in iPad sets.

**3. Captions.** Choose 5-8 screens. Put the strongest one on the cover; frames 1-3 must show real UI. Write a
caption per frame and locale following [references/copywriting.md](references/copywriting.md). Show the table
frame → shot → caption for every locale and wait for approval. If the user asks for a forbidden claim ("#1",
"free", "best", a price, "new", "download now"), say which store rule forbids it and propose a benefit caption.
The forbidden text is not an option to choose; ask the user to approve the replacement. Add `"alt"` per frame and
locale for Play's alt text.

**4. Style.** Propose one of `sketch`, `tone`, `poster` or `minimal` with one line on why, and show its preview
(`<skill>/assets/previews/<style>.jpg`). Details and overrides are in [references/styles.md](references/styles.md).
Brand colours for `app.brand`: the app's theme, or `$PY <skill>/scripts/palette.py <icon.png>`.

**5. series.json.** Start from `<skill>/assets/series.example.json` and save it as `store/screenshots/series.json`,
unless the project has a better place. Paths are relative to the series file. A shot's `path` is either one file
with `"platform"` (`android`, `ios` or `web`) and `"form"` (`phone`, `tablet` or `foldable`), or a map keyed
`"<platform>"` / `"<platform>-<form>"`:

```json
{"path": {"android": "shots/android/02.png", "ios": "shots/ios/02.png", "android-tablet": "shots/tablet/02.png"}}
```

A cover with `"span": 2` covers two frames, and its devices cross the border between them on their own; leave
`offset` out unless you need a specific position (`[x, y]`: x in frames from the frame's left edge, so 1.0 is the
border of a 1-wide frame; y in frame heights). Output goes next to the series file (`out/`) and the project root is
found by walking up; set `"output": {"workdir": ..., "project_root": ...}` (relative to the series file) only to
change that. Then:

```bash
$PY <skill>/scripts/render.py store/screenshots/series.json --validate
```

Fix every FAIL it prints (missing files, frame counts per store, wrong platform or form for a target).

**6. Render.**

```bash
$PY <skill>/scripts/render.py store/screenshots/series.json
```

Output goes to `out/` next to the series file:

- `<target>/<WxH>/<locale>/NN.png` (JPEG when a PNG is over the store's size limit) and `canvas.png`;
- `contact-<locale>.png`, `alt-text.<locale>.txt` and `render-report.json`.

Use `--style NAME` to try another style, and `--targets` or `--locales` to render a subset.

**7. Check.**

```bash
$PY <skill>/scripts/check.py store/screenshots
```

Fix every FAIL. Fix each warn or tell the user why it stays. Then open every `contact-<locale>.png` (the frames
side by side) and check:

- borders meet;
- captions read well;
- nothing important is cut off;
- no stray dialog or other apps' logos.

Return to step 5 or 6 until both the check and the look pass.

**8. Place.**

```bash
$PY <skill>/scripts/place.py store/screenshots --dry-run
$PY <skill>/scripts/place.py store/screenshots
```

It writes to the fastlane tree, or to Triple-T when the project has `src/main/play/listings`, and it refuses to
replace existing files: on any conflict it copies nothing at all. Show the conflicts to the user and run it with
`--force` only after they agree (it then replaces only the slots this series fills). Tell the user:

- where everything went;
- what place.py left for manual upload (foldables);
- that nothing is committed.

## Rules the scripts cannot enforce

- No store badges, "Featured by Apple", "Editor's choice", awards, ratings, reviews or download counts in any
  image, even when the user asks: stores forbid them or they are fake.
- Only the neutral device frame. Never draw something that looks like a specific iPhone or Android phone.
- Fictional data only: no real people's names, messages or accounts in the shots.
- Don't overwrite listing files without asking. Don't upload, and don't commit.

Store limits and their sources: [references/store-rules.md](references/store-rules.md).
