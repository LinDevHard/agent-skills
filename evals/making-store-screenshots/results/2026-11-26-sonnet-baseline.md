# Baseline without the skill — Sonnet, 2026-11-26

| Eval | Outcome | Gaps the skill must close |
|---|---|---|
| 1 android-folder-tone | 6+6 frames 1080x1920 RGB PNG in fastlane phoneScreenshots (named 01.png); Georgia caption, tinted gradient, rounded shot without a device | No feature graphic; looked at the ru sheet only; tone tints came out almost identical; no RuStore/AppGallery limits considered; Georgia is a system font (not bundled, not OFL) |
| 3 fastlane-panorama-cover | 7 frames; one phone centred on the seam of a 2160-wide canvas, halves verified pixel by pixel | Wrote to a new styled/ folder instead of the listing (never placed); captions not shown for approval; reordered shots so the home screen went last; no feature graphic |
| 4 refuses-banned-claims | Replaced "#1 … free!" with a benefit caption and explained the Play rules | Did not ask before replacing; files left in out/, not in the listing tree; no feature graphic; plain indigo gradient |
| 5 android-shots-for-app-store | Made 24 App Store images from the Android shots, then warned they would likely be rejected (2.3.10) | **Produced a rejectable set instead of stopping**; called 6.9" the required size (it is 6.3" Dynamic Island medium); 6.5" size chosen, not the required one |

## Gaps to close in SKILL.md

1. Stop when the shots cannot go into a set (Android shots for the App Store) instead of producing it.
2. Required sizes and per-store limits come from the target table, not memory.
3. Always the feature graphic for Play; always place into the listing tree, asking before overwriting.
4. Captions shown for approval before rendering; every locale's contact sheet looked at.
5. Bundled fonts and the device frame keep the look consistent and licensed.
