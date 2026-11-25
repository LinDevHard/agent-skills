"""Load and validate a series.json.

Coordinates: `offset[0]` and decor `x` are measured in frames from the canvas's left edge of the frame
the element belongs to (decor: from the canvas's left edge), so 1.5 is the middle of the next frame.
`offset[1]`, decor `y` are fractions of frame height; decor `w` is a fraction of frame width.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from targets import STORE_LIMITS, TARGETS

# Display names, in the order stores are listed in messages.
STORE_NAMES = {
    "appstore": "App Store",
    "play": "Play",
    "rustore": "RuStore",
    "appgallery": "AppGallery",
    "fdroid": "F-Droid",
}
MAX_SHOTS_PER_FRAME = 3  # Pixstage lays out one to three shots per frame.
PLATFORMS = ("ios", "android", "web")


class SeriesError(Exception):
    pass


@dataclass
class Issue:
    level: Literal["FAIL", "warn"]
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level} {self.where}: {self.message}"


@dataclass
class App:
    name: str
    brand: list[str] = field(default_factory=list)
    icon: str | None = None


@dataclass
class StyleRef:
    name: str = "minimal"
    overrides: dict = field(default_factory=dict)


@dataclass
class Crop:
    top: int = 0
    bottom: int = 0


@dataclass
class ShotRef:
    path: str | dict[str, str]
    platform: str | None = None
    layout: str = "phone"
    rotate: float = 0.0
    tilt: float = 0.0
    crop: Crop | None = None
    offset: tuple[float, float] = (0.5, 0.0)
    scale: float = 1.0

    def path_for(self, platform: str) -> str | None:
        """The file to use on a target platform, or None when this shot must not appear there."""
        if isinstance(self.path, dict):
            return self.path.get(platform) or self.path.get("web")
        if platform == "ios" and self.platform == "android":
            return None
        return self.path

    def all_paths(self) -> list[str]:
        return list(self.path.values()) if isinstance(self.path, dict) else [self.path]


@dataclass
class Frame:
    role: Literal["cover", "feature"] = "feature"
    span: int = 1
    shots: list[ShotRef] = field(default_factory=list)
    caption: dict[str, str] = field(default_factory=dict)
    subtitle: dict[str, str] = field(default_factory=dict)
    alt: dict[str, str] = field(default_factory=dict)


@dataclass
class Decor:
    kind: str
    x: float
    y: float
    w: float = 0.3
    rotate: float = 0.0
    color: str | None = None


@dataclass
class Output:
    workdir: str = "store/screenshots"
    project_root: str = "."


@dataclass
class Series:
    app: App
    style: StyleRef
    targets: list[str]
    locales: list[str]
    frames: list[Frame]
    decor: list[Decor] = field(default_factory=list)
    output: Output = field(default_factory=Output)

    @property
    def frame_count(self) -> int:
        return sum(f.span for f in self.frames)


def _shot(d: dict) -> ShotRef:
    d = dict(d)
    if d.get("crop") is not None:
        d["crop"] = Crop(**d["crop"])
    if "offset" in d:
        d["offset"] = tuple(d["offset"])
    return ShotRef(**d)


def load(path: Path) -> Series:
    path = Path(path)
    if not path.exists():
        raise SeriesError(f"{path} not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SeriesError(f"{path}: invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}") from e
    try:
        frames = []
        for f in raw.get("frames", []):
            f = dict(f)
            f["shots"] = [_shot(s) for s in f.get("shots", [])]
            frames.append(Frame(**f))
        return Series(
            app=App(**raw["app"]),
            style=StyleRef(**raw.get("style", {})),
            targets=list(raw.get("targets", [])),
            locales=list(raw.get("locales", [])),
            frames=frames,
            decor=[Decor(**d) for d in raw.get("decor", [])],
            output=Output(**raw.get("output", {})),
        )
    except (KeyError, TypeError) as e:
        raise SeriesError(f"{path}: unexpected or missing field: {e}") from e


def _names(stores: list[str]) -> str:
    return " and ".join(name for key, name in STORE_NAMES.items() if key in stores)


def validate(s: Series, base_dir: Path) -> list[Issue]:
    issues: list[Issue] = []

    def fail(where: str, msg: str) -> None:
        issues.append(Issue("FAIL", where, msg))

    def warn(where: str, msg: str) -> None:
        issues.append(Issue("warn", where, msg))

    if not s.targets:
        fail("targets", f"no targets; use some of: {', '.join(TARGETS)}")
    for t in s.targets:
        if t not in TARGETS:
            fail("targets", f"unknown target '{t}'; known: {', '.join(TARGETS)}")
    if not s.locales:
        fail("locales", "no locales; use the listing's locales, e.g. en-US")

    series_targets = [TARGETS[t] for t in s.targets if t in TARGETS and t != "feature-graphic"]
    stores = sorted({st for t in series_targets for st in t.stores})
    n = s.frame_count
    too_few = [st for st in stores if n < STORE_LIMITS[st].min_frames]
    too_many = [st for st in stores if n > STORE_LIMITS[st].max_frames]
    if too_few:
        need = max(STORE_LIMITS[st].min_frames for st in too_few)
        fail("frames", f"{n} frames; {_names(too_few)} need at least {need}")
    if too_many:
        cap = min(STORE_LIMITS[st].max_frames for st in too_many)
        fail("frames", f"{n} frames; {_names(too_many)} allow at most {cap}")

    ios = any(t.platform == "ios" for t in series_targets)
    for i, frame in enumerate(s.frames):
        where = f"frames[{i}]"
        if frame.role not in ("cover", "feature"):
            fail(where, f"role '{frame.role}' must be 'cover' or 'feature'")
        if frame.span not in (1, 2):
            fail(where, f"span {frame.span} must be 1 or 2")
        if not frame.shots:
            fail(where, "no shots; every frame must show the app's real UI (App Store 2.3.3)")
        if len(frame.shots) > MAX_SHOTS_PER_FRAME:
            fail(where, f"{len(frame.shots)} shots; at most {MAX_SHOTS_PER_FRAME} per frame")
        for j, shot in enumerate(frame.shots):
            swhere = f"{where}.shots[{j}]"
            if not isinstance(shot.path, dict) and shot.platform not in PLATFORMS:
                fail(swhere, f"set platform to one of {', '.join(PLATFORMS)}")
            for p in shot.all_paths():
                if not (base_dir / p).is_file():
                    existing = sorted(x.name for x in (base_dir / p).parent.glob("*"))[:10]
                    fail(swhere, f"file {p} not found; that folder has: {', '.join(existing) or 'nothing'}")
            if ios and shot.path_for("ios") is None:
                fail(swhere, "Android shot in an App Store target: Apple 2.3.10 forbids Android imagery; "
                     "add an ios path or drop the ios targets")
        for loc in s.locales:
            if not frame.caption.get(loc):
                warn(where, f"no caption for {loc}")
    return issues
