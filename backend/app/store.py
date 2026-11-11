from difflib import SequenceMatcher
from datetime import date
from pathlib import Path

from .models import AmendRef, CitationIn, Corpus, DieuKhoan, GraphOut, PhienBan, QuanHe, SearchHit, VanBan, VerifyOut

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


def _norm(s: str) -> str:
    return " ".join(s.casefold().split())


def verify(c: Corpus, cit: CitationIn, as_of: date) -> VerifyOut:
    def out(**kw) -> VerifyOut:
        base = dict(citation=cit, exists=True, quote_match=0.0, valid_as_of=as_of, amended_by=[], current_text=None)
        return VerifyOut(**(base | kw))

    dk = tim_dieu_khoan(c, cit.so_hieu, cit.dieu, cit.khoan)
    if dk is None:
        return out(exists=False, status="not_found")
    pb = phien_ban_tai(dk, as_of)
    if pb is None:
        return out(status="not_in_force")
    amended_by = [
        AmendRef(so_hieu=p.nguon_sua_doi.so_hieu, dieu=p.nguon_sua_doi.dieu,
                 khoan=p.nguon_sua_doi.khoan, effective_date=p.hieu_luc_tu)
        for p in dk.phien_ban if p.nguon_sua_doi and p.hieu_luc_tu <= as_of
    ]
    q, text = _norm(cit.quote), _norm(pb.noi_dung)
    match = 0.0 if not q else 1.0 if q in text else round(SequenceMatcher(None, q, text).ratio(), 2)
    return out(status="amended" if amended_by else "valid", amended_by=amended_by,
               quote_match=match, current_text=pb.noi_dung)


def graph(c: Corpus, so_hieu: str, depth: int) -> GraphOut | None:
    """BFS vô hướng qua quan hệ đã duyệt, tối đa `depth` bước."""
    if tim_van_ban(c, so_hieu) is None:
        return None
    approved = [q for q in c.quan_he if q.trang_thai_duyet == "da_duyet"]
    seen, frontier = {so_hieu}, {so_hieu}
    edges: list[QuanHe] = []
    for _ in range(depth):
        nxt: set[str] = set()
        for q in approved:
            if (q.nguon in frontier or q.dich in frontier) and q not in edges:
                edges.append(q)
                nxt |= {q.nguon, q.dich} - seen
        seen |= nxt
        frontier = nxt
    nodes = [v for v in c.van_ban if v.so_hieu in seen]
    return GraphOut(root=so_hieu, nodes=nodes, edges=edges)
