from datetime import date
from pathlib import Path

from .models import Corpus, DieuKhoan, PhienBan, VanBan

DATA_PATH = Path(__file__).parent / "data" / "sample.json"


def load(path: Path) -> Corpus:
    return Corpus.model_validate_json(path.read_text(encoding="utf-8"))


def phien_ban_tai(dk: DieuKhoan, as_of: date) -> PhienBan | None:
    """Phiên bản có hiệu lực tại as_of: hieu_luc_tu <= as_of < hieu_luc_den (den=None: còn hiệu lực)."""
    for pb in dk.phien_ban:
        if pb.hieu_luc_tu <= as_of and (pb.hieu_luc_den is None or as_of < pb.hieu_luc_den):
            return pb
    return None


def tim_van_ban(c: Corpus, so_hieu: str) -> VanBan | None:
    return next((v for v in c.van_ban if v.so_hieu == so_hieu), None)


def tim_dieu_khoan(c: Corpus, so_hieu: str, dieu: str, khoan: str) -> DieuKhoan | None:
    return next(
        (d for d in c.dieu_khoan if d.van_ban == so_hieu and d.dieu == dieu and d.khoan == khoan),
        None,
    )
