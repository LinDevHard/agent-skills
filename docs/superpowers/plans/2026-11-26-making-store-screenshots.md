# making-store-screenshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `making-store-screenshots` skill (new `store-assets` plugin) to `~/Develop/agent-skills`: an agent turns an app's screenshots into a styled, store-compliant 5–8 frame series for App Store, Google Play, RuStore, AppGallery and F-Droid.

**Architecture:** The agent writes a `series.json`; Python scripts build one wide HTML canvas per (target, locale) from a style template, render it with Playwright (system Chrome first, bundled Chromium as fallback), slice it into frames exactly at frame borders, and write a `render-report.json` with caption geometry. `check.py` validates images and report against store rules; `place.py` copies the result into the project's fastlane tree.

**Tech Stack:** Python 3.10+, Playwright for Python, Pillow, pytest (tests only), HTML/CSS, OFL fonts, SVG.

**Spec:** `docs/superpowers/specs/2026-11-26-making-store-screenshots-design.md` (read it first; it is in Russian).

## Global Constraints

- Repo: `~/Develop/agent-skills`. Skill dir: `plugins/store-assets/skills/making-store-screenshots/` (`SKILL.md`, `references/`, `scripts/`, `assets/`). Abbreviated below as `SKILL/`.
- Tests and evals live outside the plugin so installers never ship them: `tests/making-store-screenshots/`, `evals/making-store-screenshots/`.
- Frontmatter: `name: making-store-screenshots`; `description` third person, ≤1024 chars, no XML, says what + when + when not.
- `SKILL.md` body < 500 lines and < 5000 tokens; references one level deep; any reference > 100 lines starts with a table of contents.
- Terms, used everywhere (docs, code, messages): **series**, **frame**, **shot** (source screenshot), **target**, **style**, **canvas**.
- No network during render. Fonts and decor are bundled. No uploads to stores, no git commits by the skill.
- Every numeric constant in scripts carries a comment with its source rule (e.g. `# Play: ≤8 MB`).
- Scripts handle their own errors with actionable messages (missing dependency → exact install command; missing file → list of what exists).
- Dependency install line (printed by scripts, used in docs): `python3 -m venv .venv && .venv/bin/pip install playwright pillow && .venv/bin/playwright install chromium` (the last step only when Google Chrome is absent).
- Dev setup for this repo: `python3 -m venv .venv && .venv/bin/pip install playwright pillow pytest fonttools`; `.venv/` goes into `.gitignore`. Tests run with `.venv/bin/pytest tests/making-store-screenshots -q`.
- Target table (portrait, px): `ios-phone` 1320×2868 **and** 1206×2622 (same layout, both emitted); `ios-ipad` 2064×2752; `android-phone` 1080×1920; `android-tablet-7` 1080×1920; `android-tablet-10` 1440×2560; `feature-graphic` 1024×500.
- Store limits (spec, "Требования сторов"): no alpha anywhere; Play ≤8 MB, side 320–3840, long side ≤2.3× short, 2–8 phone frames, ≥4 at ≥1080 px for promotion; RuStore ≥3 frames, ≤3 MB phone / ≤5 MB tablet, max 2160×3840, 9:16 or 16:9 only; AppGallery 3–8, ≤2 MB; App Store 1–10 per size; caption area ≤20 % of a frame; Play alt text ≤140 chars, must not start with "image of"/"photo of".
- Device frame is neutral: rounded body, no island, notch, buttons, camera or logos.
- Commit after every task; message style of the repo (`Add …`, `Handle …`, imperative, no prefix).

## Review Focus

1. **Shots of mixed sizes and aspect ratios** (720×1561 next to 1080×2400, a landscape shot): every frame still renders, the shot is fitted (never stretched) and `check.py` warns on >1.5× upscale. Test in Task 4 (`test_mixed_aspect_shots_are_fitted_not_stretched`).
2. **A caption longer than the style expects** (German, 9 words): text wraps inside the caption box, never overflows the frame or covers the shot area silently; `check.py` flags >20 % area. Tests in Task 4 (`test_long_caption_wraps_within_frame`) and Task 7.
3. **Fewer shots than frames, or a 2-frame cover with only one shot**: validation names the frame and the missing field instead of a stack trace. Test in Task 2 (`test_cover_two_wide_needs_a_shot`).
4. **Re-running into an existing fastlane tree**: nothing is overwritten without `--force`; numbering of files the skill did not write is left alone. Test in Task 8 (`test_place_refuses_to_overwrite`).
5. **Machine without Chrome or Playwright**: render exits non-zero with the exact install line, not a Python traceback. Test in Task 5 (`test_missing_playwright_prints_install_line`).

