import json
from pathlib import Path

import pytest
from conftest import write_project

import series

def _project(tmp_path, mutate=None):
    return write_project(tmp_path, mutate)


def _issues(path: Path):
    return series.validate(series.load(path), path.parent)


def _fails(issues):
    return [i for i in issues if i.level == "FAIL"]


def test_example_is_valid(tmp_path):
    assert _fails(_issues(_project(tmp_path))) == []


def test_unknown_target_lists_known(tmp_path):
    path = _project(tmp_path, lambda d: d.update(targets=["ios-watch"]))
    fails = _fails(_issues(path))
    assert any("android-phone" in f.message for f in fails)


def test_missing_shot_file_names_frame(tmp_path):
    path = _project(tmp_path)
    data = json.loads(path.read_text())
    data["frames"][2]["shots"][0]["path"] = "shots/missing.png"
    path.write_text(json.dumps(data))
    fails = _fails(_issues(path))
    assert any(f.where == "frames[2].shots[0]" for f in fails)


def test_cover_two_wide_needs_a_shot(tmp_path):
    def mutate(d):
        d["frames"][0].update(span=2, shots=[])

    fails = _fails(_issues(_project(tmp_path, mutate)))
    assert any(f.where == "frames[0]" for f in fails)


def test_more_than_three_shots_fails(tmp_path):
    def mutate(d):
        shot = d["frames"][1]["shots"][0]
        d["frames"][1]["shots"] = [shot] * 4

    fails = _fails(_issues(_project(tmp_path, mutate)))
    assert any(f.where == "frames[1]" for f in fails)


def test_caption_missing_for_locale_warns(tmp_path):
    def mutate(d):
        d["locales"] = ["en-US", "de-DE"]

    issues = _issues(_project(tmp_path, mutate))
    assert any(i.level == "warn" and "de-DE" in i.message for i in issues)


def test_android_shot_in_ios_target_fails(tmp_path):
    def mutate(d):
        d["targets"] = ["ios-phone"]
        d["frames"][1]["shots"] = [{"path": "shots/a.png", "platform": "android"}]

    fails = _fails(_issues(_project(tmp_path, mutate)))
    assert any("2.3.10" in f.message and f.where.startswith("frames[1]") for f in fails)


@pytest.mark.parametrize(
    ("count", "needle"),
    [(2, "RuStore and AppGallery need at least 3"), (9, "Play and AppGallery allow at most 8")],
)
def test_frame_count_against_stores(tmp_path, count, needle):
    def mutate(d):
        d["targets"] = ["android-phone"]
        feature = d["frames"][1]
        d["frames"] = [dict(feature) for _ in range(count)]

    fails = _fails(_issues(_project(tmp_path, mutate)))
    assert any(needle in f.message for f in fails), [f.message for f in fails]


def test_bad_json_reports_line(tmp_path):
    path = tmp_path / "series.json"
    path.write_text('{\n  "app": {,\n}')
    with pytest.raises(series.SeriesError, match="line 2"):
        series.load(path)

