# Evals for making-store-screenshots

`evals.json` holds five scenarios. Each runs in a fresh scratch folder built from its `setup` steps, in a fresh
agent session, once with the skill installed and once without it (the baseline). Results go to
`results/<date>-<model>[-baseline].md`: one line per expectation, pass or fail, plus what the agent did that
was surprising (files it never read, files it read repeatedly, steps it skipped).

Run them on Haiku, Sonnet and Opus. Eval 2 needs macOS with full Xcode (`xcrun simctl`) and XcodeGen; where
those are missing, record it as skipped.

`fixtures/` holds the inputs: six raw Pixstage phone screenshots (`pixstage-android/`, captured from an
emulator with a clean status bar), tablet and foldable captures, a stub Android project with real listing
text, a SwiftUI stub for eval 2, and `pixstage-series.json` used for the style previews.
`style-review/` holds the contact sheets the author approved on 2026-11-26.