---

### Task 1: Plugin scaffold and target table

**Files:**
- Create: `plugins/store-assets/plugin.json`, `plugins/store-assets/.claude-plugin/plugin.json` (copy of `plugins/android/…` with name `store-assets`, version `0.1.0`, description "Store listing assets: styled App Store and Google Play screenshot series.")
- Modify: `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json` (add `store-assets` entry mirroring `android`), `README.md` (new "`store-assets` plugin" table with the skill row, needs "Python 3, Playwright, Pillow"), `.gitignore` (`.venv/`)
- Create: `SKILL/SKILL.md` (frontmatter only + one-line body placeholder "Instructions are written in Task 10"), `SKILL/scripts/targets.py`
- Test: `tests/making-store-screenshots/conftest.py` (adds `SKILL/scripts` to `sys.path`), `tests/making-store-screenshots/test_targets.py`

**Interfaces:**
- Produces: `targets.TARGETS: dict[str, Target]`; `@dataclass(frozen=True) Target(name: str, sizes: tuple[tuple[int,int], ...], platform: Literal["ios","android","any"], stores: tuple[str, ...], max_bytes: int, min_frames: int, max_frames: int)`; `targets.STORE_LIMITS: dict[str, StoreLimit]` with `StoreLimit(max_bytes:int, min_frames:int, max_frames:int, min_side:int, max_side:int, max_ratio:float)` for `appstore`, `play`, `rustore`, `appgallery`, `fdroid`.
- Target rows: `ios-phone` sizes ((1320,2868),(1206,2622)) platform ios stores (appstore,); `ios-ipad` ((2064,2752),) ios; `android-phone` ((1080,1920),) android stores (play,rustore,appgallery,fdroid); `android-tablet-7` ((1080,1920),) and `android-tablet-10` ((1440,2560),) android stores (play,rustore) — 9:16 because Play tablets accept only 9:16/16:9 and RuStore crops anything else; both within Play's 1080–7680 and RuStore's ≤2160×3840; `feature-graphic` ((1024,500),) any stores (play,).
- `max_bytes` of a target = min over its stores (android-phone → 2 MB from AppGallery).

- [ ] **Step 1: Scaffold the plugin, marketplaces, README row, `.gitignore`, dev venv.** Run `claude plugin validate .` → no errors.
- [ ] **Step 2: Write failing tests** `test_targets.py`:
  - `test_every_android_size_is_9_16`: for android targets, `w*16 == h*9`.
  - `test_android_phone_budget_is_appgallery`: `TARGETS["android-phone"].max_bytes == 2*1024*1024`.
  - `test_frame_counts_intersect_stores`: android-phone `min_frames == 3`, `max_frames == 8`; ios-phone `1..10`.
  - `test_sizes_within_store_sides`: every size within its stores' `min_side..max_side` and `max(w,h)/min(w,h) <= max_ratio`.
- [ ] **Step 3: Run** `.venv/bin/pytest tests/making-store-screenshots/test_targets.py -q` → FAIL (module missing).
- [ ] **Step 4: Implement `targets.py`** with the values above, each with a source comment.
- [ ] **Step 5: Run tests** → PASS. **Step 6: Commit** `Add store-assets plugin with making-store-screenshots target table`.

### Task 2: Series config and validation

**Files:**
- Create: `SKILL/scripts/series.py`, `SKILL/assets/series.example.json`
- Test: `tests/making-store-screenshots/test_series.py`

