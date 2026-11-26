import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "plugins/store-assets/skills/making-store-screenshots"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image  # noqa: E402

EXAMPLE = SKILL_DIR / "assets/series.example.json"


def write_project(tmp_path: Path, mutate=None, shot_size=(1080, 2400)) -> Path:
    """Copy the example series into tmp_path with placeholder shots; return the series.json path."""
    data = json.loads(EXAMPLE.read_text())
    if mutate:
        mutate(data)
    for frame in data["frames"]:
        for shot in frame["shots"]:
            paths = shot["path"].values() if isinstance(shot["path"], dict) else [shot["path"]]
            for p in paths:
                (tmp_path / p).parent.mkdir(parents=True, exist_ok=True)
                if not (tmp_path / p).exists():
                    Image.new("RGB", shot_size, "#e8ecff").save(tmp_path / p)
    path = tmp_path / "series.json"
    path.write_text(json.dumps(data, ensure_ascii=False))
    return path


@pytest.fixture
def project(tmp_path):
    return lambda mutate=None, **kw: write_project(tmp_path, mutate, **kw)
