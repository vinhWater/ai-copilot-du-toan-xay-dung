from datetime import date
from pathlib import Path

from .models import Corpus, DieuKhoan, PhienBan, SearchHit, VanBan

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


def search(c: Corpus, query: str, as_of: date, top_k: int) -> list[SearchHit]:
    # ponytail: keyword đếm token, thay bằng hybrid pgvector + full-text khi có Postgres
    q = query.casefold()
    tokens = q.split()
    hits: list[SearchHit] = []
    for dk in c.dieu_khoan:
        pb = phien_ban_tai(dk, as_of)
        if pb is None:
            continue
        text = f"{dk.van_ban} {dk.tieu_de} {pb.noi_dung}".casefold()
        score = float(sum(t in text for t in tokens)) + (10.0 if dk.van_ban.casefold() in q else 0.0)
        if score == 0:
            continue
        vb = tim_van_ban(c, dk.van_ban)
        hits.append(SearchHit(
            so_hieu=dk.van_ban, dieu=dk.dieu, khoan=dk.khoan, tieu_de=dk.tieu_de, noi_dung=pb.noi_dung,
            hieu_luc_tu=pb.hieu_luc_tu, hieu_luc_den=pb.hieu_luc_den, score=score,
            minh_hoa=vb.minh_hoa if vb else True,
        ))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]