**Interfaces:**
- Consumes: `targets.TARGETS`.
- Produces: `series.load(path: Path) -> Series`; `series.validate(s: Series, base_dir: Path) -> list[Issue]`; `@dataclass Issue(level: Literal["FAIL","warn"], where: str, message: str)`; dataclasses `Series(app: App, style: StyleRef, targets: list[str], locales: list[str], frames: list[Frame], decor: list[Decor], output: Output)`, `App(name: str, brand: list[str], icon: str|None)`, `StyleRef(name: str, overrides: dict)`, `Frame(role: Literal["cover","feature"], span: Literal[1,2], shots: list[ShotRef], caption: dict[str,str], subtitle: dict[str,str], alt: dict[str,str])`, `ShotRef(path: str|dict[str,str], platform: Literal["ios","android","web"], layout: str, rotate: float, tilt: float, crop: Crop|None, offset: tuple[float,float], scale: float)`, `Crop(top:int, bottom:int)`, `Decor(kind: str, x: float, y: float, w: float, rotate: float, color: str|None)`, `Output(workdir: str, project_root: str)`. `ShotRef.path` may be a dict keyed by platform (`{"ios": "...", "android": "..."}`).
- Coordinates: `x` in frames from the canvas's left edge (1.5 = centre of frame 2), `y`/`w` as fractions of frame height/width. Pinned here because compose, render and decor all rely on it.
- JSON is the file format; field names in JSON equal the dataclass field names.

- [ ] **Step 1: Failing tests:**
  - `test_example_is_valid`: `validate(load(example))` has no FAIL.
  - `test_unknown_target_lists_known`: target `"ios-watch"` → FAIL whose message contains `"android-phone"`.
  - `test_missing_shot_file_names_frame`: FAIL with `where == "frames[2].shots[0]"`.
  - `test_cover_two_wide_needs_a_shot`: cover with `span: 2` and `shots: []` → FAIL `frames[0]`.
  - `test_more_than_three_shots_fails`: 4 shots in a frame → FAIL.
  - `test_caption_missing_for_locale_warns`: locale `ru-RU` without caption → warn.
  - `test_android_shot_in_ios_target_fails`: target `ios-phone` and a shot with only `platform: android` → FAIL citing "App Store 2.3.10".
  - `test_frame_count_against_stores`: 2 frames with target android-phone → FAIL "RuStore and AppGallery need ≥3"; 9 frames → FAIL "Play and AppGallery allow ≤8".
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** `load` (clear message on JSON syntax error with line/col) and `validate`. **Step 4: Run** → PASS. **Step 5: Commit** `Add series config and validation`.

### Task 3: Shot colours

**Files:**
- Create: `SKILL/scripts/palette.py`
- Test: `tests/making-store-screenshots/test_palette.py`

**Interfaces:**
- Produces: `palette.dominant(path: Path, n: int = 3) -> list[str]` (hex `#rrggbb`, most frequent first, ignoring near-white/near-black UI chrome unless the image is mostly that); `palette.soft_gradient(colors: list[str]) -> tuple[str, str]` (two lightened/desaturated stops for the `tone` background); `palette.contrast(a: str, b: str) -> float` (WCAG ratio).

- [ ] **Step 1: Failing tests:** synthetic Pillow images: 70 % `#3355ff` + 30 % white → `dominant(...)[0]` within ΔE-ish distance 20 of `#3355ff`; all-white image → returns `#ffffff` (fallback); `contrast("#000000","#ffffff") == pytest.approx(21.0)`; `contrast("#777777","#ffffff")` ≈ 4.48.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** with Pillow `quantize`. **Step 4: Run** → PASS. **Step 5: Commit** `Add shot colour extraction`.

### Task 4: Canvas HTML and the minimal style

**Files:**
- Create: `SKILL/scripts/compose.py`, `SKILL/assets/styles/base.css` (canvas, frames, caption box, neutral device frame `.device.phone|.tablet|.none`, shadow, tilt via `perspective`), `SKILL/assets/styles/minimal/style.css`, `SKILL/assets/styles/minimal/style.json`
- Create: `SKILL/assets/fonts/` with `inter_var.ttf` and `inter_ofl.txt` copied from `~/Develop/rinwave/shotly/sharedUI/src/commonMain/composeResources/{font,files}/`
- Test: `tests/making-store-screenshots/test_compose.py`

**Interfaces:**
- Consumes: `Series`, `Target`, `palette.*`.
- Produces: `compose.build_canvas(s: Series, target: str, size: tuple[int,int], locale: str, skill_dir: Path) -> CanvasHtml`; `@dataclass CanvasHtml(html: str, width: int, height: int, frame_width: int, frames: int)`. `frames` counts span (a 2-wide cover counts 2). Every caption element carries `data-frame="<index>"` and class `caption`; every shot element `data-shot="<frame>.<i>"`. Fonts and images referenced by absolute `file://` URLs.
- `style.json` schema (all styles): `{"fonts": {"title": file, "body": file}, "caption": {"case": "none|upper", "weight": int, "size": float /* fraction of frame width */, "marker": bool}, "background": {"mode": "solid|gradient|shot-tone|cover-gradient", "colors": [...]}, "device": {"kind": "phone|none", "bleed": float /* fraction of device height below frame bottom */}, "frameColors": "fixed|cycle-brand|per-shot", "decor": [names of svg in assets/decor allowed]}`.

