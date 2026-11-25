"""Build the HTML of one canvas: every frame of a series for one target size and locale, side by side.

The canvas is drawn once and sliced at frame borders, so anything placed across a border (a shot,
decor) continues on the next frame when the store shows the frames in a row.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

import palette
from series import Frame, Series, ShotRef
from targets import TARGETS

# Layout of a portrait frame, as fractions of frame height or width.
CAPTION_TOP = 0.06  # Below the top 5 % that store UI may cover.
SHOTS_TOP = 0.27  # Where devices start: under a two-line caption with a subtitle.
DEVICE_WIDTH = 0.74  # One device per frame, as a share of frame width.
# Auto placement for 2 and 3 shots: (x offset in frames, y offset in frame heights, width share).
AUTO_LAYOUT = {
    1: [(0.5, 0.0, DEVICE_WIDTH)],
    2: [(0.33, 0.0, 0.52), (0.67, 0.07, 0.52)],
    3: [(0.22, 0.06, 0.38), (0.5, 0.0, 0.38), (0.78, 0.06, 0.38)],
}
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


def _caption_html(text: str) -> str:
    """Caption with its last word wrapped, so a style can put a marker behind it."""
    words = text.split()
    if len(words) < 2:
        return f'<span class="last">{_esc(text)}</span>'
    return f'{_esc(" ".join(words[:-1]))} <span class="last">{_esc(words[-1])}</span>'


def _frame_background(style: dict, s: Series, frame: Frame, index: int, base_dir: Path, platform: str) -> str:
    bg = style.get("background", {})
    colors = bg.get("colors") or s.app.brand or ["#f4f5fb", "#dfe3f5"]
    mode = bg.get("mode", "solid")
    if mode == "shot-tone" and frame.shots:
        path = frame.shots[0].path_for(platform)
        if path:
            top, bottom = palette.soft_gradient(palette.dominant(base_dir / path))
            return f"linear-gradient(180deg, {top}, {bottom})"
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
    if style.get("frameColors") == "cycle-brand":
        return brand[index % len(brand)]
    return brand[0]


def _shot_html(shot: ShotRef, key: str, frame_left: float, fw: int, fh: int, auto, style: dict,
               base_dir: Path, platform: str) -> str:
    rel = shot.path_for(platform)
    src = base_dir / rel
    with Image.open(src) as img:
        img_w, img_h = img.size
    crop_top = shot.crop.top if shot.crop else 0
    crop_bottom = shot.crop.bottom if shot.crop else 0
    visible_h = img_h - crop_top - crop_bottom

    kind = shot.layout if shot.layout in BEZEL else style.get("device", {}).get("kind", "phone")
    auto_x, auto_y, auto_w = auto
    explicit = shot.offset != (0.5, 0.0)
    x_frames = shot.offset[0] if explicit else auto_x
    y_extra = shot.offset[1] if explicit else auto_y
    dev_w = auto_w * fw * shot.scale
    bezel = BEZEL[kind] * dev_w
    screen_w = dev_w - 2 * bezel
    k = screen_w / img_w  # Shot pixels -> canvas pixels; the shot keeps its aspect ratio.
    screen_h = visible_h * k
    dev_h = screen_h + 2 * bezel
    left = frame_left + x_frames * fw - dev_w / 2
    top = (SHOTS_TOP + y_extra) * fh
    transform = f"rotate({shot.rotate}deg)"
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


def _fonts_css(style: dict, skill_dir: Path) -> str:
    out = []
    for role, file in style.get("fonts", {}).items():
        out.append(
            f'@font-face {{ font-family: "{role}"; src: url("{_url(skill_dir / "assets/fonts" / file)}"); '
            "font-weight: 100 900; }"
        )
    return "\n".join(out)


def _page(css: str, body: str, width: int, height: int, fw: int, fh: int) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{css}\n:root {{ --fw:{fw}px; --fh:{fh}px; }}"
        f"#canvas {{ width:{width}px; height:{height}px; }}</style></head>"
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
    fw, fh = size
    if target == "feature-graphic":
        return _feature_graphic(s, style, css, size, locale, base_dir, skill_dir)

    caption_cfg = style.get("caption", {})
    font_px = caption_cfg.get("size", 0.085) * fw
    backgrounds, captions, shots = [], [], []
    x = 0.0
    for i, frame in enumerate(s.frames):
        width = frame.span * fw
        backgrounds.append(
            f'<section class="frame role-{frame.role}" data-frame="{i}" '
            f'style="left:{x:.0f}px; width:{width}px; background:{_frame_background(style, s, frame, i, base_dir, platform)}; '
            f'--accent:{_accent(style, s, i)}"></section>'
        )
        caption = frame.caption.get(locale, "")
        subtitle = frame.subtitle.get(locale, "")
        sub_html = f'<p class="subtitle">{_esc(subtitle)}</p>' if subtitle else ""
        captions.append(
            f'<div class="caption role-{frame.role}" data-frame="{i}" '
            # The caption stays inside the frame's first slot: text cut by a border reads badly in search.
            f'style="left:{x + fw * 0.08:.0f}px; top:{CAPTION_TOP * fh:.0f}px; width:{fw * 0.84:.0f}px; '
            f'font-size:{font_px:.1f}px; --accent:{_accent(style, s, i)}">'
            f"<h1>{_caption_html(caption)}</h1>{sub_html}</div>"
        )
        usable = [sh for sh in frame.shots if sh.path_for(platform)]
        layout = AUTO_LAYOUT.get(len(usable), AUTO_LAYOUT[3])
        for j, shot in enumerate(usable):
            auto = layout[min(j, len(layout) - 1)]
            if frame.span == 2:
                auto = (auto[0] * 2, auto[1], auto[2])
            shots.append(_shot_html(shot, f"{i}.{j}", x, fw, fh, auto, style, base_dir, platform))
        x += width

    decor = []
    for d in s.decor:
        path = skill_dir / "assets/decor" / f"{d.kind}.svg"
        color = d.color or "var(--decor, #1b1b1f)"
        decor.append(
            f'<div class="decor decor-{_esc(d.kind)}" style="left:{d.x * fw:.0f}px; top:{d.y * fh:.0f}px; '
            f'width:{d.w * fw:.0f}px; height:{d.w * fw:.0f}px; transform:rotate({d.rotate}deg); '
            f'background:{color}; -webkit-mask-image:url({_url(path)}); mask-image:url({_url(path)})"></div>'
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
