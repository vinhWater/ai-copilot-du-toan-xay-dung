"""Validity Agent: áp quan hệ đã duyệt vào phiên bản điều khoản + tình trạng hiệu lực theo ngày."""
from datetime import date

from .models import Corpus, DieuKhoan, NguonSuaDoi, PhienBan, QuanHe, TinhTrang
from .store import tim_van_ban


def _dong(dk: DieuKhoan, d: date) -> None:
    """Kết thúc phiên bản đang mở tại ngày d (khoảng [tu, den))."""
    for pb in dk.phien_ban:
        if pb.hieu_luc_den is None and pb.hieu_luc_tu < d:
            pb.hieu_luc_den = d


def ap_dung(c: Corpus, q: QuanHe) -> list[str]:
    """Áp 1 quan hệ đã duyệt vào phiên bản điều khoản. Trả cảnh báo (không áp được gì)."""
    d = q.ngay_hieu_luc
    if q.loai in ("can_cu", "huong_dan"):
        return []
    if d is None:
        return [f"Quan hệ {q.id} thiếu ngày hiệu lực — chưa áp vào phiên bản"]
    if q.loai in ("sua_doi", "bo_sung") and not (q.noi_dung_moi and q.dich_dieu):
        return [f"Quan hệ {q.id} thiếu điều đích hoặc nội dung mới — chưa áp vào phiên bản"]

    targets = [
        dk for dk in c.dieu_khoan
        if dk.van_ban == q.dich and (q.dich_dieu is None or dk.dieu == q.dich_dieu)
        and (q.dich_khoan is None or dk.khoan == q.dich_khoan)
    ]
    for dk in targets:
        _dong(dk, d)
    if q.loai in ("bai_bo", "thay_the"):
        return [] if targets else [f"Văn bản đích {q.dich} chưa có điều khoản trong kho — chỉ ghi quan hệ"]

    khoan = q.dich_khoan or "0"
    moi = PhienBan(noi_dung=q.noi_dung_moi, hieu_luc_tu=d,
                   nguon_sua_doi=NguonSuaDoi(so_hieu=q.nguon, dieu=q.nguon_dieu or ""))
    dk = next((t for t in targets if t.khoan == khoan), None)
    if dk is None:
        tieu_de = targets[0].tieu_de if targets else ""
        c.dieu_khoan.append(DieuKhoan(van_ban=q.dich, dieu=q.dich_dieu, khoan=khoan, tieu_de=tieu_de, phien_ban=[moi]))
    else:
        dk.phien_ban.append(moi)
    return []


def tinh_trang(c: Corpus, so_hieu: str, as_of: date) -> TinhTrang | None:
    """None = văn bản chỉ được viện dẫn, không có quan hệ nào cho biết hiệu lực."""
    rels = [q for q in c.quan_he if q.dich == so_hieu and q.trang_thai_duyet == "da_duyet"
            and q.ngay_hieu_luc and q.ngay_hieu_luc <= as_of]
    if any(q.loai in ("thay_the", "bai_bo") and q.dich_dieu is None for q in rels):
        return "het_hieu_luc"
    vb = tim_van_ban(c, so_hieu)
    if vb is None or vb.ngay_hieu_luc is None:
        return None
    if as_of < vb.ngay_hieu_luc:
        return "chua_co_hieu_luc"
    if any(q.loai in ("sua_doi", "bai_bo") for q in rels):  # bo_sung chỉ thêm, không làm hết hiệu lực
        return "het_hieu_luc_mot_phan"
    return "con_hieu_luc"
