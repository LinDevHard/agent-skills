import re

import pytest

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
    # The 2-wide cover's auto layout puts a device across x = 1080.
    spans = [(_left_px(c.html, f'data-shot="0.{j}"'), _width_px(c.html, f'data-shot="0.{j}"')) for j in (0, 1)]
    assert any(left < 1080 < left + w for left, w in spans)


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


def test_style_auto_decor_crosses_every_border(project):
    def mutate(d):
        d["style"]["name"] = "sketch"

    c = _canvas(project(mutate))
    lefts = [float(v) for v in re.findall(r'class="decor[^"]*" style="left:([\d.]+)px', c.html)]
    widths = [float(v) for v in re.findall(r'class="decor[^"]*" style="[^"]*?width:([\d.]+)px', c.html)]
    for border in range(1080, c.width, 1080):
        if border == 1080:
            continue  # inside the 2-wide cover, not a frame border
        assert any(left < border < left + w for left, w in zip(lefts, widths)), border


def test_explicit_decor_replaces_auto_decor(project):
    def mutate(d):
        d["style"]["name"] = "sketch"
        d["decor"] = [{"kind": "arrow", "x": 0.5, "y": 0.5}]

    c = _canvas(project(mutate))
    assert c.html.count('class="decor ') == 1


def test_decor_masks_are_inline(project):
    # Chrome refuses mask-image from file:// URLs (CORS), so masks must be data URIs.
    def mutate(d):
        d["style"]["name"] = "sketch"

    c = _canvas(project(mutate))
    styles = re.findall(r'class="decor [^"]*" style="([^"]*)"', c.html)
    assert styles and all("mask-image:url('data:image/svg+xml" in st for st in styles)


def test_two_wide_cover_auto_layout_crosses_border(project):
    def mutate(d):
        for shot in d["frames"][0]["shots"]:
            shot.pop("offset", None)

    c = _canvas(project(mutate))
    spans = [(_left_px(c.html, f'data-shot="0.{j}"'), _width_px(c.html, f'data-shot="0.{j}"')) for j in (0, 1)]
    assert any(left < 1080 < left + w for left, w in spans)
    assert all(w >= 0.6 * 1080 for _, w in spans)


def test_style_rotates_feature_phones(project):
    def mutate(d):
        d["style"]["name"] = "sketch"

    c = _canvas(project(mutate))
    angles = re.findall(r'data-shot="[1-4]\.0"[^>]*rotate\((-?[\d.]+)deg\)', c.html)
    assert len(angles) == 4 and any(float(a) != 0 for a in angles)


def test_poster_accent_is_the_brightest_brand_colour(project):
    def mutate(d):
        d["style"]["name"] = "poster"

    c = _canvas(project(mutate))
    assert "--accent:#FFC15E" in c.html and "--accent:#2A1BD6" not in c.html


def _tablet_project(project, target):
    def mutate(d):
        d["targets"] = [target]
        for f in d["frames"]:
            for s in f["shots"]:
                s["form"] = "tablet"

    return project(mutate, shot_size=(2560, 1600))


def _box(html: str, attr: str) -> tuple[float, float, float, float]:
    m = re.search(rf'{attr}[^>]*?style="left:([\d.-]+)px; top:([\d.-]+)px; width:([\d.]+)px; height:([\d.]+)px', html)
    assert m, attr
    return tuple(float(v) for v in m.groups())


def test_frame_class():
    assert compose.frame_class(1080, 1920) == "tall"
    assert compose.frame_class(1200, 1920) == "tall"
    assert compose.frame_class(2064, 2752) == "square"
    assert compose.frame_class(2160, 2160) == "square"
    assert compose.frame_class(2560, 1920) == "wide"
    assert compose.frame_class(2560, 1440) == "wide"


def test_wide_frame_caption_left_device_right(project):
    path = _tablet_project(project, "android-tablet-10-landscape")
    c = _canvas(path, "android-tablet-10-landscape", (2560, 1440))
    fw = 2560
    cap_left = _left_px(c.html, 'class="caption role-feature[^"]*" data-frame="1"') - 2 * fw
    cap_width = _width_px(c.html, 'class="caption role-feature[^"]*" data-frame="1"')
    assert cap_left < 0.1 * fw and cap_left + cap_width <= 0.45 * fw
    x, y, w, h = _box(c.html, 'data-shot="1.0"')
    assert x - 2 * fw >= 0.4 * fw and x - 2 * fw + w <= fw
    assert 'class="shot device-tablet"' in c.html


