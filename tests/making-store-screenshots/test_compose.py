import re

from conftest import SKILL_DIR

import compose
import series


def _canvas(path, target="android-phone", size=(1080, 1920), locale="en-US"):
    s = series.load(path)
    return compose.build_canvas(s, target, size, locale, SKILL_DIR, path.parent)


def _left_px(html: str, attr: str) -> float:
    m = re.search(rf'{attr}[^>]*?style="[^"]*?left:\s*([\d.]+)px', html)
    assert m, attr
    return float(m.group(1))


def _width_px(html: str, attr: str) -> float:
    m = re.search(rf'{attr}[^>]*?style="[^"]*?width:\s*([\d.]+)px', html)
    assert m, attr
    return float(m.group(1))


def test_canvas_width_is_frames_times_width(project):
    def mutate(d):
        d["frames"].append(dict(d["frames"][1]))  # 2-wide cover + 5 features = 7 frames

    c = _canvas(project(mutate))
    assert (c.width, c.height, c.frames, c.frame_width) == (7 * 1080, 1920, 7, 1080)


def test_spanning_shot_crosses_border(project):
    c = _canvas(project())
    # The cover's second shot sits at offset 1.25 frames, its box must straddle x = 1080.
    left = _left_px(c.html, 'data-shot="0.1"')
    width = _width_px(c.html, 'data-shot="0.1"')
    assert left < 1080 < left + width


def test_caption_text_is_escaped(project):
    def mutate(d):
        d["frames"][1]["caption"]["en-US"] = "<b>&"

    c = _canvas(project(mutate))
    assert "&lt;b&gt;&amp;" in c.html
    assert "<b>&" not in c.html


def test_uses_platform_specific_shot(project):
    def mutate(d):
        d["targets"] = ["ios-phone"]
        d["frames"][1]["shots"] = [{"path": {"ios": "shots/a-ios.png", "android": "shots/a-and.png"}}]

    c = _canvas(project(mutate), "ios-phone", (1320, 2868))
    assert "a-ios.png" in c.html
    assert "a-and.png" not in c.html


def test_every_caption_tagged_with_its_frame(project):
    c = _canvas(project())
    frames = re.findall(r'class="caption[^"]*" data-frame="(\d+)"', c.html)
    assert frames == ["0", "1", "2", "3", "4"]


def test_feature_graphic_has_no_device(project):
    c = _canvas(project(), "feature-graphic", (1024, 500))
    assert (c.width, c.height, c.frames) == (1024, 500, 1)
    assert "data-shot=" not in c.html
