from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

TinhTrang = Literal["con_hieu_luc", "het_hieu_luc_mot_phan", "het_hieu_luc"]


class VanBan(BaseModel):
    so_hieu: str
    loai: str
    co_quan_ban_hanh: str
    ngay_ban_hanh: date
    ngay_hieu_luc: date
    tinh_trang: TinhTrang
    minh_hoa: bool = True


class NguonSuaDoi(BaseModel):
    so_hieu: str
    dieu: str
    khoan: str | None = None


class PhienBan(BaseModel):
    noi_dung: str
    hieu_luc_tu: date
    hieu_luc_den: date | None = None
    nguon_sua_doi: NguonSuaDoi | None = None


class DieuKhoan(BaseModel):
    van_ban: str
    dieu: str
    khoan: str
    tieu_de: str = ""
    phien_ban: list[PhienBan]


class QuanHe(BaseModel):
    nguon: str
    dich: str
    loai: Literal["thay_the", "sua_doi", "bo_sung", "huong_dan", "can_cu", "bai_bo"]
    ngay_hieu_luc: date | None = None
    trang_thai_duyet: Literal["de_xuat", "da_duyet", "tu_choi"]


class HaoPhi(BaseModel):
    loai: Literal["vat_lieu", "nhan_cong", "may"]
    ten: str
    don_vi: str
    gia_tri: float


class DinhMuc(BaseModel):
    ma_hieu: str
    ten_cong_tac: str
    don_vi: str
    hao_phi: list[HaoPhi]
    can_cu_so_hieu: str
    can_cu_phu_luc: str


class Corpus(BaseModel):
    van_ban: list[VanBan]
    dieu_khoan: list[DieuKhoan]
    quan_he: list[QuanHe]
    dinh_muc: list[DinhMuc]


class ArticleOut(BaseModel):
    so_hieu: str
    dieu: str
    khoan: str
    tieu_de: str
    noi_dung: str
    hieu_luc_tu: date
    hieu_luc_den: date | None
    nguon_sua_doi: NguonSuaDoi | None
    as_of_date: date
    minh_hoa: bool


class SearchIn(BaseModel):
    query: str = Field(min_length=1)
    as_of_date: date | None = None
    top_k: int = Field(5, ge=1, le=50)


class SearchHit(BaseModel):
    so_hieu: str
    dieu: str
    khoan: str
    tieu_de: str
    noi_dung: str
    hieu_luc_tu: date
    hieu_luc_den: date | None
    score: float
    minh_hoa: bool


class CitationIn(BaseModel):
    so_hieu: str
    dieu: str
    khoan: str
    quote: str = ""
    as_of_date: date | None = None


class AmendRef(BaseModel):
    so_hieu: str
    dieu: str
    khoan: str | None
    effective_date: date


class VerifyOut(BaseModel):
    citation: CitationIn
    exists: bool
    quote_match: float
    valid_as_of: date
    status: Literal["valid", "amended", "not_in_force", "not_found"]
    amended_by: list[AmendRef]
    current_text: str | None


class GraphOut(BaseModel):
    root: str
    nodes: list[VanBan]
    edges: list[QuanHe]


class ErrorDetail(BaseModel):
    code: Literal["document_not_found", "article_not_found", "not_in_force"]
    message: str


class ErrorOut(BaseModel):
    detail: ErrorDetail
