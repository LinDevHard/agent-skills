"""Build the HTML of one canvas: every frame of a series for one target size and locale, side by side.

The canvas is drawn once and sliced at frame borders, so anything placed across a border (a shot,
decor) continues on the next frame when the store shows the frames in a row.
"""

from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

import palette
from series import Decor, Frame, Series, ShotRef
from targets import TARGETS

# Frame layouts by shape. Caption box: (left, top, width) as shares of the frame; shots: (x in frames,
# y offset in frame heights, max width share, max height share or None to let tall frames bleed off the bottom).
CAPTION_TOP = 0.06  # Below the top 5 % that store UI may cover.
LAYOUTS = {
    "tall": {  # phones, portrait tablets in 9:16
        "caption": (0.08, CAPTION_TOP, 0.84),
        "shots_top": 0.27,  # under a two-line caption with a subtitle
        "auto": {
            1: [(0.5, 0.0, 0.74, None)],
            2: [(0.33, 0.0, 0.52, None), (0.67, 0.07, 0.52, None)],
            3: [(0.22, 0.06, 0.38, None), (0.5, 0.0, 0.38, None), (0.78, 0.06, 0.38, None)],
        },
        # A 2-wide cover: large devices that overlap the border between its slots (Themify's cover).
        "cover2": {
            1: [(1.0, 0.0, 0.8, None)],
            2: [(0.78, 0.0, 0.68, None), (1.38, 0.07, 0.68, None)],
            3: [(0.45, 0.06, 0.56, None), (1.0, 0.0, 0.62, None), (1.55, 0.06, 0.56, None)],
        },
    },
    "square": {  # foldable inner screens, iPad portrait (3:4)
        "caption": (0.08, CAPTION_TOP, 0.84),
        "shots_top": 0.3,
        "auto": {
            1: [(0.5, 0.0, 0.62, None)],
            2: [(0.33, 0.0, 0.44, None), (0.67, 0.06, 0.44, None)],
            3: [(0.22, 0.05, 0.32, None), (0.5, 0.0, 0.32, None), (0.78, 0.05, 0.32, None)],
        },
        "cover2": {
            1: [(1.0, 0.0, 0.7, None)],
            2: [(0.75, 0.0, 0.6, None), (1.35, 0.06, 0.6, None)],
            3: [(0.45, 0.05, 0.5, None), (1.0, 0.0, 0.54, None), (1.55, 0.05, 0.5, None)],
        },
    },
    "wide": {  # landscape tablets, foldable inner 4:3, iPad landscape
        "caption": (0.05, 0.3, 0.32),  # left column
        "caption_max_h": 0.6,
        "shots_top": 0.14,
        "auto": {
            1: [(0.69, 0.0, 0.58, 0.86)],
            2: [(0.6, 0.0, 0.36, 0.8), (0.84, 0.06, 0.36, 0.8)],
            3: [(0.53, 0.06, 0.26, 0.7), (0.7, 0.0, 0.26, 0.74), (0.87, 0.06, 0.26, 0.7)],
        },
        "cover2": {
            1: [(1.1, 0.0, 0.7, 0.86)],
            2: [(0.8, 0.0, 0.5, 0.86), (1.32, 0.06, 0.5, 0.86)],
            3: [(0.62, 0.06, 0.4, 0.78), (1.0, 0.0, 0.42, 0.82), (1.38, 0.06, 0.4, 0.78)],
        },
    },
}
# Caption and doodle scale per frame shape: frame width on 9:16 and taller frames, less on wider ones.
UNIT = {
    "tall": lambda fw, fh: min(fw, fh * 9 / 16),
    "square": lambda fw, fh: min(fw, fh) * 0.9,
    "wide": lambda fw, fh: fh * 0.9,
}
# Doodle heights (share of frame height) per shape: clear of the caption band in every layout.
AUTO_DECOR_Y = {"tall": (0.33, 0.72), "square": (0.34, 0.76), "wide": (0.06, 0.8)}
TALL_MIN, WIDE_MAX = 1.4, 0.9  # h/w thresholds: 9:16 and 10:16 are tall, 3:4 and 1:1 square, 4:3 and 16:9 wide.


def frame_class(w: int, h: int) -> str:
    ratio = h / w
    return "tall" if ratio >= TALL_MIN else "square" if ratio >= WIDE_MAX else "wide"


BEZEL = {"phone": 0.035, "tablet": 0.028, "none": 0.0}  # Bezel thickness as a share of device width.


@dataclass
class CanvasHtml:
    html: str
    width: int
    height: int
    frame_width: int
    frames: int


