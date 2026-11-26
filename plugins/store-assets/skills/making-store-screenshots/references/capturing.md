# Capturing shots

## Contents

- [Android](#android)
- [iOS](#ios)
- [Web](#web)
- [Shots from a folder](#shots-from-a-folder)

Before any capture, clean the status bar; after the last capture, restore it. A clean bar is a store rule
(full battery and signal, no notifications, no carrier).

## Android

```bash
<skill-dir>/scripts/statusbar.sh android on          # demo mode: 12:00, full battery and signal
android screen capture -o shots/android/01.png       # Android CLI, if installed
adb exec-out screencap -p > shots/android/01.png     # otherwise
<skill-dir>/scripts/statusbar.sh android off
```

- Pick the device: `adb devices`; pass `-s <serial>` to adb and the serial as the third argument of
  `statusbar.sh`. Phones: any 1080×2400-class emulator. Tablets: a tablet emulator (Pixel Tablet). Foldables:
  a foldable emulator unfolded for inner-screen shots (`adb emu unfold`), folded for outer-screen shots.
- Get to a screen: `android layout` prints the UI tree with `content-desc` and centre coordinates; tap with
  `adb shell input tap X Y`; launch an activity with `adb shell am start -n <package>/<activity>` (a debug build
  may have extra launchers, such as LeakCanary's). Deep links: `adb shell am start -a android.intent.action.VIEW -d <uri>`.
- Look at every capture before using it: wrong screen, a dialog, a keyboard, a toast, a loading state.
- Real data that is not the user's own (other apps' icons in a gallery, a real person's name) must not appear:
  use another screen or seed the app with fictional data.
- If an emulator has a manual `wm size` override, it changes the capture size: note it, reset it with
  `adb shell wm size reset` for the capture, and put it back afterwards.

## iOS

Needs full Xcode (`xcrun simctl`); Command Line Tools alone are not enough.

```bash
<skill-dir>/scripts/statusbar.sh ios on              # 9:41, full bars and battery, no carrier
xcrun simctl io booted screenshot shots/ios/01.png
<skill-dir>/scripts/statusbar.sh ios off
```

- iPhone shots from an iPhone simulator; iPad shots from an iPad simulator. Never use phone shots in an iPad
  set: Apple rejects it.
- Navigate with deep links (`xcrun simctl openurl booted <url>`) or launch arguments, or ask the user to bring
  the screen up.

## Web

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 412, "height": 915}, device_scale_factor=2.625)  # 1080x2400 phone
    page.goto("http://localhost:3000/screen")
    page.screenshot(path="shots/web/01.png")
```

A web app's shots are platform-neutral (`"platform": "web"`) and may go into both sets when they show no
Android or iOS chrome.

## Shots from a folder

- Check each image: size, whether it is a phone, tablet or foldable shot, the status bar, stray dialogs.
- A dirty status bar or navigation bar can be cut off with `"crop": {"top": <px>, "bottom": <px>}` on the shot.
- Shots smaller than about two thirds of the target width look soft; check.py warns above 1.5× upscale.
