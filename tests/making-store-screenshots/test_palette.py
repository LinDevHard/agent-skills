import pytest
from PIL import Image

import palette


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))


def _distance(a: str, b: str) -> float:
    return sum((x - y) ** 2 for x, y in zip(_hex_to_rgb(a), _hex_to_rgb(b))) ** 0.5


def test_dominant_ignores_white_chrome(tmp_path):
    img = Image.new("RGB", (100, 100), "#ffffff")
    img.paste(Image.new("RGB", (100, 70), "#3355ff"), (0, 30))
    img.save(tmp_path / "a.png")
    assert _distance(palette.dominant(tmp_path / "a.png")[0], "#3355ff") < 20


def test_all_white_falls_back_to_white(tmp_path):
    Image.new("RGB", (50, 50), "#ffffff").save(tmp_path / "w.png")
    assert palette.dominant(tmp_path / "w.png")[0] == "#ffffff"


def test_contrast_black_white():
    assert palette.contrast("#000000", "#ffffff") == pytest.approx(21.0)


def test_contrast_grey():
    assert palette.contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)


def test_soft_gradient_is_lighter_than_source():
    top, bottom = palette.soft_gradient(["#3355ff"])
    for stop in (top, bottom):
        assert palette.luminance(stop) > palette.luminance("#3355ff")


def test_cli_prints_hex_colours(tmp_path):
    import subprocess
    import sys

    from conftest import SKILL_DIR

    Image.new("RGB", (40, 40), "#3355ff").save(tmp_path / "i.png")
    r = subprocess.run([sys.executable, str(SKILL_DIR / "scripts/palette.py"), str(tmp_path / "i.png"), "2"],
                       capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip().startswith("#")
