"""Impact Analysis: văn bản mới (đã duyệt quan hệ) ảnh hưởng điều khoản, định mức nào + webhook document.updated."""
import json
import logging
import os
import urllib.request

from .models import AnhHuong, Corpus, ImpactOut

LOAI_THAY_DOI = ("sua_doi", "bo_sung", "bai_bo", "thay_the")  # can_cu / huong_dan không đổi nội dung
log = logging.getLogger(__name__)


def phan_tich(c: Corpus, so_hieu: str) -> ImpactOut:
    rels = [q for q in c.quan_he
            if q.nguon == so_hieu and q.trang_thai_duyet == "da_duyet" and q.loai in LOAI_THAY_DOI]
    dks: dict[tuple[str, str, str], AnhHuong] = {}
    for q in rels:
        for dk in c.dieu_khoan:
            if dk.van_ban == q.dich and q.dich_dieu in (None, dk.dieu) and q.dich_khoan in (None, dk.khoan):
                dks.setdefault((dk.van_ban, dk.dieu, dk.khoan), AnhHuong(
                    so_hieu=dk.van_ban, dieu=dk.dieu, khoan=dk.khoan, loai=q.loai, ngay_hieu_luc=q.ngay_hieu_luc))
    van_ban = sorted({q.dich for q in rels})
    # ponytail: định mức chỉ biết căn cứ cấp văn bản → báo mọi định mức của văn bản bị ảnh hưởng (thừa còn hơn sót)
    dinh_muc = [d.ma_hieu for d in c.dinh_muc if d.can_cu_so_hieu in van_ban]
    return ImpactOut(so_hieu=so_hieu, van_ban=van_ban, dieu_khoan=list(dks.values()), dinh_muc=dinh_muc)


def gui_webhook(payload: dict) -> None:
    """POST JSON tới các URL trong WEBHOOK_URLS (phân tách dấu phẩy). Lỗi chỉ ghi log.

    ponytail: không retry/hàng đợi; thêm khi Module 2 cần đảm bảo nhận đủ sự kiện."""
    body = json.dumps(payload, ensure_ascii=False, default=str).encode()
    for url in filter(None, (u.strip() for u in os.environ.get("WEBHOOK_URLS", "").split(","))):
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=5).close()
        except OSError as e:
            log.warning("Webhook %s lỗi: %s", url, e)
