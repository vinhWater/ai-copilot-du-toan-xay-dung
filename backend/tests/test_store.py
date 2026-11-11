from app.store import DATA_PATH, load

C = load(DATA_PATH)


def test_load_sample():
    assert len(C.van_ban) == 3
    assert all(v.minh_hoa for v in C.van_ban)
    assert all("MINHHOA" in v.so_hieu for v in C.van_ban)
