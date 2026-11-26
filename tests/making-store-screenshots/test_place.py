import subprocess
import sys

from conftest import SKILL_DIR
from PIL import Image

PLACE = SKILL_DIR / "scripts/place.py"


def _out(root, target="android-phone", size="1080x1920", locale="en-US", n=6, ext="png"):
    d = root / "store/screenshots/out" / target / size / locale
    d.mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        Image.new("RGB", (8, 8), "#123").save(d / f"{i:02d}.{ext}")
    Image.new("RGB", (8, 8), "#123").save(d / "canvas.png")
    return root


def _place(root, *args):
    return subprocess.run([sys.executable, str(PLACE), str(root / "store/screenshots"), "--project-root", str(root),
                           *args], capture_output=True, text=True)


def test_fastlane_layout_paths(tmp_path):
    _out(tmp_path)
    _out(tmp_path, "android-tablet-10-landscape", "2560x1440", n=4)
    _out(tmp_path, "feature-graphic", "1024x500", n=1)
    _out(tmp_path, "ios-phone", "1320x2868", n=3)
    r = _place(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    base = tmp_path / "fastlane/metadata/android/en-US/images"
    assert sorted(p.name for p in (base / "phoneScreenshots").iterdir()) == [f"{i}.png" for i in range(1, 7)]
    assert sorted(p.name for p in (base / "tenInchScreenshots").iterdir()) == [f"{i}.png" for i in range(1, 5)]
    assert (base / "featureGraphic.png").is_file()
    assert (tmp_path / "fastlane/screenshots/en-US/01_1320x2868.png").is_file()
    assert "canvas" not in r.stdout


def test_triple_t_detected(tmp_path):
    (tmp_path / "app/src/main/play/listings/en-US").mkdir(parents=True)
    _out(tmp_path)
    _out(tmp_path, "feature-graphic", "1024x500", n=1)
    r = _place(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    g = tmp_path / "app/src/main/play/listings/en-US/graphics"
    assert (g / "phone-screenshots/1.png").is_file() and (g / "feature-graphic/1.png").is_file()
    assert not (tmp_path / "fastlane").exists()


def test_place_refuses_to_overwrite(tmp_path):
    _out(tmp_path)
    dest = tmp_path / "fastlane/metadata/android/en-US/images/phoneScreenshots"
    dest.mkdir(parents=True)
    (dest / "1.jpg").write_bytes(b"old")
    r = _place(tmp_path)
    assert r.returncode == 1
    assert "1.jpg" in r.stdout and "--force" in r.stdout
    assert (dest / "1.jpg").read_bytes() == b"old"
    assert sorted(p.name for p in dest.iterdir()) == ["1.jpg"]  # nothing else copied


def test_force_overwrites_only_own_slots(tmp_path):
    _out(tmp_path)
    dest = tmp_path / "fastlane/metadata/android/en-US/images/phoneScreenshots"
    dest.mkdir(parents=True)
    (dest / "1.jpg").write_bytes(b"old")
    (dest / "9.png").write_bytes(b"other")
    r = _place(tmp_path, "--force")
    assert r.returncode == 0, r.stdout + r.stderr
    names = sorted(p.name for p in dest.iterdir())
    assert "1.jpg" not in names and "1.png" in names and "9.png" in names
    assert (dest / "9.png").read_bytes() == b"other"
    assert "9.png" in r.stdout and "will upload too" in r.stdout


def test_dry_run_copies_nothing(tmp_path):
    _out(tmp_path)
    r = _place(tmp_path, "--dry-run")
    assert r.returncode == 0 and "would copy" in r.stdout
    assert not (tmp_path / "fastlane").exists()


def test_foldables_are_left_for_manual_upload(tmp_path):
    _out(tmp_path)
    _out(tmp_path, "android-foldable", "2160x2160", n=3)
    r = _place(tmp_path)
    assert r.returncode == 0
    assert "android-foldable" in r.stdout and "Play Console" in r.stdout


def test_both_tablet_orientations_conflict(tmp_path):
    _out(tmp_path, "android-tablet-10", "1440x2560", n=4)
    _out(tmp_path, "android-tablet-10-landscape", "2560x1440", n=4)
    r = _place(tmp_path)
    assert r.returncode == 1 and "one orientation" in r.stdout


def test_missing_out_dir(tmp_path):
    r = _place(tmp_path)
    assert r.returncode == 2 and "render.py" in r.stderr
