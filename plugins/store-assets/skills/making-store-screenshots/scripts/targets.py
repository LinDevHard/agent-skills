"""Render targets and store limits.

Store rules checked 2026-11-26 against the official pages listed in references/store-rules.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MB = 1024 * 1024


@dataclass(frozen=True)
class StoreLimit:
    max_bytes: int
    min_frames: int
    max_frames: int
    min_side: int
    max_side: int
    max_ratio: float


STORE_LIMITS: dict[str, StoreLimit] = {
    # Apple: 1-10 screenshots per display size; no file-size or side limits are published,
    # so Play's 8 MB and 320-3840 px act as a safe ceiling.
    "appstore": StoreLimit(8 * MB, 1, 10, 320, 3840, 2.3),
    # Play: 2-8 phone screenshots, <=8 MB, sides 320-3840 px, long side <=2.3x short side.
    "play": StoreLimit(8 * MB, 2, 8, 320, 3840, 2.3),
    # RuStore: >=3 per device type, uploads of up to 10, <=3 MB on phones, max 2160x3840,
    # 9:16 or 16:9 (anything else is stretched or cropped). No minimum side is published.
    "rustore": StoreLimit(3 * MB, 3, 10, 320, 3840, 16 / 9 + 0.01),
    # AppGallery: 3-8 screenshots, <=2 MB, sides 320-3840 px. No ratio limit is published.
    "appgallery": StoreLimit(2 * MB, 3, 8, 320, 3840, 2.3),
    # F-Droid publishes no count, size or ratio limits.
    "fdroid": StoreLimit(8 * MB, 1, 10, 320, 3840, 2.3),
}


@dataclass(frozen=True)
class Target:
    name: str
    sizes: tuple[tuple[int, int], ...]
    platform: Literal["ios", "android", "any"]
    stores: tuple[str, ...]
    max_bytes: int
    min_frames: int
    max_frames: int


def _target(
    name: str,
    sizes: tuple[tuple[int, int], ...],
    platform: Literal["ios", "android", "any"],
    stores: tuple[str, ...],
    max_bytes: int | None = None,
) -> Target:
    limits = [STORE_LIMITS[s] for s in stores]
    return Target(
        name=name,
        sizes=sizes,
        platform=platform,
        stores=stores,
        # The strictest store wins: one file set is uploaded to all of them.
        max_bytes=max_bytes if max_bytes is not None else min(lim.max_bytes for lim in limits),
        min_frames=max(lim.min_frames for lim in limits),
        max_frames=min(lim.max_frames for lim in limits),
    )


ANDROID_STORES = ("play", "rustore", "appgallery", "fdroid")

TARGETS: dict[str, Target] = {
    t.name: t
    for t in (
        # Apple requires the 6.3" (Dynamic Island, medium) size; the 6.9" size has the same aspect,
        # so both are drawn from one layout.
        _target("ios-phone", ((1320, 2868), (1206, 2622)), "ios", ("appstore",)),
        # Apple requires iPad 13" when the app runs on iPad.
        _target("ios-ipad", ((2064, 2752),), "ios", ("appstore",)),
        # One 9:16 set serves Play, RuStore (crops other ratios), AppGallery and F-Droid.
        _target("android-phone", ((1080, 1920),), "android", ANDROID_STORES),
        # Play tablets: 9:16 or 16:9, sides 1080-7680; RuStore tablets: <=5 MB.
        _target("android-tablet-7", ((1080, 1920),), "android", ("play", "rustore"), max_bytes=5 * MB),
        _target("android-tablet-10", ((1440, 2560),), "android", ("play", "rustore"), max_bytes=5 * MB),
        # Play feature graphic: exactly 1024x500, one per listing.
        Target("feature-graphic", ((1024, 500),), "any", ("play",), 8 * MB, 1, 1),
    )
}
