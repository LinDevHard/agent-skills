#!/usr/bin/env python3
"""Render a series to store-ready frames.

    render.py <series.json> [--validate] [--targets t1,t2] [--locales l1,l2] [--style NAME]

Writes <workdir>/out/<target>/<WxH>/<locale>/NN.png|jpg, canvas.png, contact-<locale>.png,
alt-text.<locale>.txt and render-report.json. Exit codes: 0 ok, 1 series has FAIL issues, 2 missing
dependency or browser.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

INSTALL_LINE = (
    "python3 -m venv .venv && .venv/bin/pip install playwright pillow && .venv/bin/playwright install chromium"
)
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

CONTACT_HEIGHT = 1200  # Contact sheet height: enough to judge seams and captions by eye.
CHUNK = 4000  # Screenshot wide canvases in chunks: Chrome caps a single capture at 16384 px.
JPEG_QUALITIES = range(95, 65, -5)  # Highest first; below 70 artefacts show on UI text.
ALT_MAX = 140  # Play: alt text of 140 characters or less.


def _need_deps():
    try:
        import PIL  # noqa: F401
        import playwright.sync_api  # noqa: F401
    except ImportError as e:
        print(f"Missing dependency ({e.name or e}). Install into a local venv:\n  {INSTALL_LINE}\n"
              "(the last step is only needed when Google Chrome is not installed)", file=sys.stderr)
        sys.exit(2)


GEOMETRY_JS = """() => {
  const box = el => { const r = el.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; };
  return {
    captions: [...document.querySelectorAll('.caption')].map(el => {
      const h1 = el.querySelector('h1') || el;
      const cs = getComputedStyle(h1);
      const b = box(el);
      return {frame: +el.dataset.frame, text: el.innerText.trim(), box: b, color: cs.color,
              line_height: parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2,
              overflow: h1.scrollWidth > el.clientWidth + 1, broken_word: el.dataset.broken === '1',
              max_bottom: el.dataset.maxH ? b[1] + (+el.dataset.maxH) : document.getElementById('canvas').offsetHeight};
    }),
    shots: [...document.querySelectorAll('.shot')].map(el => ({
      key: el.dataset.shot, scale: +el.dataset.scale, platform: el.dataset.platform,
      src: el.querySelector('img').getAttribute('src'), box: box(el), screen: box(el.querySelector('.screen'))})),
  };
}"""


def _rgb_hex(css: str) -> str:
    nums = [float(v) for v in css[css.index("(") + 1 : css.index(")")].replace("/", ",").split(",")[:3]]
    return "#{:02x}{:02x}{:02x}".format(*(round(n) for n in nums))


def _launch(p):
    try:
        return p.chromium.launch(channel="chrome")
    except Exception:
        try:
            return p.chromium.launch()
        except Exception as e:
            print(f"No browser for rendering: {e}\nInstall Chromium for Playwright:\n"
                  "  .venv/bin/playwright install chromium", file=sys.stderr)
            sys.exit(2)


def _capture(page, html_path: Path, width: int, height: int):
    from PIL import Image

    page.set_viewport_size({"width": min(width, CHUNK), "height": height})
    page.goto(html_path.as_uri())
    page.evaluate("document.fonts.ready")
    page.evaluate("Promise.all([...document.images].map(i => i.decode().catch(() => null)))")
    page.evaluate("window.fitCaptions && window.fitCaptions()")
    geometry = page.evaluate(GEOMETRY_JS)
    canvas = Image.new("RGB", (width, height), "white")
    for x in range(0, width, CHUNK):
        w = min(CHUNK, width - x)
        png = page.screenshot(clip={"x": x, "y": 0, "width": w, "height": height}, full_page=True)
        canvas.paste(Image.open(io.BytesIO(png)).convert("RGB"), (x, 0))
    return canvas, geometry


def _save(img, path_stem: Path, max_bytes: int) -> Path:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    if buf.tell() <= max_bytes:
        path = path_stem.with_suffix(".png")
        path.write_bytes(buf.getvalue())
        return path
    for q in JPEG_QUALITIES:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= max_bytes:
            path = path_stem.with_suffix(".jpg")
            path.write_bytes(buf.getvalue())
            return path
    raise RuntimeError(f"{path_stem.name}: does not fit {max_bytes // 1024} KB even as JPEG quality 70; "
                       "use calmer backgrounds or fewer noisy shots")


def _slot_frames(s) -> list[int]:
    """Series frame index for each slot (a 2-wide cover fills two slots)."""
    out = []
    for i, f in enumerate(s.frames):
        out += [i] * f.span
    return out


def _alt_lines(s, locale: str) -> list[str]:
    lines = []
    for slot, i in enumerate(_slot_frames(s), start=1):
        f = s.frames[i]
        text = f.alt.get(locale) or " — ".join(t for t in (f.caption.get(locale), f.subtitle.get(locale)) if t)
        lines.append(f"{slot:02d}: {text[:ALT_MAX]}")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("series")
    ap.add_argument("--validate", action="store_true", help="check the series and stop")
    ap.add_argument("--targets")
    ap.add_argument("--locales")
    ap.add_argument("--style", help="render with another style (previews)")
    args = ap.parse_args(argv)
    _need_deps()

    import compose
    import series as series_mod
    from PIL import Image
    from playwright.sync_api import sync_playwright
    from targets import TARGETS

    path = Path(args.series).resolve()
    try:
        s = series_mod.load(path)
    except series_mod.SeriesError as e:
        print(f"FAIL {e}", file=sys.stderr)
        return 1
    if args.style:
        s.style.name = args.style
    issues = series_mod.validate(s, path.parent)
    for issue in issues:
        print(issue)
    if any(i.level == "FAIL" for i in issues):
        print(f"{sum(i.level == 'FAIL' for i in issues)} FAIL: fix series.json before rendering")
        return 1
    if args.validate:
        print("series OK")
        return 0

    targets = args.targets.split(",") if args.targets else s.targets
    locales = args.locales.split(",") if args.locales else s.locales
    workdir, _root = series_mod.output_dirs(s, path)
    out = workdir / "out"
    cache = out / ".html"
    cache.mkdir(parents=True, exist_ok=True)
    slots = _slot_frames(s)
    report = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "series": str(path),
              "style": s.style.name, "frames": []}
    contact_src: dict[str, tuple[str, list]] = {}

    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(device_scale_factor=1)
        for target in targets:
            t = TARGETS[target]
            for size in t.sizes:
                for locale in locales:
                    try:
                        c = compose.build_canvas(s, target, size, locale, SKILL_DIR, path.parent)
                    except ValueError as e:
                        print(f"FAIL {target}: {e}", file=sys.stderr)
                        return 1
                    html_path = cache / f"{target}-{size[0]}x{size[1]}-{locale}.html"
                    html_path.write_text(c.html, encoding="utf-8")
                    canvas, geo = _capture(page, html_path, c.width, c.height)
                    d = out / target / f"{size[0]}x{size[1]}" / locale
                    d.mkdir(parents=True, exist_ok=True)
                    for old in d.glob("[0-9][0-9].*"):
                        old.unlink()
                    canvas.save(d / "canvas.png")
                    fw = c.frame_width
                    files = []
                    for slot in range(c.frames):
                        left = slot * fw
                        img = canvas.crop((left, 0, left + fw, c.height))
                        f = _save(img, d / f"{slot + 1:02d}", t.max_bytes)
                        files.append(f)
                        frame_index = 0 if target == "feature-graphic" else slots[slot]
                        caps = [
                            {"text": cap["text"], "color": _rgb_hex(cap["color"]), "line_height": cap["line_height"],
                             "overflow": cap["overflow"], "broken_word": cap["broken_word"],
                             "max_bottom": cap["max_bottom"],
                             "box": [cap["box"][0] - left, cap["box"][1], cap["box"][2], cap["box"][3]]}
                            for cap in geo["captions"]
                            if cap["frame"] == frame_index and left <= cap["box"][0] < left + fw
                        ]
                        shots = [
                            {"path": str(Path(sh["src"].replace("file://", "")).relative_to(path.parent))
                             if sh["src"].startswith("file://" + str(path.parent)) else sh["src"],
                             "platform": sh["platform"], "scale": sh["scale"],
                             "screen": [sh["screen"][0] - left, sh["screen"][1], sh["screen"][2], sh["screen"][3]]}
                            for sh in geo["shots"]
                            if sh["box"][0] < left + fw and sh["box"][0] + sh["box"][2] > left
                        ]
                        report["frames"].append({
                            "target": target, "size": list(size), "locale": locale, "index": slot,
                            "frame": frame_index, "file": str(f.relative_to(out)), "bytes": f.stat().st_size,
                            "captions": caps, "shots": shots,
                        })
                    if target != "feature-graphic" and (locale not in contact_src or target == "android-phone"):
                        contact_src[locale] = (target, files)
        browser.close()

    for locale, (_target, files) in contact_src.items():
        imgs = [Image.open(f).convert("RGB") for f in files]
        scale = CONTACT_HEIGHT / imgs[0].height
        sheet = Image.new("RGB", (sum(round(i.width * scale) for i in imgs), CONTACT_HEIGHT), "white")
        x = 0
        for i in imgs:
            i = i.resize((round(i.width * scale), CONTACT_HEIGHT), Image.LANCZOS)
            sheet.paste(i, (x, 0))
            x += i.width
        sheet.save(out / f"contact-{locale}.png")
    for locale in locales:
        (out / f"alt-text.{locale}.txt").write_text("\n".join(_alt_lines(s, locale)) + "\n", encoding="utf-8")
    (out / "render-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"rendered {len(report['frames'])} images into {out}")
    for locale in contact_src:
        print(f"look at {out / f'contact-{locale}.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