def load_style(skill_dir: Path, name: str, overrides: dict) -> dict:
    path = skill_dir / "assets/styles" / name / "style.json"
    if not path.is_file():
        known = sorted(p.name for p in (skill_dir / "assets/styles").iterdir() if p.is_dir())
        raise ValueError(f"unknown style '{name}'; known: {', '.join(known)}")
    style = json.loads(path.read_text())
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(style.get(key), dict):
            style[key] = {**style[key], **value}
        else:
            style[key] = value
    return style


def _url(path: Path) -> str:
    return path.resolve().as_uri()


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _word(w: str) -> str:
    # A hyphen is a legal line break ("3D-/tilt"); keep hyphenated words whole.
    return f'<span class="nobr">{_esc(w)}</span>' if "-" in w.strip("-") else _esc(w)


def _caption_html(text: str) -> str:
    """Caption with its last word wrapped, so a style can put a marker behind it."""
    words = text.split()
    if len(words) < 2:
        return f'<span class="last">{" ".join(_word(w) for w in words)}</span>'
    return f'{" ".join(_word(w) for w in words[:-1])} <span class="last">{_word(words[-1])}</span>'


def _frame_background(style: dict, s: Series, frame: Frame, index: int, base_dir: Path, platform: str,
                      form: str = "phone") -> str:
    bg = style.get("background", {})
    colors = bg.get("colors") or s.app.brand or ["#f4f5fb", "#dfe3f5"]
    mode = bg.get("mode", "solid")
    if mode == "shot-tone" and frame.shots:
        path = next((p for p in (sh.path_for(platform, form) for sh in frame.shots) if p), None)
        if path:
            top, bottom = palette.soft_gradient(palette.dominant(base_dir / path))
            return f"linear-gradient(180deg, {top}, {bottom})"
    if mode == "soft-brand":  # the brand, lightened enough for dark caption text
        top, bottom = palette.soft_gradient([colors[index % len(colors)], colors[(index + 1) % len(colors)]])
        return f"linear-gradient(170deg, {top}, {bottom})"
    if mode == "gradient":
        return f"linear-gradient(160deg, {colors[0]}, {colors[-1]})"
    if mode == "cover-gradient":
        dark = bg.get("base", "#0c0c10")
        if frame.role == "cover":
            accent = (s.app.brand or colors)[0]
            return f"radial-gradient(120% 80% at 0% 0%, {accent} 0%, {dark} 70%)"
        return dark
    return colors[0]


def _accent(style: dict, s: Series, index: int) -> str:
    brand = s.app.brand or style.get("background", {}).get("colors") or ["#2a1bd6"]
    if style.get("accent") == "brightest":  # Dark styles need the accent that reads on black.
        return max(brand, key=palette.luminance)
    if style.get("frameColors") == "cycle-brand":
        return brand[index % len(brand)]
    return brand[0]


def _shot_html(shot: ShotRef, key: str, frame_left: float, fw: int, fh: int, auto, style: dict,
               base_dir: Path, platform: str, index: int = 0, form: str = "phone", shots_top: float = 0.27) -> str:
    rel = shot.path_for(platform, form)
    src = base_dir / rel
    with Image.open(src) as img:
        img_w, img_h = img.size
    crop_top = shot.crop.top if shot.crop else 0
    crop_bottom = shot.crop.bottom if shot.crop else 0
    visible_h = img_h - crop_top - crop_bottom

    if shot.layout == "none":
        kind = "none"
    elif form != "phone":
        kind = "tablet"  # tablets and foldables get the neutral tablet body
    else:
        kind = shot.layout if shot.layout in BEZEL else style.get("device", {}).get("kind", "phone")
    auto_x, auto_y, w_share, h_share = auto
    explicit = shot.offset != (0.5, 0.0)
    x_frames = shot.offset[0] if explicit else auto_x
    y_extra = shot.offset[1] if explicit else auto_y
    b = BEZEL[kind]
    if frame_class(fw, fh) == "tall" and img_w > visible_h:  # a landscape shot in a portrait frame: use the width
        w_share = min(0.92, w_share * 1.25)
    dev_w = w_share * fw * shot.scale
    if h_share:  # Fit by height too: a device dev_w wide is dev_w * ((1-2b) * vh/iw + 2b) tall.
        dev_w = min(dev_w, h_share * fh * shot.scale / ((1 - 2 * b) * visible_h / img_w + 2 * b))
    bezel = b * dev_w
    screen_w = dev_w - 2 * bezel
    k = screen_w / img_w  # Shot pixels -> canvas pixels; the shot keeps its aspect ratio.
    screen_h = visible_h * k
    dev_h = screen_h + 2 * bezel
    left = frame_left + x_frames * fw - dev_w / 2
    top = (shots_top + y_extra) * fh
    if h_share and dev_h < 0.8 * fh and not explicit:
        top = (fh - dev_h) / 2 + y_extra * fh  # a short (landscape) device sits in the middle of a wide frame
    rotate = shot.rotate
    turns = style.get("device", {}).get("rotate") or []
    if not rotate and turns:  # The style's own turn, alternating per frame, unless the shot sets one.
        rotate = turns[index % len(turns)]
    transform = f"rotate({rotate}deg)"
    if shot.tilt:
        transform = f"perspective({dev_w * 3:.0f}px) rotateY({-shot.tilt}deg) rotateX({shot.tilt / 3:.1f}deg) " + transform
    return (
        f'<div class="shot device-{kind}" data-shot="{key}" data-scale="{k:.4f}" '
        f'data-platform="{_esc(shot.platform or platform)}" '
        f'style="left:{left:.1f}px; top:{top:.1f}px; width:{dev_w:.1f}px; height:{dev_h:.1f}px; '
        f'--bezel:{bezel:.1f}px; transform:{transform}">'
        f'<div class="screen" style="width:{screen_w:.1f}px; height:{screen_h:.1f}px">'
        f'<img src="{_url(src)}" style="width:{screen_w:.1f}px; margin-top:{-crop_top * k:.1f}px"></div></div>'
    )


