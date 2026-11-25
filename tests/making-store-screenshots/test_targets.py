from targets import STORE_LIMITS, TARGETS


def test_every_android_size_is_9_16():
    for t in TARGETS.values():
        if t.platform == "android":
            for w, h in t.sizes:
                assert w * 16 == h * 9, (t.name, w, h)


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