def test_square_frame_device_fits(project):
    def mutate(d):
        d["targets"] = ["android-foldable"]
        for f in d["frames"]:
            for s in f["shots"]:
                s["form"] = "foldable"

    c = _canvas(project(mutate, shot_size=(2208, 1840)), "android-foldable", (2160, 2160))
    x, y, w, h = _box(c.html, 'data-shot="1.0"')
    assert w <= 0.75 * 2160 and y >= 0.2 * 2160


def test_tall_caption_size_unchanged_for_iphone(project):
    def mutate(d):
        d["targets"] = ["ios-phone"]
        for f in d["frames"]:
            for s in f["shots"]:
                s["platform"] = "ios"

    c = _canvas(project(mutate), "ios-phone", (1320, 2868))
    m = re.search(r'data-frame="1"[^>]*font-size:([\d.]+)px', c.html)
    assert float(m.group(1)) == pytest.approx(0.082 * 1320, rel=0.01)


@pytest.mark.parametrize(
    ("target", "size"),
    [("android-tablet-10-landscape", (2560, 1440)), ("android-foldable", (2160, 2160))],
)
def test_caption_is_large_enough_on_wide_and_square_frames(project, target, size):
    def mutate(d):
        d["targets"] = [target]
        for f in d["frames"]:
            for s in f["shots"]:
                s["form"] = "foldable" if "foldable" in target else "tablet"

    c = _canvas(project(mutate, shot_size=(2560, 1600)), target, size)
    font = float(re.search(r'data-frame="1"[^>]*font-size:([\d.]+)px', c.html).group(1))
    assert font >= 0.07 * size[1]


@pytest.mark.parametrize(
    ("target", "size"),
    [("android-phone", (1080, 1920)), ("android-tablet-10-landscape", (2560, 1440)), ("android-foldable", (2160, 2160))],
)
def test_auto_decor_stays_off_captions(project, target, size):
    def mutate(d):
        d["style"]["name"] = "sketch"
        d["targets"] = [target]
        if target != "android-phone":
            for f in d["frames"]:
                for s in f["shots"]:
                    s["form"] = "foldable" if "foldable" in target else "tablet"

    c = _canvas(project(mutate, shot_size=(2560, 1600)), target, size)
    caps = []
    for i in range(1, 5):
        m = re.search(rf'class="caption role-feature[^"]*" data-frame="{i}" style="left:([\d.]+)px; top:([\d.]+)px; '
                      r'width:([\d.]+)px', c.html)
        caps.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), 0.0))
    decor = [tuple(float(v) for v in m) for m in re.findall(
        r'class="decor [^"]*" style="left:([\d.-]+)px; top:([\d.-]+)px; width:([\d.]+)px; height:([\d.]+)px', c.html)]
    assert decor
    for dx, dy, dw, dh in decor:
        for cx, cy, cw, ch in caps:
            ch = size[1] * 0.25  # the caption block's height is not in the HTML; 25 % of the frame covers 3 lines
            overlap = dx < cx + cw and cx < dx + dw and dy < cy + ch and cy < dy + dh
            assert not overlap, ((dx, dy, dw, dh), (cx, cy, cw))


def test_landscape_shot_fills_portrait_frame(project):
    def mutate(d):
        d["targets"] = ["android-tablet-10"]
        for f in d["frames"]:
            for s in f["shots"]:
                s["form"] = "tablet"

    c = _canvas(project(mutate, shot_size=(2560, 1600)), "android-tablet-10", (1440, 2560))
    x, y, w, h = _box(c.html, 'data-shot="1.0"')
    assert w >= 0.85 * 1440


def test_hyphenated_words_do_not_break(project):
    def mutate(d):
        d["frames"][1]["caption"]["en-US"] = "Turn and 3D-tilt now"

    c = _canvas(project(mutate))
    assert '<span class="nobr">3D-tilt</span>' in c.html


def test_minimal_background_keeps_dark_caption_readable(project):
    import palette

    c = _canvas(project())  # example uses minimal with a saturated brand
    stops = re.findall(r'class="frame role-feature" data-frame="1" style="[^"]*linear-gradient\([^,]+, (#[0-9a-f]{6}), (#[0-9a-f]{6})\)', c.html)
    assert stops, "minimal should draw a computed soft gradient"
    for stop in stops[0]:
        assert palette.contrast("#101014", stop) >= 4.5, stop
