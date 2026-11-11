from datetime import date

from fastapi import FastAPI, HTTPException

from .models import ArticleOut, VanBan
from .store import DATA_PATH, load, phien_ban_tai, tim_dieu_khoan, tim_van_ban

app = FastAPI(
    title="Legal Knowledge API (MOCK — dữ liệu minh họa)",
    description="Mock server Module 1. Toàn bộ dữ liệu là MINH HỌA, chưa xác minh nguồn chính thống.",
)
CORPUS = load(DATA_PATH)


@app.get("/documents/{so_hieu:path}")
def get_document(so_hieu: str) -> VanBan:
    vb = tim_van_ban(CORPUS, so_hieu)
    if vb is None:
        raise HTTPException(404, "Không tìm thấy văn bản")
    return vb


@app.get("/articles/{so_hieu:path}/{dieu}/{khoan}")
def get_article(so_hieu: str, dieu: str, khoan: str, as_of_date: date | None = None) -> ArticleOut:
    as_of = as_of_date or date.today()
    dk = tim_dieu_khoan(CORPUS, so_hieu, dieu, khoan)
    if dk is None:
        raise HTTPException(404, "Không tìm thấy điều khoản")
    pb = phien_ban_tai(dk, as_of)
    if pb is None:
        raise HTTPException(404, f"Điều khoản không có hiệu lực tại ngày {as_of.isoformat()}")
    vb = tim_van_ban(CORPUS, so_hieu)
    return ArticleOut(
        so_hieu=so_hieu, dieu=dieu, khoan=khoan, tieu_de=dk.tieu_de, noi_dung=pb.noi_dung,
        hieu_luc_tu=pb.hieu_luc_tu, hieu_luc_den=pb.hieu_luc_den, nguon_sua_doi=pb.nguon_sua_doi,
        as_of_date=as_of, minh_hoa=vb.minh_hoa if vb else True,
    )
