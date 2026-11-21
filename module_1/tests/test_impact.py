"""Impact Analysis + webhook. Dữ liệu MINH HỌA (sample.json)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

import app.main as main
from conftest import MINH_HOA
from app.impact import gui_webhook, phan_tich
from app.models import QuanHe
from app.store import load


def test_impact_sua_doi_ca_van_ban():
    r = phan_tich(load(MINH_HOA), "03/2026/TT-MINHHOA")
    assert r.van_ban == ["02/2026/TT-MINHHOA"]
    assert {(a.dieu, a.khoan) for a in r.dieu_khoan} == {("1", "1"), ("2", "1")}
    assert r.dinh_muc == ["MH.0001", "MH.0002"]


def test_impact_cap_khoan_va_bo_qua_can_cu():
    c = load(MINH_HOA)
    c.quan_he = [
        QuanHe(nguon="X", dich="02/2026/TT-MINHHOA", loai="bai_bo", dich_dieu="2", dich_khoan="1",
               trang_thai_duyet="da_duyet"),
        QuanHe(nguon="X", dich="01/2026/ND-MINHHOA", loai="can_cu", trang_thai_duyet="da_duyet"),
        QuanHe(nguon="X", dich="02/2026/TT-MINHHOA", loai="sua_doi", dich_dieu="1", trang_thai_duyet="de_xuat"),
    ]
    r = phan_tich(c, "X")
    assert [(a.dieu, a.khoan, a.loai) for a in r.dieu_khoan] == [("2", "1", "bai_bo")]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "CORPUS", load(MINH_HOA))
    monkeypatch.setattr(main, "STATE", None)
    return TestClient(main.app)


def test_impact_api(client):
    assert client.get("/impact/03/2026/TT-MINHHOA").json()["van_ban"] == ["02/2026/TT-MINHHOA"]
    assert client.get("/impact/99/2026/X").status_code == 404


def test_approve_ban_webhook(client, monkeypatch):
    sent = []
    monkeypatch.setattr(main, "gui_webhook", sent.append)
    main.CORPUS.quan_he.append(QuanHe(nguon="03/2026/TT-MINHHOA", dich="02/2026/TT-MINHHOA", loai="bai_bo",
                                      dich_dieu="1", dich_khoan="1", trang_thai_duyet="de_xuat"))
    can_cu = next(q.id for q in main.CORPUS.quan_he if q.loai == "can_cu" and q.trang_thai_duyet == "de_xuat")
    client.post(f"/relations/{can_cu}/approve")
    assert sent == []  # căn cứ không đổi nội dung → không bắn
    bai_bo = main.CORPUS.quan_he[-1].id
    client.post(f"/relations/{bai_bo}/approve")
    assert sent[0]["event"] == "document.updated" and sent[0]["impact"]["so_hieu"] == "03/2026/TT-MINHHOA"


def test_gui_webhook_that(monkeypatch):
    got = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            got.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    monkeypatch.setenv("WEBHOOK_URLS", f"http://127.0.0.1:{srv.server_port}/hook, http://127.0.0.1:1/chet")
    gui_webhook({"event": "document.updated", "so_hieu": "Đ"})  # URL thứ 2 lỗi chỉ ghi log
    srv.server_close()
    assert got == [{"event": "document.updated", "so_hieu": "Đ"}]
