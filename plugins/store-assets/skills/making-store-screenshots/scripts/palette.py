#!/usr/bin/env python3
"""Colours from shots: dominant colours, soft background gradients, WCAG contrast.

    palette.py <image> [n]    prints the n (default 3) dominant colours, e.g. for app.brand from the icon
"""

from __future__ import annotations

import colorsys
from pathlib import Path

from PIL import Image

SAMPLE_SIDE = 128  # Downscale before quantizing: colour share does not need full resolution.
QUANT_COLORS = 12  # Enough buckets to separate UI chrome from content colours.
CHROME_LIGHTNESS = (0.06, 0.94)  # HLS lightness outside this range counts as white/black UI chrome.


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def dominant(path: Path, n: int = 3) -> list[str]:
    """Most frequent colours of an image, most frequent first, skipping near-white/near-black chrome
    unless the image is nothing but chrome."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((SAMPLE_SIDE, SAMPLE_SIDE))
    q = img.quantize(colors=QUANT_COLORS, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    colors = [tuple(pal[i * 3 : i * 3 + 3]) for _, i in counts]

    def is_chrome(c):
        _, light, _ = colorsys.rgb_to_hls(*(v / 255 for v in c))
        return not CHROME_LIGHTNESS[0] < light < CHROME_LIGHTNESS[1]

    content = [c for c in colors if not is_chrome(c)]
    return [_hex(c) for c in (content or colors)[:n]]


def soft_gradient(colors: list[str]) -> tuple[str, str]:
    """Two lightened, slightly desaturated stops for a background in the tone of the shot."""
    base = colors[0]
    second = colors[1] if len(colors) > 1 else base

    def soften(h: str, lightness: float) -> str:
        hue, _, sat = colorsys.rgb_to_hls(*(v / 255 for v in _rgb(h)))
        r, g, b = colorsys.hls_to_rgb(hue, lightness, sat * 0.7)
        return _hex((round(r * 255), round(g * 255), round(b * 255)))

    # 0.86 / 0.78: light enough for dark caption text, still clearly tinted.
    return soften(base, 0.86), soften(second, 0.78)


def luminance(h: str) -> float:
    """WCAG relative luminance."""

    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


if __name__ == "__main__":
    import sys

    if len(sys.argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    print(" ".join(dominant(Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) == 3 else 3)))
