# With the skill — Haiku, Sonnet, Opus, 2026-11-26

Eval 2 skipped on all models: this machine has Command Line Tools only (no `xcrun simctl`, no XcodeGen).

| Eval | Haiku | Sonnet | Opus | Baseline (Sonnet, no skill) |
|---|---|---|---|---|
| 1 android-folder-tone | PASS | PASS | PASS | partial: no feature graphic, one locale looked at |
| 3 fastlane-panorama-cover | PASS | PASS | PASS | partial: never placed, no approval of captions |
| 4 refuses-banned-claims | PASS | PASS | PASS | PASS (refused), files not placed |
| 5 android-shots-for-app-store | PASS | PASS | PASS | **FAIL: built a rejectable App Store set** |

All rendering runs ended with `check.py` at `0 FAIL, 0 warn`, opened the contact sheets, and placed files only
when nothing would be overwritten (eval 3 stopped at place.py's conflict list, originals untouched).

## Findings fixed after this round

- `output.workdir` / `project_root` resolved confusingly; with the example, output landed in a doubled path
  (all six rendering runs hit it). Now both resolve against the series file; `out/` defaults to the series
  folder and the project root is found by walking up (`series.output_dirs`, `find_project_root`).
- `series.example.json` used `layout` and explicit cover offsets; now `form`, auto cover layout and `alt`.
- Commands said `python3` while dependencies may live in a venv; SKILL.md now uses one `$PY`.
- No path for "store requested but platform missing"; added to step 1.
- No tell-tale signs of Android vs iOS shots; added to step 2.
- Restyling shots that sit in the listing tree: copy them out before placing (Opus).
- "Ask which to use" read as if a forbidden caption were an option; reworded.
- `palette.py` had no command line; added.
- Working files written outside the folder; SKILL.md now says to keep scratch files in the series folder.

## Deferred

- A 2-wide cover repeats its alt text on both slots.
- Locale-specific shots need one series per locale.
- Shots showing locked Pro features: no rule; left to the user.
