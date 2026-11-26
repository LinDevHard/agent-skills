import json
import subprocess
import sys

import pytest
from conftest import SKILL_DIR
from PIL import Image

import check

CHECK = SKILL_DIR / "scripts/check.py"


def _workdir(tmp_path, frames=6, target="android-phone", size=(1080, 1920), locale="en-US", caption="Pick a layout",
             caption_box=(80, 120, 900, 200), bg="#f4f5fb", text="#111111", mode="RGB", shots=None, alt=True):
    """A fake render: out/<target>/<WxH>/<locale>/NN.png + canvas.png + report."""
    out = tmp_path / "out"
    d = out / target / f"{size[0]}x{size[1]}" / locale
    d.mkdir(parents=True)
    canvas = Image.new(mode, (size[0] * frames, size[1]), bg)
    report = {"frames": []}
    for i in range(frames):
        img = Image.new(mode, size, bg)
        x, y, w, h = caption_box
        img.paste(Image.new(mode, (w // 3, h // 3), text), (x + 10, y + 10))  # some "text" pixels
        canvas.paste(img, (i * size[0], 0))
        f = d / f"{i + 1:02d}.png"
        img.save(f)
        report["frames"].append({
            "target": target, "size": list(size), "locale": locale, "index": i, "frame": i,
            "file": str(f.relative_to(out)), "bytes": f.stat().st_size,
            "captions": [{"text": caption, "box": list(caption_box), "color": text, "line_height": 60,
                          "overflow": False, "broken_word": False, "max_bottom": size[1]}],
            "shots": shots if shots is not None else [{"path": "s.png", "platform": "android", "scale": 1.0,
                                                       "screen": [100, 500, 800, 1400]}],
        })
    canvas.save(d / "canvas.png")
    (out / "render-report.json").write_text(json.dumps(report))
    if alt:
        (out / f"alt-text.{locale}.txt").write_text(
            "\n".join(f"{i + 1:02d}: Layout picker with three phones" for i in range(frames)) + "\n")
    return tmp_path


def _findings(workdir, **kw):
    return check.run(workdir, **kw)


def _has(findings, level, needle):
    return any(f.level == level and needle in f.message for f in findings)


def test_clean_render_passes(tmp_path):
    assert [f for f in _findings(_workdir(tmp_path)) if f.level == "FAIL"] == []


def test_wrong_size_fails(tmp_path):
    w = _workdir(tmp_path)
    p = w / "out/android-phone/1080x1920/en-US/03.png"
    Image.new("RGB", (1080, 1900), "#fff").save(p)
    assert _has(_findings(w), "FAIL", "1080x1900")


def test_alpha_fails(tmp_path):
    assert _has(_findings(_workdir(tmp_path, mode="RGBA")), "FAIL", "alpha")


def test_too_few_frames_for_rustore(tmp_path):
    assert _has(_findings(_workdir(tmp_path, frames=2)), "FAIL", "RuStore")


def test_file_over_appgallery_budget(tmp_path, monkeypatch):
    w = _workdir(tmp_path)
    monkeypatch.setattr(check, "file_size", lambda p: 2 * 1024 * 1024 + 1)
    assert _has(_findings(w), "FAIL", "2048 KB")


@pytest.mark.parametrize(
    "caption", ["The best photo editor", "#1 screenshot app", "Free forever", "New look", "50% off", "Download now",
                "Лучший редактор", "Скриншоты бесплатно", "Скидка на Pro", "Скачайте сейчас", "Всего 99 ₽"],
)
def test_banned_caption_fails(tmp_path, caption):
    assert _has(_findings(_workdir(tmp_path, caption=caption)), "FAIL", "caption")


@pytest.mark.parametrize("caption", ["Freedom to design", "Newsletter covers", "Лучи света", "Топливо для идей"])
def test_harmless_words_pass(tmp_path, caption):
    assert not _has(_findings(_workdir(tmp_path, caption=caption)), "FAIL", "caption")


def test_caption_area_over_20_percent(tmp_path):
    assert _has(_findings(_workdir(tmp_path, caption_box=(0, 100, 1080, 450))), "FAIL", "20 %")


def test_low_contrast_fails(tmp_path):
    assert _has(_findings(_workdir(tmp_path, bg="#bbbbbb", text="#999999")), "FAIL", "contrast")


def test_mid_contrast_warns(tmp_path):
    f = _findings(_workdir(tmp_path, bg="#ffffff", text="#808080"))  # 3.95:1
    assert _has(f, "warn", "contrast") and not _has(f, "FAIL", "contrast")


def test_caption_in_top_cutoff_warns(tmp_path):
    assert _has(_findings(_workdir(tmp_path, caption_box=(80, 20, 900, 150))), "warn", "top or bottom 5 %")


def test_upscaled_shot_warns(tmp_path):
    shots = [{"path": "s.png", "platform": "android", "scale": 1.8, "screen": [100, 500, 800, 1400]}]
    assert _has(_findings(_workdir(tmp_path, shots=shots)), "warn", "upscaled")


def test_android_shot_in_ios_fails(tmp_path):
    w = _workdir(tmp_path, target="ios-phone", size=(1206, 2622))
    assert _has(_findings(w), "FAIL", "2.3.10")


def test_slices_must_tile_canvas(tmp_path):
    w = _workdir(tmp_path)
    p = w / "out/android-phone/1080x1920/en-US/02.png"
    Image.new("RGB", (1080, 1920), "#ff0000").save(p)
    assert _has(_findings(w), "FAIL", "canvas")


def test_alt_text_prefix_and_length(tmp_path):
    w = _workdir(tmp_path, alt=False)
    (w / "out/alt-text.en-US.txt").write_text("01: Image of a phone\n02: " + "x" * 141 + "\n")
    f = _findings(w)
    assert _has(f, "FAIL", "image of") and _has(f, "FAIL", "140")


def test_missing_alt_text_warns(tmp_path):
    assert _has(_findings(_workdir(tmp_path, alt=False)), "warn", "alt text")


def test_other_locale_warns_about_word_list(tmp_path):
    assert _has(_findings(_workdir(tmp_path, locale="de-DE")), "warn", "by eye")


def test_overflow_fails_and_broken_word_warns(tmp_path):
    w = _workdir(tmp_path)
    rp = w / "out/render-report.json"
    r = json.loads(rp.read_text())
    r["frames"][0]["captions"][0]["overflow"] = True
    r["frames"][1]["captions"][0]["broken_word"] = True
    rp.write_text(json.dumps(r))
    f = _findings(w)
    assert _has(f, "FAIL", "does not fit") and _has(f, "warn", "broken")


def test_cli_exit_codes(tmp_path):
    ok = subprocess.run([sys.executable, str(CHECK), str(_workdir(tmp_path / "a"))], capture_output=True, text=True)
    assert ok.returncode == 0 and "0 FAIL" in ok.stdout
    bad = subprocess.run([sys.executable, str(CHECK), str(_workdir(tmp_path / "b", caption="Best app"))],
                         capture_output=True, text=True)
    assert bad.returncode == 1 and "FAIL" in bad.stdout


def test_cli_missing_report(tmp_path):
    r = subprocess.run([sys.executable, str(CHECK), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 2 and "render.py" in r.stderr
