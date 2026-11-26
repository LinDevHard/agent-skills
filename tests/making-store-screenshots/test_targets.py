from targets import STORE_LIMITS, TARGETS


def test_every_rustore_size_is_9_16_or_16_9():
    # RuStore stretches or crops any other ratio.
    for t in TARGETS.values():
        if "rustore" in t.stores:
            for w, h in t.sizes:
                assert w * 16 == h * 9 or w * 9 == h * 16, (t.name, w, h)


def test_android_phone_budget_is_appgallery():
    assert TARGETS["android-phone"].max_bytes == 2 * 1024 * 1024


def test_frame_counts_intersect_stores():
    phone = TARGETS["android-phone"]
    assert (phone.min_frames, phone.max_frames) == (3, 8)
    ios = TARGETS["ios-phone"]
    assert (ios.min_frames, ios.max_frames) == (1, 10)


def test_sizes_within_store_sides():
    for t in TARGETS.values():
        for store in t.stores:
            lim = STORE_LIMITS[store]
            for w, h in t.sizes:
                assert lim.min_side <= min(w, h) and max(w, h) <= lim.max_side, (t.name, store)
                assert max(w, h) / min(w, h) <= lim.max_ratio, (t.name, store)


def test_tablet_targets_are_9_16_or_16_9():
    for name in ("android-tablet-7", "android-tablet-7-landscape", "android-tablet-10", "android-tablet-10-landscape"):
        t = TARGETS[name]
        assert t.form == "tablet" and t.stores == ("play", "rustore")
        assert t.min_frames == 4  # Play large screens
        for w, h in t.sizes:
            assert w * 16 == h * 9 or w * 9 == h * 16, (name, w, h)


def test_foldable_sizes_within_play_sides():
    inner, outer = TARGETS["android-foldable"], TARGETS["android-foldable-outer"]
    assert inner.form == "foldable" and outer.form == "phone"  # the outer screen shows phone UI
    for t in (inner, outer):
        assert t.stores == ("play",) and (t.min_frames, t.max_frames) == (3, 8)
        for w, h in t.sizes:
            assert 960 <= min(w, h) and max(w, h) <= 3840
    assert {round(w / h, 3) for w, h in inner.sizes} == {1.0, round(4 / 3, 3)}
    assert [round(w / h, 3) for w, h in outer.sizes] == [round(10 / 16, 3)]


def test_ipad_both_orientations():
    assert TARGETS["ios-ipad"].sizes == ((2064, 2752),)
    assert TARGETS["ios-ipad-landscape"].sizes == ((2752, 2064),)
    assert TARGETS["ios-ipad"].form == "tablet" and TARGETS["ios-phone"].form == "phone"
