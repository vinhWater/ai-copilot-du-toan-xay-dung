import json
from datetime import date
from pathlib import Path

import pytest

from app.docx_text import paragraphs
from app.models import QuanHe
from app.relations import evaluate, extract

DATA = Path(__file__).parent.parent / "data"
DOCX = DATA / "raw" / "206_2026_ND-CP_457659.docx"
GOLD = DATA / "labels" / "206_2026_ND-CP.relations.json"


@pytest.mark.skipif(not DOCX.exists(), reason="thiếu file văn bản gốc")
def test_nd206_khop_nhan_chuan():
    gold = [QuanHe.model_validate(q) for q in json.loads(GOLD.read_text(encoding="utf-8"))["quan_he"]]
    pred = extract("206/2026/NĐ-CP", paragraphs(DOCX))
    assert all(q.trang_thai_duyet == "de_xuat" and q.trich_dan for q in pred)
    r = evaluate(pred, gold)
    assert r["precision"] == 1.0 and r["recall"] == 1.0, r
    thay = next(q for q in pred if q.loai == "thay_the")
    assert thay.dich == "10/2021/NĐ-CP" and thay.ngay_hieu_luc == date(2026, 7, 1)


def test_can_cu_trong_than_dieu_khong_tinh():
    paras = ["Số: 1/2026/TT-MINHHOA", "Căn cứ Nghị định số 9/2025/NĐ-MINHHOA;", "Điều 1. Phạm vi",
             "1. Căn cứ Thông tư số 8/2024/TT-MINHHOA, chủ đầu tư quyết định."]
    assert [(q.loai, q.dich) for q in extract("1/2026/TT-MINHHOA", paras)] == [("can_cu", "9/2025/NĐ-MINHHOA")]


def test_van_ban_sua_doi_minh_hoa():
    # Văn bản MINH HỌA, không phải văn bản thật
    paras = [
        "Số: 03/2026/TT-MINHHOA",
        "THÔNG TƯ SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA THÔNG TƯ SỐ 02/2026/TT-MINHHOA",
        "Căn cứ Nghị định số 01/2026/ND-MINHHOA;",
        "Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 02/2026/TT-MINHHOA",
        "1. Sửa đổi, bổ sung khoản 1 Điều 2 như sau:",
        "“1. Nội dung minh họa đã sửa đổi.”",
        "2. Bãi bỏ khoản 3 Điều 4.",
        "Điều 2. Hiệu lực thi hành",
        "Thông tư này có hiệu lực từ ngày 01 tháng 7 năm 2026.",
    ]
    got = {(q.loai, q.dich, q.dich_dieu, q.dich_khoan): q for q in extract("03/2026/TT-MINHHOA", paras)}
    sd = got[("sua_doi", "02/2026/TT-MINHHOA", "2", "1")]
    assert sd.noi_dung_moi == "1. Nội dung minh họa đã sửa đổi." and sd.ngay_hieu_luc == date(2026, 7, 1)
    assert ("bai_bo", "02/2026/TT-MINHHOA", "4", "3") in got
    assert ("can_cu", "01/2026/ND-MINHHOA", None, None) in got


def test_evaluate():
    a = QuanHe(nguon="A", dich="B", loai="can_cu", trang_thai_duyet="de_xuat")
    b = QuanHe(nguon="A", dich="C", loai="can_cu", trang_thai_duyet="de_xuat")
    assert evaluate([a, b], [a]) == {"tp": 1, "precision": 0.5, "recall": 1.0}
