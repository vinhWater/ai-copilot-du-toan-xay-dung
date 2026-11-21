"""Validity Agent + API duyệt. Toàn bộ văn bản ở đây là MINH HỌA."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

import app.main as main
from conftest import MINH_HOA
from app.models import Corpus, DieuKhoan, PhienBan, QuanHe, VanBan
from app.store import load, phien_ban_tai, tim_dieu_khoan
from app.validity import ap_dung, tinh_trang

D = date(2026, 7, 1)


def corpus() -> Corpus:
    vb = VanBan(so_hieu="A", ngay_ban_hanh=date(2026, 1, 1), ngay_hieu_luc=date(2026, 2, 1))
    dk = lambda d, k: DieuKhoan(van_ban="A", dieu=d, khoan=k, phien_ban=[  # noqa: E731
        PhienBan(noi_dung=f"gốc {d}.{k}", hieu_luc_tu=date(2026, 2, 1))])
    return Corpus(van_ban=[vb], dieu_khoan=[dk("1", "1"), dk("1", "2"), dk("2", "1")], quan_he=[], dinh_muc=[])


def qh(loai, **kw) -> QuanHe:
    return QuanHe(nguon="B", dich="A", loai=loai, ngay_hieu_luc=D, trang_thai_duyet="da_duyet", **kw)


def test_sua_doi_tao_phien_ban_moi():
    c = corpus()
    q = qh("sua_doi", nguon_dieu="1", dich_dieu="1", dich_khoan="2", noi_dung_moi="mới")
    c.quan_he.append(q)
    assert ap_dung(c, q) == []
    dk = tim_dieu_khoan(c, "A", "1", "2")
    assert phien_ban_tai(dk, date(2026, 6, 30)).noi_dung == "gốc 1.2"
    pb = phien_ban_tai(dk, D)
    assert pb.noi_dung == "mới" and pb.nguon_sua_doi.so_hieu == "B" and pb.nguon_sua_doi.dieu == "1"
    assert phien_ban_tai(tim_dieu_khoan(c, "A", "1", "1"), D).noi_dung == "gốc 1.1"  # khoản khác không đổi
    assert tinh_trang(c, "A", D) == "het_hieu_luc_mot_phan"
    assert tinh_trang(c, "A", date(2026, 6, 30)) == "con_hieu_luc"


def test_bai_bo_dieu():
    c = corpus()
    ap_dung(c, qh("bai_bo", dich_dieu="1"))
    assert phien_ban_tai(tim_dieu_khoan(c, "A", "1", "1"), D) is None
    assert phien_ban_tai(tim_dieu_khoan(c, "A", "2", "1"), D) is not None


def test_thay_the_ca_van_ban():
    c = corpus()
    q = qh("thay_the")
    c.quan_he.append(q)
    ap_dung(c, q)
    assert all(phien_ban_tai(dk, D) is None for dk in c.dieu_khoan)
    assert tinh_trang(c, "A", D) == "het_hieu_luc"
    assert tinh_trang(c, "A", date(2026, 1, 15)) == "chua_co_hieu_luc"


def test_bo_sung_khoan_moi():
    c = corpus()
    ap_dung(c, qh("bo_sung", dich_dieu="1", dich_khoan="3", noi_dung_moi="thêm"))
    assert phien_ban_tai(tim_dieu_khoan(c, "A", "1", "3"), D).noi_dung == "thêm"


def test_thieu_noi_dung_khong_ap():
    c = corpus()
    assert ap_dung(c, qh("sua_doi", dich_dieu="1")) and len(c.dieu_khoan[0].phien_ban) == 1


def test_van_ban_vien_dan_khong_ro_tinh_trang():
    assert tinh_trang(corpus(), "LUAT-X", D) is None


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "CORPUS", load(MINH_HOA))
    monkeypatch.setattr(main, "STATE", None)
    return TestClient(main.app)


def test_duyet_quan_he(client):
    pend = client.get("/relations", params={"trang_thai": "de_xuat"}).json()
    assert len(pend) == 1 and pend[0]["dich"] == "01/2026/ND-MINHHOA"
    r = client.post(f"/relations/{pend[0]['id']}/approve")
    assert r.status_code == 200 and r.json()["quan_he"]["trang_thai_duyet"] == "da_duyet"
    again = client.post(f"/relations/{pend[0]['id']}/approve")
    assert again.status_code == 409 and again.json()["detail"]["code"] == "relation_not_pending"
    g = client.get("/graph/01/2026/ND-MINHHOA").json()
    assert {e["nguon"] for e in g["edges"]} == {"02/2026/TT-MINHHOA", "03/2026/TT-MINHHOA"}


def test_tu_choi_va_404(client):
    rid = client.get("/relations", params={"trang_thai": "de_xuat"}).json()[0]["id"]
    assert client.post(f"/relations/{rid}/reject").json()["trang_thai_duyet"] == "tu_choi"
    assert client.post("/relations/khong-co/approve").json()["detail"]["code"] == "relation_not_found"


def test_tinh_trang_theo_ngay_api(client):
    assert client.get("/documents/02/2026/TT-MINHHOA", params={"as_of_date": "2026-04-01"}).json()["tinh_trang"] == "con_hieu_luc"
    assert client.get("/documents/02/2026/TT-MINHHOA", params={"as_of_date": "2026-08-01"}).json()["tinh_trang"] == "het_hieu_luc_mot_phan"


def test_luu_file_trang_thai(client, tmp_path, monkeypatch):
    state = tmp_path / "corpus.json"
    monkeypatch.setattr(main, "STATE", state)
    rid = client.get("/relations", params={"trang_thai": "de_xuat"}).json()[0]["id"]
    client.post(f"/relations/{rid}/approve")
    assert next(q for q in load(state).quan_he if q.id == rid).trang_thai_duyet == "da_duyet"
