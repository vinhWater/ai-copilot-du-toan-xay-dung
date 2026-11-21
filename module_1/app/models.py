import hashlib
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field

TinhTrang = Literal["chua_co_hieu_luc", "con_hieu_luc", "het_hieu_luc_mot_phan", "het_hieu_luc"]


class VanBan(BaseModel):
    """Văn bản chỉ được viện dẫn (chưa nạp vào kho) có các trường None = chưa có dữ liệu, không đoán."""
    so_hieu: str
    loai: str = ""
    co_quan_ban_hanh: str = ""
    ngay_ban_hanh: date | None = None
    ngay_hieu_luc: date | None = None
    tinh_trang: TinhTrang | None = None
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
    nguon_dieu: str | None = None  # điều của văn bản nguồn chứa câu quan hệ
    dich_dieu: str | None = None  # quan hệ cấp điều khoản: điều/khoản của văn bản đích
    dich_khoan: str | None = None
    noi_dung_moi: str | None = None  # sua_doi/bo_sung: nội dung thay vào điều khoản đích
    trich_dan: str = ""  # câu gốc làm bằng chứng cho người duyệt

    @computed_field
    @property
    def id(self) -> str:
        key = "|".join([self.nguon, self.loai, self.dich, self.dich_dieu or "", self.dich_khoan or ""])
        return hashlib.sha1(key.encode()).hexdigest()[:12]


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


class DuyetOut(BaseModel):
    quan_he: QuanHe
    canh_bao: list[str]


class AnhHuong(BaseModel):
    so_hieu: str
    dieu: str
    khoan: str
    loai: str  # loại quan hệ gây ảnh hưởng
    ngay_hieu_luc: date | None


class ImpactOut(BaseModel):
    so_hieu: str
    van_ban: list[str]  # văn bản bị sửa đổi / thay thế / bãi bỏ (kể cả chưa có trong kho)
    dieu_khoan: list[AnhHuong]
    dinh_muc: list[str]  # mã hiệu định mức có căn cứ là văn bản bị ảnh hưởng → cần rà soát


class ErrorDetail(BaseModel):
    code: Literal["document_not_found", "article_not_found", "not_in_force", "relation_not_found",
                  "relation_not_pending"]
    message: str


class ErrorOut(BaseModel):
    detail: ErrorDetail
