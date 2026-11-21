"""PostgreSQL: chỉ chạy khi có TEST_DATABASE_URL (DB riêng cho test — bị xóa sạch dữ liệu)."""
import os

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import db
from app.store import load
from conftest import MINH_HOA

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="không có TEST_DATABASE_URL")


@pytest.fixture
def url():
    db.init(URL)
    with db.psycopg.connect(URL) as conn:
        conn.execute("TRUNCATE van_ban, dieu_khoan, phien_ban, quan_he, dinh_muc, hao_phi")
    return URL


def test_db_trong(url):
    assert db.load(url) is None


def test_ghi_doc_giu_nguyen(url):
    c = load(MINH_HOA)
    db.save(c, url)
    assert db.load(url).model_dump() == c.model_copy(update={
        "van_ban": sorted(c.van_ban, key=lambda v: v.so_hieu),
        "quan_he": sorted(c.quan_he, key=lambda q: (q.nguon, q.id)),
        "dinh_muc": sorted(c.dinh_muc, key=lambda d: d.ma_hieu),
    }).model_dump()


def test_duyet_luu_vao_db(url, monkeypatch):
    monkeypatch.setattr(main, "DB_URL", url)
    client = TestClient(main.app)
    rid = client.get("/relations", params={"trang_thai": "de_xuat"}).json()[0]["id"]
    client.post(f"/relations/{rid}/approve")
    assert next(q for q in db.load(url).quan_he if q.id == rid).trang_thai_duyet == "da_duyet"
