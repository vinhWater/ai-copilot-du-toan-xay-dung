from datetime import date

from app.store import DATA_PATH, load, phien_ban_tai, search, tim_dieu_khoan

C = load(DATA_PATH)
DK = tim_dieu_khoan(C, "02/2026/TT-MINHHOA", "2", "1")


def test_load_sample():
    assert len(C.van_ban) == 3
    assert all(v.minh_hoa for v in C.van_ban)
    assert all("MINHHOA" in v.so_hieu for v in C.van_ban)


def test_bien_trai_tinh():
    assert phien_ban_tai(DK, date(2026, 3, 1)).nguon_sua_doi is None


def test_bien_phai_khong():
    assert phien_ban_tai(DK, date(2026, 7, 1)).nguon_sua_doi.so_hieu == "03/2026/TT-MINHHOA"


def test_ngay_truoc_cuoi():
    assert phien_ban_tai(DK, date(2026, 6, 30)).nguon_sua_doi is None


def test_truoc_hieu_luc():
    assert phien_ban_tai(DK, date(2026, 1, 1)) is None


def test_search_casefold():
    hits = search(C, "Bê Tông", date(2026, 8, 1), 5)
    assert hits and hits[0].so_hieu == "02/2026/TT-MINHHOA" and hits[0].dieu == "1"


def test_search_as_of_loc_phien_ban():
    texts = [h.noi_dung for h in search(C, "Điều 2 Khoản 1", date(2026, 8, 1), 50)]
    assert texts and not any("gốc" in t for t in texts)
