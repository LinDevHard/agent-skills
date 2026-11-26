import json
import subprocess
import sys

import pytest
from conftest import SKILL_DIR
from PIL import Image

RENDER = SKILL_DIR / "scripts/render.py"
INSTALL_LINE = (
    "python3 -m venv .venv && .venv/bin/pip install playwright pillow && .venv/bin/playwright install chromium"
)

try:
    import playwright  # noqa: F401

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

browser = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright is not installed")


def _render(series_path, *args):
    return subprocess.run(
        [sys.executable, str(RENDER), str(series_path), *args], capture_output=True, text=True, timeout=300
    )


def _out(series_path):
    return series_path.parent / "out"  # output.workdir defaults to the series file's folder


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    from conftest import write_project

    tmp = tmp_path_factory.mktemp("render")
    path = write_project(tmp)
    r = _render(path, "--locales", "en-US")
    assert r.returncode == 0, r.stdout + r.stderr
    return path


@browser
def test_frames_have_exact_size_and_no_alpha(rendered):
    files = sorted((_out(rendered) / "android-phone/1080x1920/en-US").glob("[0-9][0-9].*"))
    assert len(files) == 6
    for f in files:
        with Image.open(f) as img:
            assert img.size == (1080, 1920)
            assert img.mode == "RGB"


@browser
def test_slices_tile_the_canvas(rendered):
    d = _out(rendered) / "android-phone/1080x1920/en-US"
    canvas = Image.open(d / "canvas.png").convert("RGB")
    files = sorted(d.glob("[0-9][0-9].png"))
    joined = Image.new("RGB", canvas.size)
    for i, f in enumerate(files):
        joined.paste(Image.open(f).convert("RGB"), (i * 1080, 0))
    assert joined.tobytes() == canvas.tobytes()


@browser
def test_report_has_caption_boxes(rendered):
    report = json.loads((_out(rendered) / "render-report.json").read_text())
    frames = [f for f in report["frames"] if f["target"] == "android-phone"]
    # Six slots; the 2-wide cover keeps its caption on its first slot only.
    assert [bool(f["captions"]) for f in frames] == [True, False, True, True, True, True]
    for f in frames:
        for c in f["captions"]:
            x, y, w, h = c["box"]
            assert 0 <= x and x + w <= 1080 and 0 <= y and y + h <= 1920, c


@browser
def test_contact_sheet_and_alt_text(rendered):
    out = _out(rendered)
    assert (out / "contact-android-phone-1080x1920-en-US.png").is_file()
    assert (out / "contact-feature-graphic-1024x500-en-US.png").exists() is False  # one image, no sheet
    assert (out / "alt-text.en-US.txt").read_text().strip()


@browser
def test_ios_phone_emits_both_sizes(project):
    def mutate(d):
        d["targets"] = ["ios-phone"]
        for f in d["frames"]:
            for s in f["shots"]:
                s["platform"] = "ios"

    path = project(mutate)
    r = _render(path, "--locales", "en-US")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (_out(path) / "ios-phone/1320x2868/en-US/01.png").is_file()
    assert (_out(path) / "ios-phone/1206x2622/en-US/01.png").is_file()


@browser
def test_oversized_png_becomes_jpeg_under_budget(project, tmp_path):
    import random

    def mutate(d):
        d["targets"] = ["android-phone"]

    path = project(mutate)
    rnd = random.Random(1)
    noise = Image.frombytes("RGB", (1080, 2400), bytes(rnd.getrandbits(8) for _ in range(1080 * 2400 * 3)))
    for p in (tmp_path / "shots").glob("*.png"):
        noise.save(p)
    r = _render(path, "--locales", "en-US")
    assert r.returncode == 0, r.stdout + r.stderr
    files = sorted((_out(path) / "android-phone/1080x1920/en-US").glob("[0-9][0-9].*"))
    assert files and all(f.stat().st_size <= 2 * 1024 * 1024 for f in files)
    assert any(f.suffix == ".jpg" for f in files)  # frames that fit as PNG stay PNG