AUTO_DECOR_WIDTH = 0.24  # Share of the caption unit: reads as a doodle, still fits the gap between devices.


def _auto_decor(s: Series, style: dict, cls: str, fw: int, fh: int) -> list[Decor]:
    """One doodle across every frame border, so the series reads as one strip (sketch style)."""
    kinds = style.get("decor") or []
    if not kinds:
        return []
    w = AUTO_DECOR_WIDTH * UNIT[cls](fw, fh) / fw
    ys = AUTO_DECOR_Y[cls]
    out, border = [], 0
    for i, frame in enumerate(s.frames[:-1]):
        border += frame.span
        out.append(Decor(kind=kinds[i % len(kinds)], x=border - w / 2, y=ys[i % 2], w=w,
                         rotate=(-12, 9, -4)[i % 3]))
    return out


def _fonts_css(style: dict, skill_dir: Path) -> str:
    out = []
    for role, file in style.get("fonts", {}).items():
        out.append(
            f'@font-face {{ font-family: "{role}"; src: url("{_url(skill_dir / "assets/fonts" / file)}"); '
            "font-weight: 100 900; }"
        )
    return "\n".join(out)


# Shrinks each caption until its longest word fits on a line and the block fits its height
# (data-max-h). Run by render.py after fonts load; never breaks a word in the middle.
FIT_JS = """
window.fitCaptions = () => {
  for (const el of document.querySelectorAll('.caption')) {
    const h1 = el.querySelector('h1');
    const maxH = +el.dataset.maxH || Infinity;
    let size = parseFloat(getComputedStyle(el).fontSize);
    const floor = size * 0.4;  // below this the caption is unreadable anyway; check.py flags it
    for (let i = 0; i < 60 && size > floor; i++) {
      if (h1.scrollWidth <= el.clientWidth + 1 && el.scrollHeight <= maxH) break;
      size *= 0.96;
      el.style.fontSize = size + 'px';
    }
    if (h1.scrollWidth > el.clientWidth + 1) {  // last resort: a word longer than the column
      el.style.overflowWrap = 'anywhere';
      for (const span of el.querySelectorAll('span')) span.style.whiteSpace = 'normal';
      el.dataset.broken = '1';
    }
  }
};
"""


def _page(css: str, body: str, width: int, height: int, fw: int, fh: int) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{css}\n:root {{ --fw:{fw}px; --fh:{fh}px; }}"
        f"#canvas {{ width:{width}px; height:{height}px; }}</style><script>{FIT_JS}</script></head>"
        f"<body><div id='canvas'>{body}</div></body></html>"
    )


