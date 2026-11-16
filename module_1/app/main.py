import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query

from .models import (ArticleOut, CitationIn, DinhMuc, DuyetOut, ErrorOut, GraphOut, QuanHe, SearchHit, SearchIn,
                     VanBan, VerifyOut)
from .store import DATA_PATH, graph, load, norms, phien_ban_tai, save, search, tim_dieu_khoan, tim_van_ban, verify
from .validity import ap_dung, tinh_trang

app = FastAPI(
    title="Legal Knowledge API — Module 1",
    description="Bản ghi có `minh_hoa: true` là dữ liệu MINH HỌA hoặc chưa xác minh nguồn chính thống. "
    "Lỗi 404/409: `detail.code` ∈ document_not_found | article_not_found | not_in_force | "
    "relation_not_found | relation_not_pending.",
)
# CORPUS_PATH: file trạng thái (duyệt quan hệ, văn bản nạp mới). Không đặt = chỉ trong RAM, đọc sample.json.
STATE = Path(os.environ["CORPUS_PATH"]) if os.environ.get("CORPUS_PATH") else None
CORPUS = load(STATE if STATE and STATE.exists() else DATA_PATH)
LOCK = threading.Lock()  # ponytail: 1 lock toàn cục + ghi cả file JSON; chuyển Postgres khi nhiều người duyệt cùng lúc
VN = ZoneInfo("Asia/Ho_Chi_Minh")
NOT_FOUND = {404: {"model": ErrorOut}}
REL_ERRORS = {404: {"model": ErrorOut}, 409: {"model": ErrorOut}}


def today_vn(now: datetime | None = None) -> date:
    """Ngày hiện tại theo giờ Việt Nam (container chạy UTC)."""
    return (now or datetime.now(VN)).astimezone(VN).date()


def persist() -> None:
    if STATE:
        save(CORPUS, STATE)


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, {"code": code, "message": message})


def _404(code: str, message: str) -> HTTPException:
    return _err(404, code, message)


def _voi_tinh_trang(vb: VanBan, as_of: date) -> VanBan:
    return vb.model_copy(update={"tinh_trang": tinh_trang(CORPUS, vb.so_hieu, as_of)})


@app.get("/documents/{so_hieu:path}", responses=NOT_FOUND)
def get_document(so_hieu: str, as_of_date: date | None = None) -> VanBan:
    vb = tim_van_ban(CORPUS, so_hieu)
    if vb is None:
        raise _404("document_not_found", "Không tìm thấy văn bản")
    return _voi_tinh_trang(vb, as_of_date or today_vn())


@app.get("/articles/{so_hieu:path}/{dieu}/{khoan}", responses=NOT_FOUND)
def get_article(so_hieu: str, dieu: str, khoan: str, as_of_date: date | None = None) -> ArticleOut:
    as_of = as_of_date or today_vn()
    dk = tim_dieu_khoan(CORPUS, so_hieu, dieu, khoan)
    if dk is None:
        raise _404("article_not_found", "Không tìm thấy điều khoản")
    pb = phien_ban_tai(dk, as_of)
    if pb is None:
        raise _404("not_in_force", f"Điều khoản không có hiệu lực tại ngày {as_of.isoformat()}")
    vb = tim_van_ban(CORPUS, so_hieu)
    return ArticleOut(
        so_hieu=so_hieu, dieu=dieu, khoan=khoan, tieu_de=dk.tieu_de, noi_dung=pb.noi_dung,
        hieu_luc_tu=pb.hieu_luc_tu, hieu_luc_den=pb.hieu_luc_den, nguon_sua_doi=pb.nguon_sua_doi,
        as_of_date=as_of, minh_hoa=vb.minh_hoa if vb else True,
    )


@app.post("/search")
def post_search(body: SearchIn) -> list[SearchHit]:
    return search(CORPUS, body.query, body.as_of_date or today_vn(), body.top_k)


@app.post("/citations/verify")
def post_verify(body: CitationIn) -> VerifyOut:
    return verify(CORPUS, body, body.as_of_date or today_vn())


@app.get("/graph/{so_hieu:path}", responses=NOT_FOUND)
def get_graph(so_hieu: str, depth: int = Query(1, ge=1, le=3), as_of_date: date | None = None) -> GraphOut:
    g = graph(CORPUS, so_hieu, depth)
    if g is None:
        raise _404("document_not_found", "Không tìm thấy văn bản")
    as_of = as_of_date or today_vn()
    g.nodes = [_voi_tinh_trang(n, as_of) for n in g.nodes]
    return g


@app.get("/norms")
def get_norms(ma_hieu: str | None = None, keyword: str | None = None) -> list[DinhMuc]:
    return norms(CORPUS, ma_hieu, keyword)


@app.get("/relations")
def list_relations(trang_thai: Literal["de_xuat", "da_duyet", "tu_choi"] | None = None,
                   so_hieu: str | None = None) -> list[QuanHe]:
    """Danh sách quan hệ (màn hình duyệt dùng `trang_thai=de_xuat`)."""
    return [q for q in CORPUS.quan_he
            if (trang_thai is None or q.trang_thai_duyet == trang_thai)
            and (so_hieu is None or so_hieu in (q.nguon, q.dich))]


def _pending(rid: str) -> QuanHe:
    q = next((q for q in CORPUS.quan_he if q.id == rid), None)
    if q is None:
        raise _404("relation_not_found", "Không tìm thấy quan hệ")
    if q.trang_thai_duyet != "de_xuat":
        raise _err(409, "relation_not_pending", f"Quan hệ đã ở trạng thái {q.trang_thai_duyet}")
    return q


@app.post("/relations/{rid}/approve", responses=REL_ERRORS)
def approve_relation(rid: str) -> DuyetOut:
    """Người duyệt xác nhận → ghi vào graph + áp vào phiên bản điều khoản (Validity Agent)."""
    with LOCK:
        q = _pending(rid)
        q.trang_thai_duyet = "da_duyet"
        canh_bao = ap_dung(CORPUS, q)
        persist()
    return DuyetOut(quan_he=q, canh_bao=canh_bao)


@app.post("/relations/{rid}/reject", responses=REL_ERRORS)
def reject_relation(rid: str) -> QuanHe:
    with LOCK:
        q = _pending(rid)
        q.trang_thai_duyet = "tu_choi"
        persist()
    return q


# Pipeline nạp văn bản (POST /ingest) do SV1 phụ trách; chỉ gắn vào khi file có mặt.
try:
    from .ingest import router as ingest_router
except ModuleNotFoundError as e:
    if e.name != f"{__package__}.ingest":
        raise
else:
    app.include_router(ingest_router)