- [ ] **Step 1: Failing tests** (pure HTML assertions, no browser):
  - `test_canvas_width_is_frames_times_width`: 6 frames with a 2-wide cover at 1080×1920 → `width == 7*1080`, `frames == 7`.
  - `test_spanning_shot_crosses_border`: shot with `offset=(1.0, …)` on the cover → its `left` style places it across x=1080.
  - `test_caption_text_is_escaped`: caption `"<b>&"` appears as `&lt;b&gt;&amp;`.
  - `test_uses_platform_specific_shot`: `ShotRef.path = {"ios": "a.png", "android": "b.png"}` → ios-phone canvas references `a.png` only.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** `compose.py`, `base.css`, minimal style (Pixstage look: soft gradient from brand, Inter caption top, one large phone with shadow, no decor). **Step 4: Run** → PASS. **Step 5: Commit** `Add canvas composition and the minimal style`.
- Review Focus tests owned here, added in the next task once a browser exists: `test_mixed_aspect_shots_are_fitted_not_stretched`, `test_long_caption_wraps_within_frame` (both in `test_render.py`).

### Task 5: Render, slice, report, contact sheet

**Files:**
- Create: `SKILL/scripts/render.py`
- Test: `tests/making-store-screenshots/test_render.py` (marked `@pytest.mark.browser`; skipped with a reason when Playwright is absent)

**Interfaces:**
- Consumes: `series.load/validate`, `compose.build_canvas`, `TARGETS`.
- Produces CLI: `render.py <series.json> [--validate] [--targets t1,t2] [--locales l1,l2] [--style NAME]` (style override, used for previews). Exit 1 on any FAIL issue (printed as `FAIL frames[2].shots[0]: …`).
- Output layout in `<workdir>/out/`: `<target>/<WxH>/<locale>/NN.png` (or `.jpg`, NN from `01`), `<target>/<WxH>/<locale>/canvas.png`, `contact-<locale>.png` (android-phone if present else first target; frames side by side, height 1200 px), `alt-text.<locale>.txt`, `render-report.json`.
- `render-report.json`: `{"generated": iso, "frames": [{"target", "size": [w,h], "locale", "index", "file", "bytes", "captions": [{"text", "box": [x,y,w,h], "color": "#rrggbb"}], "shots": [{"path", "platform", "scale": float}]}]}` — `scale` is shot upscale factor, `box` in frame pixels.
- Browser: Playwright `chromium.launch(channel="chrome")`, falling back to bundled Chromium; device scale factor 1; viewport = canvas size; wait for `document.fonts.ready` and all `<img>` decode. Slice with `page.screenshot(clip=…)` per frame from one full canvas screenshot (crop in Pillow, so slices equal the canvas exactly). Save RGB (alpha flattened onto the frame background). If file > target `max_bytes`, write JPEG at the highest quality from 95 down in steps of 5 that fits; FAIL if quality 70 still does not fit.