@browser
def test_mixed_aspect_shots_are_fitted_not_stretched(project, tmp_path):
    def mutate(d):
        d["targets"] = ["android-phone"]
        d["frames"][1]["shots"] = [{"path": "shots/narrow.png", "platform": "android"}]
        d["frames"][2]["shots"] = [{"path": "shots/wide.png", "platform": "android"}]

    (tmp_path / "shots").mkdir(exist_ok=True)
    Image.new("RGB", (720, 1561), "#336").save(tmp_path / "shots/narrow.png")
    Image.new("RGB", (1920, 1080), "#633").save(tmp_path / "shots/wide.png")
    path = project(mutate)
    r = _render(path, "--locales", "en-US")
    assert r.returncode == 0, r.stdout + r.stderr
    report = json.loads((_out(path) / "render-report.json").read_text())
    boxes = {s["path"]: s for f in report["frames"] for s in f["shots"]}
    for name, aspect in (("shots/narrow.png", 720 / 1561), ("shots/wide.png", 1920 / 1080)):
        w, h = boxes[name]["screen"][2:]
        assert w / h == pytest.approx(aspect, rel=0.01)


@browser
def test_long_caption_wraps_within_frame(project):
    def mutate(d):
        d["targets"] = ["android-phone"]
        d["frames"][1]["caption"]["en-US"] = "Bildschirmfotos verwandeln sich mühelos in wunderschöne Geschäftsauftritte heute"

    path = project(mutate)
    r = _render(path, "--locales", "en-US")
    assert r.returncode == 0, r.stdout + r.stderr
    report = json.loads((_out(path) / "render-report.json").read_text())
    frame = next(f for f in report["frames"] if f["index"] == 2)  # frame 1 starts at slot 2 after the 2-wide cover
    x, y, w, h = frame["captions"][0]["box"]
    assert x >= 0 and x + w <= 1080
    assert h > frame["captions"][0]["line_height"] * 1.5


def test_missing_playwright_prints_install_line(project, tmp_path):
    path = project()
    blocker = tmp_path / "block"
    blocker.mkdir()
    (blocker / "playwright").mkdir()
    (blocker / "playwright/__init__.py").write_text("raise ImportError('blocked for test')\n")
    r = subprocess.run(
        [sys.executable, str(RENDER), str(path)],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(blocker), "PATH": "/usr/bin:/bin"},
        timeout=60,
    )
    assert r.returncode == 2
    assert INSTALL_LINE in r.stderr
    assert "Traceback" not in r.stderr


@browser
def test_tablet_landscape_renders_exact_size(project):
    def mutate(d):
        d["targets"] = ["android-tablet-10-landscape"]
        for f in d["frames"]:
            for s in f["shots"]:
                s["form"] = "tablet"

    path = project(mutate, shot_size=(2560, 1600))
    r = _render(path, "--locales", "en-US")
    assert r.returncode == 0, r.stdout + r.stderr
    files = sorted((_out(path) / "android-tablet-10-landscape/2560x1440/en-US").glob("[0-9][0-9].*"))
    assert len(files) == 6
    for f in files:
        with Image.open(f) as img:
            assert img.size == (2560, 1440) and img.mode == "RGB"
            assert f.stat().st_size <= 5 * 1024 * 1024


def _foldable_caption_report(project, caption):
    def mutate(d):
        d["targets"] = ["android-foldable"]
        d["frames"][1]["caption"]["en-US"] = caption
        for f in d["frames"]:
            for s in f["shots"]:
                s["form"] = "foldable"

    path = project(mutate, shot_size=(2208, 1840))
    r = _render(path, "--locales", "en-US", "--style", "sketch")
    assert r.returncode == 0, r.stdout + r.stderr
    report = json.loads((_out(path) / "render-report.json").read_text())
    return [c for f in report["frames"] for c in f["captions"]]


@browser
def test_caption_shrinks_instead_of_breaking_a_word(project):
    caps = _foldable_caption_report(project, "Bildschirmfotos verschönern")
    assert caps and not any(c["overflow"] or c["broken_word"] for c in caps)
    for c in caps:
        assert c["box"][1] + c["box"][3] <= c["max_bottom"] + 1, c


@browser
def test_impossible_word_breaks_and_is_reported(project):
    caps = _foldable_caption_report(project, "Bildschirmfotoverschönerungsprogrammversion")
    long = [c for c in caps if c["text"].startswith("BILDSCHIRM")]
    assert long and all(c["broken_word"] and not c["overflow"] for c in long)
