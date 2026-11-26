#!/usr/bin/env bash
# Clean status bar for store screenshots, and back.
#   statusbar.sh android on|off [adb serial]
#   statusbar.sh ios on|off [simulator udid, default: booted]
# Stores ask for a full battery, full signal, no notifications and no carrier name.
set -euo pipefail

platform="${1:-}"; mode="${2:-}"; device="${3:-}"
usage() { echo "usage: statusbar.sh android|ios on|off [device]" >&2; exit 2; }
[[ "$mode" == on || "$mode" == off ]] || usage

case "$platform" in
  android)
    command -v adb >/dev/null || { echo "adb not found: install Android platform-tools and add them to PATH" >&2; exit 2; }
    adb_cmd=(adb); [[ -n "$device" ]] && adb_cmd+=(-s "$device")
    "${adb_cmd[@]}" get-state >/dev/null 2>&1 || { echo "no Android device: start an emulator or connect a phone (adb devices)" >&2; exit 2; }
    demo() { "${adb_cmd[@]}" shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }
    if [[ "$mode" == on ]]; then
      "${adb_cmd[@]}" shell settings put global sysui_demo_allowed 1
      demo enter
      demo clock -e hhmm 1200
      demo battery -e level 100 -e plugged false
      # fully=true drops the "no internet" mark; an empty datatype hides "3G"/"LTE".
      demo network -e wifi show -e level 4 -e fully true
      demo network -e mobile show -e level 4 -e datatype '' -e fully true
      demo notifications -e visible false
      echo "android status bar: demo mode on (12:00, full battery and signal, no notifications)"
    else
      demo exit
      echo "android status bar: demo mode off"
    fi
    ;;
  ios)
    xcrun simctl help >/dev/null 2>&1 || { echo "xcrun simctl not found: install full Xcode (Command Line Tools are not enough)" >&2; exit 2; }
    target="${device:-booted}"
    if [[ "$mode" == on ]]; then
      xcrun simctl status_bar "$target" override --time 9:41 --dataNetwork wifi --wifiMode active --wifiBars 3 \
        --cellularMode active --cellularBars 4 --operatorName '' --batteryState charged --batteryLevel 100
      echo "ios status bar: overridden (9:41, full battery and signal, no carrier)"
    else
      xcrun simctl status_bar "$target" clear
      echo "ios status bar: cleared"
    fi
    ;;
  *) usage ;;
esac