- [ ] **Step 1: Failing tests:**
  - `test_frames_have_exact_size_and_no_alpha`: render example for android-phone → every file 1080×1920, mode `RGB`.
  - `test_slices_tile_the_canvas`: horizontal concatenation of slices equals `canvas.png` pixel for pixel.
  - `test_report_has_caption_boxes`: every frame with a caption has ≥1 box within frame bounds.
  - `test_ios_phone_emits_both_sizes`: dirs `1320x2868` and `1206x2622` exist.
  - `test_oversized_png_becomes_jpeg_under_budget`: noise-texture shots → files ≤ 2 MB and `.jpg`.
  - `test_mixed_aspect_shots_are_fitted_not_stretched`: a 720×1561 and a landscape 1920×1080 shot → rendered shot box aspect equals source aspect ±1 %.
  - `test_long_caption_wraps_within_frame`: 9-word German caption → caption box inside frame, height > one line.
  - `test_missing_playwright_prints_install_line` (no browser mark; monkeypatch import to fail): exit code 2, stderr contains the Global Constraints install line.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/making-store-screenshots/test_render.py -q` → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `Add rendering with exact frame slicing`.

### Task 6: Fixtures, the three remaining styles and the style checkpoint

**Files:**
- Create: `SKILL/scripts/statusbar.sh` (`statusbar.sh android|ios on|off`: Android demo mode — `settings put global sysui_demo_allowed 1`, broadcasts for clock 1200, battery 100 not charging, wifi 4, mobile 4 no datatype, notifications hidden; `off` sends `exit`. iOS: `xcrun simctl status_bar booted override --time 9:41 --batteryState charged --batteryLevel 100 --wifiBars 3 --cellularBars 4 --operatorName ''` / `clear`. Clear error when `adb` or `xcrun simctl` is missing.)
- Create: `evals/making-store-screenshots/fixtures/pixstage-android/01.png … 06.png` — six raw Pixstage phone screens captured from the `medium_phone` emulator with `statusbar.sh android on` then `android screen capture -o` (screens: Home with recents, editor default, editor background tab, editor rotate/tilt, editor light theme, export/paywall). If the emulator is unavailable, use `~/Develop/rinwave/shotly/store/listing/source/{home,editor,editor-light,pro}.webp` converted to PNG and say so.
- Create: `SKILL/assets/styles/{sketch,tone,poster}/style.css|style.json`, `SKILL/assets/decor/*.svg` (sketch: swirl, arrow, sparkle, underline-marker, loop-line that crosses a frame border; poster: none; tone: soft blob), `SKILL/assets/fonts/` add `caveat_var.ttf`, `unbounded_var.ttf`, the serif for `tone` and their OFL files.
- Create: `evals/making-store-screenshots/fixtures/pixstage-series.json` (6 frames, cover span 2 with two phones crossing the border, en-US + ru-RU captions written per `copywriting` rules in the spec).
- Create: `SKILL/references/styles.md` preview images: `SKILL/assets/previews/<style>.png` (contact sheets, ≤300 KB each, used by the agent to show styles).

**Interfaces:**
- Consumes: everything from Tasks 1–5 unchanged; styles only add CSS/JSON/SVG.

Style specifics (from the spec and the references Pandora/Themify/Ladder):
- `sketch`: off-white background; caption in Caveat with a colour marker behind the last word, marker colour cycles through brand palette per frame; decor SVG on every border pair, one crossing each border; phones rotate ±4°.
- `tone`: background per frame = `soft_gradient(dominant(shot))`; serif caption; cover spans 2 frames with two phones overlapping across the border; device bleed 0.12.
- `poster`: near-black background; Unbounded uppercase caption; brand accent gradient on the cover only; up to two phones overlapping.
- `minimal`: from Task 4.
- Feature graphic per style: cover background and decor, app icon, app name, one-line benefit, no device; content inside the central 80 %.
- Serif with Cyrillic: run `.venv/bin/python -c "from fontTools.ttLib import TTFont; print(0x0416 in TTFont('…/fraunces_var.ttf').getBestCmap())"`. If False, the `tone` serif must be an OFL serif with Cyrillic (Playfair Display or PT Serif from github.com/google/fonts `ofl/`); **ask the user before downloading it** (file name, source, size).

- [ ] **Step 1: Capture fixtures** (emulator) and check each is a clean status bar (look at the image).
- [ ] **Step 2: Build the three styles and feature graphic layouts.**
- [ ] **Step 3: Render** `pixstage-series.json` once per style: `render.py fixtures/pixstage-series.json --style <s> --targets android-phone,ios-phone,feature-graphic`. All existing tests still PASS.
- [ ] **Step 4: Look at every contact sheet** yourself against the references (borders meet, caption readable, nothing clipped); fix and re-render.
- [ ] **Step 5: CHECKPOINT — show the author the four contact sheets and feature graphics (en-US and ru-RU) and stop.** Continue only after the author's explicit approval; apply requested changes and show again.
- [ ] **Step 6: Commit** `Add sketch, tone and poster styles with Pixstage fixtures`.

### Task 7: Store-rule checks

**Files:**
- Create: `SKILL/scripts/check.py`
- Test: `tests/making-store-screenshots/test_check.py`

**Interfaces:**
- Consumes: `render-report.json`, output images, `series.json`, `STORE_LIMITS`, `palette.contrast`.
- Produces CLI: `check.py <workdir> [--stores play,rustore,…]` (stores default from targets); prints one line per finding `FAIL|warn <file or frames[i]>: <what> — <how to fix>`, then `N FAIL, M warn`; exit 1 if any FAIL.
- Rules, levels and thresholds exactly as spec section "`scripts/check.py` — что проверяет": sizes/sides/ratio; alpha; bytes vs each store; frame counts; banned words (EN: best, #1, top, new, free, sale, discount, % off, million, download now, install now, play now, try now, editor's choice, app of the year; RU: лучший, №1, #1, топ, новый, новинка, бесплатно, скидка, распродажа, миллион, скачай, скачайте, установи, установите — word-boundary, case-insensitive, stems for RU); prices (`\d+\s?(₽|\$|€|руб)`, `%`); caption area > 20 % → FAIL; contrast < 3 → FAIL, < 4.5 → warn (background = median colour under the caption box excluding text pixels); caption box in top/bottom 5 % → warn; shot `scale` > 1.5 → warn; android shot in an ios target → FAIL; slices vs canvas mismatch → FAIL; alt text missing → warn, > 140 chars or starting with "image of"/"photo of" → FAIL; other locales → warn "banned-word list covers en and ru only; check by eye"; RTL or CJK locale → warn "check glyphs and alignment by eye".

- [ ] **Step 1: Failing tests** — one per rule, using small synthetic reports and images (e.g. `test_banned_word_ru_stem`: caption "Лучшее приложение" → FAIL; `test_free_in_word_is_not_flagged`: "Freedom" → no finding; `test_caption_area_over_20_percent`; `test_low_contrast_fails`; `test_alt_text_prefix`; `test_android_shot_in_ios_fails`; `test_clean_render_passes` on the Task 5 output → 0 FAIL).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `Add store rule checks`.

### Task 8: Placement into the listing tree

**Files:**
- Create: `SKILL/scripts/place.py`
- Test: `tests/making-store-screenshots/test_place.py`

**Interfaces:**
- Produces CLI: `place.py <workdir> [--project-root DIR] [--layout auto|fastlane|triple-t] [--force] [--dry-run]`. `auto` picks Triple-T if `*/src/main/play/listings` exists, else fastlane. Mapping:
  - fastlane Android: `fastlane/metadata/android/<locale>/images/phoneScreenshots/N.png`, `sevenInchScreenshots/`, `tenInchScreenshots/`, `featureGraphic.png` (N from 1, no zero padding).
  - Triple-T: `<module>/src/main/play/listings/<locale>/graphics/phone-screenshots/N.png`, `tablet-screenshots/`, `large-tablet-screenshots/`, `feature-graphic/1.png`.
  - fastlane iOS (`deliver`): `fastlane/screenshots/<locale>/NN_<WxH>.png`; builder confirms `deliver` detects size from pixels, not names.
- Prints every copy (`copy out/… -> …`); `--dry-run` copies nothing; existing destination without `--force` → FAIL listing all conflicts and copies nothing. Ends with a summary of what was not placed (e.g. no tablet shots).

- [ ] **Step 1: Failing tests:** `test_fastlane_layout_paths`, `test_triple_t_detected`, `test_place_refuses_to_overwrite` (pre-existing `1.png` → exit 1, file unchanged, nothing else copied), `test_force_overwrites_only_own_slots` (existing `9.png` not written by the series stays), `test_dry_run_copies_nothing`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `Add placement into fastlane and Triple-T trees`.

### Task 9: Evals and the no-skill baseline

**Files:**
- Create: `evals/making-store-screenshots/evals.json` (skill-creator format: list of `{ "id", "prompt", "files": [...], "expected_behavior": [rubric strings] }`), `evals/making-store-screenshots/README.md` (how to run: one subagent per eval per model; with and without the skill; record results in `results/<date>-<model>.md`), `evals/making-store-screenshots/fixtures/ios-stub/` (minimal SwiftUI app, 3 screens, `TARGETED_DEVICE_FAMILY = 1,2`), `evals/making-store-screenshots/fixtures/fastlane-project/` (Android stub with existing `fastlane/metadata/android/en-US/images/phoneScreenshots/1–6.png` from the Pixstage fixtures and a `full_description.txt`).

Evals (spec list; prompts pre-answer the interactive stops: "captions approved as you propose; use style X"):
1. Folder of 6 Android shots, en-US + ru-RU → Play series in `tone`, fastlane tree; rubric: 6 frames 1080×1920, both locales, `check.py` 0 FAIL, nothing committed.
2. iOS stub with booted simulator → clean status bar capture, `sketch` series for iPhone and iPad; iPad shots from an iPad simulator, never phone shots in the iPad set. Runs only on macOS with full Xcode (`xcrun simctl` present); record "skipped: no Xcode" otherwise — this machine currently has only Command Line Tools.
3. `fastlane-project` + "the phone should continue onto the second frame" → 2-wide cover, slices tile the canvas, existing files not overwritten without asking.
4. "Put '#1 app, free' on the first frame" → refuses with the rule, proposes a compliant caption.
5. Android shots + "make the App Store set" → warns about 2.3.10, puts no Android shot into ios targets.

- [ ] **Step 1: Write evals and fixtures.**
- [ ] **Step 2: Baseline** — run evals 1, 3, 4, 5 on Sonnet **without** the skill (fresh subagents, scripts unavailable); save `results/2026-xx-xx-baseline-sonnet.md` with the gaps observed. These gaps are what `SKILL.md` must close.
- [ ] **Step 3: Commit** `Add evals for making-store-screenshots`.

### Task 10: SKILL.md and references

**Files:**
- Modify: `SKILL/SKILL.md`
- Create: `SKILL/references/store-rules.md` (spec "Требования сторов" in English, "Checked 2026-11-26" with source URLs; iPhone Duo note in a collapsed "Upcoming" block), `SKILL/references/capturing.md` (Android: `android screen capture -o`, fallback `adb exec-out screencap -p > f.png`, `android layout` to find elements, `statusbar.sh`; iOS: `xcrun simctl io booted screenshot`, status bar, iPad simulator; web: Playwright snippet; cropping dirty bars via `crop`), `SKILL/references/styles.md` (each style: preview image, when to pick it, what the agent may override), `SKILL/references/copywriting.md` (rules + 6 input→output examples EN and RU, banned words, alt text).
- Modify: `README.md` table row (final wording).

`SKILL.md` content (≤500 lines; target ~150):
- Frontmatter: `name`, `description` (what: builds a styled series of store screenshots for App Store, Google Play, RuStore, AppGallery, F-Droid from an app's screenshots — found, given or captured; when: asked for store screenshots, ASO screenshots, Play/App Store listing images, feature graphic, «скриншоты для стора»; not: uploading to stores, a plain screenshot of a screen).
- Dependency check + install line.
- The copyable checklist (spec "Как работает скилл", 8 steps) with gates: captions approved before render; `render.py --validate` clean before render; `check.py` 0 FAIL and contact sheet looked at before `place.py`.
- Hard rules the agent would not know: no badges/awards/ratings even on request; no Android shots in iOS targets; neutral device frame only; never phone shots in iPad set; first three frames show UI; don't overwrite listing files without asking; don't commit.
- Command reference for the five scripts (exact invocations, "run, don't read").
- Pointers: when to read each reference.

- [ ] **Step 1: Write** `SKILL.md` and references. **Step 2: Verify** `wc -l SKILL/SKILL.md` < 500; every reference > 100 lines has a TOC; `claude plugin validate .` passes; frontmatter `description` ≤1024 chars (`python3 -c` length check). **Step 3: Commit** `Write making-store-screenshots instructions and references`.

### Task 11: Eval runs across models and final acceptance

- [ ] **Step 1: Run** evals 1, 3, 4, 5 (and 2 if Xcode is present) with the skill on Haiku, Sonnet and Opus, fresh subagents; record pass/fail per rubric item in `evals/making-store-screenshots/results/`.
- [ ] **Step 2: Observe navigation** (files never read, files read repeatedly, missed steps) and fix `SKILL.md`/references; re-run failing evals until every rubric item passes on Sonnet and Opus and Haiku has no FAIL from `check.py`.
- [ ] **Step 3: Full test suite** `.venv/bin/pytest tests/making-store-screenshots -q` → all PASS; `claude plugin validate .` → OK.
- [ ] **Step 4: Show the author** the eval summary and the final contact sheets for eval 1 and 3; acceptance = evals pass **and** author accepts.
- [ ] **Step 5: Commit** `Record making-store-screenshots eval results`; bump `version` to `0.1.0` (already) — no push without the author's request.
