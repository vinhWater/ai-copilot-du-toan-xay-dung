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


def test_so_hieu_co_dau_cach(tmp_path):
    import zipfile
    f = tmp_path / "x.docx"
    xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           '<w:p><w:r><w:t>Số: 91 /2026/VBHN-BXD</w:t></w:r></w:p></w:body></w:document>')
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("word/document.xml", xml)
    assert paragraphs(f) == ["Số: 91/2026/VBHN-BXD"]


def _rels(so_hieu: str, paras: list[str]) -> set[tuple]:
    return {(q.loai, q.dich, q.dich_dieu, q.dich_khoan) for q in extract(so_hieu, paras)}


# Các câu dưới đây chép nguyên văn từ văn bản thật trong data/raw/ (chưa đối chiếu nguồn chính thống)
def test_thay_the_o_dieu_khoan_thi_hanh_tt38():
    paras = ["Số: 38/2026/TT-BXD", "Điều 2. Điều khoản thi hành",
             "1. Thông tư này có hiệu lực kể từ ngày 01 tháng 7 năm 2026.",
             "2. Thông tư này thay thế Thông tư số 12/2021/TT-BXD, Thông tư số 09/2024/TT-BXD, Thông tư số "
             "08/2025/TT-BXD và Điều 2 Thông tư số 60/2025/TT-BXD của Bộ trưởng Bộ Xây dựng./."]
    got = extract("38/2026/TT-BXD", paras)
    assert {(q.loai, q.dich, q.dich_dieu) for q in got} == {
        ("thay_the", "12/2021/TT-BXD", None), ("thay_the", "09/2024/TT-BXD", None),
        ("thay_the", "08/2025/TT-BXD", None), ("thay_the", "60/2025/TT-BXD", "2")}
    assert all(q.ngay_hieu_luc == date(2026, 7, 1) and q.nguon_dieu == "2" for q in got)


def test_thay_the_ngay_tren_dong_dieu_tt37():
    paras = ["Số: 37/2026/TT-BXD", "Điều 3. Thông tư này có hiệu lực kể từ ngày 01 tháng 7 năm 2026.",
             "Điều 4. Thông tư này thay thế Thông tư số 13/2021/TT-BXD ngày 31 tháng 8 năm 2021, Thông tư số "
             "01/2025/TT-BXD ngày 22 tháng 01 năm 2025, Điều 12 Thông tư số 09/2025/TT-BXD ngày 13 tháng 6 năm 2025, "
             "khoản 6 Điều 1 và Điều 3 Thông tư số 60/2025/TT-BXD ngày 30 tháng 12 năm 2025."]
    assert _rels("37/2026/TT-BXD", paras) == {
        ("thay_the", "13/2021/TT-BXD", None, None), ("thay_the", "01/2025/TT-BXD", None, None),
        ("thay_the", "09/2025/TT-BXD", "12", None), ("thay_the", "60/2025/TT-BXD", "1", "6"),
        ("thay_the", "60/2025/TT-BXD", "3", None)}


def test_bai_bo_bo_so_hieu_trong_phan_mo_ta_tt36_tt32():
    tt36 = ["Số: 36/2026/TT-BXD", "Điều 16. Hiệu lực thi hành",
            "1. Thông tư này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2026.",
            "2. Thông tư này bãi bỏ Thông tư số 11/2021/TT-BXD ngày 31 tháng 8 năm 2021 của Bộ trưởng Bộ Xây dựng về "
            "hướng dẫn một số nội dung xác định và quản lý chi phí đầu tư xây dựng; Thông tư số 14/2023/TT-BXD ngày 29 "
            "tháng 12 năm 2023 và Điều 1, Phụ lục III và Phụ lục V Thông tư số 60/2025/TT-BXD ngày 30 tháng 12 năm 2025."]
    assert _rels("36/2026/TT-BXD", tt36) == {
        ("bai_bo", "11/2021/TT-BXD", None, None), ("bai_bo", "14/2023/TT-BXD", None, None),
        ("bai_bo", "60/2025/TT-BXD", "1", None)}
    tt32 = ["Số: 32/2026/TT-BXD", "Điều 8. Hiệu lực thi hành",
            "1. Thông tư này có hiệu lực thi hành kể từ ngày 01 tháng 7 năm 2026.",
            "2. Bãi bỏ các điều 2, 3, 4, 5, 6, 7, 8, 9 và 19 Thông tư số 10/2021/TT-BXD ngày 25 tháng 8 năm 2021 của Bộ "
            "trưởng Bộ Xây dựng về hướng dẫn một số điều và biện pháp thi hành Nghị định số 06/2021/NĐ-CP ngày 26 tháng "
            "01 năm 2021 và Nghị định số 44/2016/NĐ-CP ngày 15 tháng 5 năm 2016 của Chính phủ./."]
    got = _rels("32/2026/TT-BXD", tt32)
    assert {d for _, sh, d, _ in got} == {"2", "3", "4", "5", "6", "7", "8", "9", "19"}
    assert {(l, sh) for l, sh, _, _ in got} == {("bai_bo", "10/2021/TT-BXD")}


def test_sua_doi_chi_neu_o_ten_van_ban_tt09():
    paras = ["Số: 09/2024/TT-BXD", "THÔNG TƯ",
             "SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐỊNH MỨC XÂY DỰNG BAN HÀNH TẠI THÔNG TƯ SỐ 12/2021/TT-BXD NGÀY 31 THÁNG 8 NĂM 2021",
             "Điều 3. Điều khoản thi hành", "Thông tư này có hiệu lực thi hành kể từ ngày 15 tháng 10 năm 2024./."]
    got = extract("09/2024/TT-BXD", paras)
    assert {(q.loai, q.dich, q.dich_dieu) for q in got} == {("sua_doi", "12/2021/TT-BXD", None)}
    assert got[0].ngay_hieu_luc == date(2024, 10, 15)
