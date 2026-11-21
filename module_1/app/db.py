"""Lưu Corpus vào PostgreSQL (DATABASE_URL). API vẫn truy vấn Corpus trong RAM; DB là nơi lưu bền."""
from pathlib import Path

import psycopg

from .models import Corpus, DieuKhoan, DinhMuc, HaoPhi, NguonSuaDoi, PhienBan, QuanHe, VanBan

SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
VB_COLS = list(VanBan.model_fields)
QH_COLS = ["id", *QuanHe.model_fields]


def _rows(conn: psycopg.Connection, sql: str) -> list[dict]:
    cur = conn.execute(sql)
    names = [d.name for d in cur.description]
    return [dict(zip(names, r)) for r in cur]


def init(url: str) -> None:
    with psycopg.connect(url) as conn:
        conn.execute(SCHEMA)


def load(url: str) -> Corpus | None:
    """None nếu DB trống (lần chạy đầu → nạp dữ liệu khởi tạo)."""
    with psycopg.connect(url) as conn:
        van_ban = [VanBan(**r) for r in _rows(conn, "SELECT * FROM van_ban ORDER BY so_hieu")]
        if not van_ban:
            return None
        pbs: dict[int, list[PhienBan]] = {}
        for r in _rows(conn, "SELECT * FROM phien_ban ORDER BY dieu_khoan_id, thu_tu"):
            nguon = NguonSuaDoi(so_hieu=r["sua_doi_so_hieu"], dieu=r["sua_doi_dieu"], khoan=r["sua_doi_khoan"]) \
                if r["sua_doi_so_hieu"] else None
            pbs.setdefault(r["dieu_khoan_id"], []).append(PhienBan(
                noi_dung=r["noi_dung"], hieu_luc_tu=r["hieu_luc_tu"], hieu_luc_den=r["hieu_luc_den"], nguon_sua_doi=nguon))
        dieu_khoan = [DieuKhoan(van_ban=r["van_ban"], dieu=r["dieu"], khoan=r["khoan"], tieu_de=r["tieu_de"],
                                phien_ban=pbs.get(r["id"], []))
                      for r in _rows(conn, "SELECT * FROM dieu_khoan ORDER BY id")]
        quan_he = [QuanHe(**{k: v for k, v in r.items() if k != "id"})
                   for r in _rows(conn, "SELECT * FROM quan_he ORDER BY nguon, id")]
        hp: dict[str, list[HaoPhi]] = {}
        for r in _rows(conn, "SELECT * FROM hao_phi ORDER BY id"):
            hp.setdefault(r.pop("ma_hieu"), []).append(HaoPhi(**{k: v for k, v in r.items() if k != "id"}))
        dinh_muc = [DinhMuc(**r, hao_phi=hp.get(r["ma_hieu"], []))
                    for r in _rows(conn, "SELECT * FROM dinh_muc ORDER BY ma_hieu")]
    return Corpus(van_ban=van_ban, dieu_khoan=dieu_khoan, quan_he=quan_he, dinh_muc=dinh_muc)


def save(c: Corpus, url: str) -> None:
    # ponytail: ghi lại toàn bộ trong 1 transaction (vài trăm dòng, < 1 s); chuyển sang upsert từng bản ghi khi kho lớn
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE van_ban, dieu_khoan, phien_ban, quan_he, dinh_muc, hao_phi RESTART IDENTITY")
        cur.executemany(f"INSERT INTO van_ban ({', '.join(VB_COLS)}) VALUES ({', '.join(['%s'] * len(VB_COLS))})",
                        [[getattr(v, k) for k in VB_COLS] for v in c.van_ban])
        for dk in c.dieu_khoan:
            dk_id = cur.execute("INSERT INTO dieu_khoan (van_ban, dieu, khoan, tieu_de) VALUES (%s, %s, %s, %s) RETURNING id",
                                (dk.van_ban, dk.dieu, dk.khoan, dk.tieu_de)).fetchone()[0]
            cur.executemany(
                "INSERT INTO phien_ban (dieu_khoan_id, thu_tu, noi_dung, hieu_luc_tu, hieu_luc_den, "
                "sua_doi_so_hieu, sua_doi_dieu, sua_doi_khoan) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                [(dk_id, i, p.noi_dung, p.hieu_luc_tu, p.hieu_luc_den, *(
                    (p.nguon_sua_doi.so_hieu, p.nguon_sua_doi.dieu, p.nguon_sua_doi.khoan) if p.nguon_sua_doi
                    else (None, None, None))) for i, p in enumerate(dk.phien_ban)])
        cur.executemany(f"INSERT INTO quan_he ({', '.join(QH_COLS)}) VALUES ({', '.join(['%s'] * len(QH_COLS))})",
                        [[getattr(q, k) for k in QH_COLS] for q in c.quan_he])
        for dm in c.dinh_muc:
            cur.execute("INSERT INTO dinh_muc (ma_hieu, ten_cong_tac, don_vi, can_cu_so_hieu, can_cu_phu_luc) "
                        "VALUES (%s, %s, %s, %s, %s)", (dm.ma_hieu, dm.ten_cong_tac, dm.don_vi, dm.can_cu_so_hieu,
                                                        dm.can_cu_phu_luc))
            cur.executemany("INSERT INTO hao_phi (ma_hieu, loai, ten, don_vi, gia_tri) VALUES (%s, %s, %s, %s, %s)",
                            [(dm.ma_hieu, h.loai, h.ten, h.don_vi, h.gia_tri) for h in dm.hao_phi])
