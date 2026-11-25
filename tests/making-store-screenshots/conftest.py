import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "plugins/store-assets/skills/making-store-screenshots"
sys.path.insert(0, str(SKILL_DIR / "scripts"))
