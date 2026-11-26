# Store rules for screenshots

Checked 2026-11-26 against the official pages linked in each section. `scripts/targets.py` and
`scripts/check.py` encode these numbers; change them together when a store changes its rules.

## Contents

- [App Store](#app-store)
- [Google Play](#google-play)
- [RuStore](#rustore)
- [Huawei AppGallery](#huawei-appgallery)
- [F-Droid](#f-droid)
- [What this means for a series](#what-this-means-for-a-series)
- [Upcoming](#upcoming)

## App Store

Sources: [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications),
[App Review Guidelines 2.3](https://developer.apple.com/app-store/review/guidelines/),
[Marketing guidelines](https://developer.apple.com/app-store/marketing/guidelines/).

- Required: at least one screenshot for iPhone with Dynamic Island (medium display), 1206×2622 or 1179×2556;
  iPad 13" (2064×2752 or 2048×2732, landscape too) when the app runs on iPad. Other sizes are scaled from these.
- 1–10 screenshots per display size; JPEG or PNG; no alpha channel or transparency.
- 2.3.3: show the app in use, not only title art, a login page or a splash screen. Text overlays are fine.
- 2.3.7 and 2.3.14: no prices, terms, discounts or unverifiable claims.
- 2.3.8: content suitable for 4+, even when the app is rated higher.
- 2.3.9: fictional account data only; you need the rights to everything shown.
- 2.3.10: no names, icons or imagery of other mobile platforms or app stores. Never put Android shots,
  an Android status bar or the word "Android" into an App Store set.
- Marketing guidelines: do not draw, simulate or modify Apple devices; only the official App Store badge;
  status bar with full signal, Wi-Fi and battery. The skill's neutral device frame has no island, notch or
  buttons for this reason.

## Google Play

Sources: [Preview assets](https://support.google.com/googleplay/android-developer/answer/9866151),
[Metadata policy](https://support.google.com/googleplay/android-developer/answer/9898842).

- Format: JPEG or 24-bit PNG without alpha; each side 320–3840 px; long side at most 2.3× the short side;
  up to 8 MB each.
- Phone: 2–8 screenshots. To be eligible for recommendations: at least 4 at 1080 px or more (portrait ≥1080×1920).
- Tablets 7" and 10" (large screens): at least 4, sides 1080–7680 px, 9:16 or 16:9.
- Foldables: 3–8, sides 960–3840 px; at least one 1:1 inner-screen shot, plus a 4:3 landscape inner-screen
  shot and a 10:16 portrait outer-screen shot.
- Feature graphic: exactly 1024×500, no alpha; key content near the centre; no devices or badges.
- Caption: at most 20 % of the image; no small text; no busy background behind text.
- Forbidden in images: "Best", "#1", "Top", "New", "Discount", "Sale", "Free", "Million downloads", rankings,
  awards, testimonials; calls to action ("Download now", "Install now", "Play now", "Try now"); time-limited
  content; Google Play or other store badges; third-party logos or celebrities without permission.
- Clean status bar: no notifications or carrier name, full battery, Wi-Fi and signal.
- No blurry, stretched or over-compressed images; correct orientation.
- UI broken across images is allowed; the first three images should show the UI.
- Localize taglines. Alt text: 140 characters or less, not starting with "image of" or "photo of".

## RuStore

Source: [Публикация приложения](https://www.rustore.ru/help/developers/publishing-and-verifying-apps/app-publication/).

- Phone screenshots are required; at least 3 for each device type uploaded; up to 10 per upload.
- PNG or JPG; at most 3 MB on phones and 5 MB on tablets; at most 2160×3840.
- Ratio 16:9 (or 9:16). Anything else is stretched or cropped, so the skill uses only 9:16 and 16:9.
- Without tablet screenshots, phone screenshots are shown on tablets too.

## Huawei AppGallery

Source: [Specifications for app visual assets](https://developer.huawei.com/consumer/en/doc/app/agc-help-app-material-requirement-0000001146534651).

- 3–8 screenshots; PNG or JPG up to 2 MB; sides 320–3840 px; the help shows 450×800 portrait.
- A language without its own assets shows the default language's.

## F-Droid

Source: [Descriptions, graphics and screenshots](https://f-droid.org/docs/All_About_Descriptions_Graphics_and_Screenshots/).

- PNG or JPEG in `fastlane/metadata/android/<locale>/images/phoneScreenshots/1.png` and so on, or the
  Triple-T tree. No count or size limits.

## What this means for a series

- One 9:16 Android set at 1080×1920 serves Play, RuStore, AppGallery and F-Droid. AppGallery's 2 MB is the
  tightest limit; render.py writes JPEG when a PNG is heavier.
- 6 frames by default: at least 4 for Play recommendations, at least 3 for RuStore and AppGallery, at most 8
  for Play and AppGallery.
- The App Store set is separate and made of iOS (or platform-neutral) shots only.
- Tablet and foldable sets use tablet and foldable shots only, never phone shots.

## Upcoming

<details>
<summary>iPhone Duo (from April 2027)</summary>

Apps built with the iOS 27.1 SDK or later will need iPhone Duo screenshots: outer display 1398×2034 (or
landscape), inner display 2007×2853 (or landscape). Not a target in this skill yet.
</details>