def build_canvas(s: Series, target: str, size: tuple[int, int], locale: str, skill_dir: Path,
                 base_dir: Path) -> CanvasHtml:
    """HTML for every frame of `s` at `size`, for one locale. Shot paths resolve against base_dir."""
    skill_dir = Path(skill_dir)
    style = load_style(skill_dir, s.style.name, s.style.overrides)
    css = "\n".join(
        [
            _fonts_css(style, skill_dir),
            (skill_dir / "assets/styles/base.css").read_text(),
            (skill_dir / "assets/styles" / s.style.name / "style.css").read_text(),
        ]
    )
    platform = TARGETS[target].platform
    form = TARGETS[target].form
    fw, fh = size
    cls = frame_class(fw, fh)
    layout_cfg = LAYOUTS[cls]
    unit = UNIT[cls](fw, fh)
    if target == "feature-graphic":
        return _feature_graphic(s, style, css, size, locale, base_dir, skill_dir)

    caption_cfg = style.get("caption", {})
    font_px = caption_cfg.get("size", 0.085) * unit
    cap_left, cap_top, cap_width = layout_cfg["caption"]
    # The caption block ends above the devices (tall, square) or within the column (wide).
    cap_max_h = layout_cfg.get("caption_max_h", layout_cfg["shots_top"] - cap_top - 0.015) * fh
    backgrounds, captions, shots = [], [], []
    x = 0.0
    for i, frame in enumerate(s.frames):
        width = frame.span * fw
        backgrounds.append(
            f'<section class="frame role-{frame.role}" data-frame="{i}" '
            f'style="left:{x:.0f}px; width:{width}px; background:{_frame_background(style, s, frame, i, base_dir, platform, form)}; '
            f'--accent:{_accent(style, s, i)}"></section>'
        )
        caption = frame.caption.get(locale, "")
        subtitle = frame.subtitle.get(locale, "")
        sub_html = f'<p class="subtitle">{_esc(subtitle)}</p>' if subtitle else ""
        captions.append(
            f'<div class="caption role-{frame.role} frame-{cls}" data-frame="{i}" '
            # The caption stays inside the frame's first slot: text cut by a border reads badly in search.
            f'style="left:{x + fw * cap_left:.0f}px; top:{cap_top * fh:.0f}px; width:{fw * cap_width:.0f}px; '
            f'font-size:{font_px:.1f}px; --accent:{_accent(style, s, i)}" data-max-h="{cap_max_h:.0f}">'
            f"<h1>{_caption_html(caption)}</h1>{sub_html}</div>"
        )
        usable = [sh for sh in frame.shots if sh.path_for(platform, form)]
        table = layout_cfg["cover2" if frame.span == 2 else "auto"]
        layout = table.get(len(usable), table[3])
        for j, shot in enumerate(usable):
            auto = layout[min(j, len(layout) - 1)]
            shots.append(_shot_html(shot, f"{i}.{j}", x, fw, fh, auto, style, base_dir, platform, i, form,
                                    layout_cfg["shots_top"]))
        x += width

    decor = []
    for d in s.decor or _auto_decor(s, style, cls, fw, fh):
        path = skill_dir / "assets/decor" / f"{d.kind}.svg"
        # Inline the SVG: Chrome refuses mask-image from file:// URLs.
        mask = "'data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode() + "'"
        color = d.color or "var(--decor, #1b1b1f)"
        decor.append(
            f'<div class="decor decor-{_esc(d.kind)}" style="left:{d.x * fw:.0f}px; top:{d.y * fh:.0f}px; '
            f'width:{d.w * fw:.0f}px; height:{d.w * fw:.0f}px; transform:rotate({d.rotate}deg); '
            f'background:{color}; -webkit-mask-image:url({mask}); mask-image:url({mask})"></div>'
        )

    total = int(x)
    body = (
        '<div class="frames">' + "".join(backgrounds) + "</div>"
        '<div class="layer shots">' + "".join(shots) + "</div>"
        '<div class="layer decor-layer">' + "".join(decor) + "</div>"
        '<div class="layer captions">' + "".join(captions) + "</div>"
    )
    return CanvasHtml(_page(css, body, total, fh, fw, fh), total, fh, fw, s.frame_count)


def _feature_graphic(s: Series, style: dict, css: str, size, locale: str, base_dir: Path,
                     skill_dir: Path) -> CanvasHtml:
    """1024x500: cover background, app icon, name and the cover caption; no device (Play advice)."""
    w, h = size
    cover = s.frames[0]
    bg = _frame_background(style, s, cover, 0, base_dir, "android")
    icon = ""
    if s.app.icon and (base_dir / s.app.icon).is_file():
        icon = f'<img class="fg-icon" src="{_url(base_dir / s.app.icon)}">'
    body = (
        f'<section class="frame feature-graphic role-cover" data-frame="0" '
        f'style="left:0; width:{w}px; background:{bg}; --accent:{_accent(style, s, 0)}">'
        f'<div class="fg-content">{icon}<div class="fg-text"><div class="fg-name">{_esc(s.app.name)}</div>'
        f'<div class="caption" data-frame="0"><h1>{_caption_html(cover.caption.get(locale, ""))}</h1></div>'
        "</div></div></section>"
    )
    return CanvasHtml(_page(css, body, w, h, w, h), w, h, w, 1)
