-- Legal Knowledge Base (Module 1). Chạy lại nhiều lần được (IF NOT EXISTS).
CREATE TABLE IF NOT EXISTS van_ban (
    so_hieu           text PRIMARY KEY,
    loai              text NOT NULL DEFAULT '',
    co_quan_ban_hanh  text NOT NULL DEFAULT '',
    ngay_ban_hanh     date,
    ngay_hieu_luc     date,
    tinh_trang        text CHECK (tinh_trang IN ('chua_co_hieu_luc', 'con_hieu_luc', 'het_hieu_luc_mot_phan', 'het_hieu_luc')),
    minh_hoa          boolean NOT NULL DEFAULT true  -- true = chưa xác minh nguồn chính thống
);

CREATE TABLE IF NOT EXISTS dieu_khoan (
    id       serial PRIMARY KEY,
    van_ban  text NOT NULL REFERENCES van_ban (so_hieu) ON DELETE CASCADE,
    dieu     text NOT NULL,
    khoan    text NOT NULL,
    tieu_de  text NOT NULL DEFAULT '',
    UNIQUE (van_ban, dieu, khoan)
);

-- Phiên bản điều khoản theo thời gian: hiệu lực trong [hieu_luc_tu, hieu_luc_den), den NULL = còn hiệu lực.
CREATE TABLE IF NOT EXISTS phien_ban (
    id             serial PRIMARY KEY,
    dieu_khoan_id  integer NOT NULL REFERENCES dieu_khoan (id) ON DELETE CASCADE,
    thu_tu         integer NOT NULL,
    noi_dung       text NOT NULL,
    hieu_luc_tu    date NOT NULL,
    hieu_luc_den   date CHECK (hieu_luc_den IS NULL OR hieu_luc_den > hieu_luc_tu),
    sua_doi_so_hieu text,  -- văn bản/điều/khoản đã sửa đổi tạo ra phiên bản này
    sua_doi_dieu    text,
    sua_doi_khoan   text,
    UNIQUE (dieu_khoan_id, thu_tu)
);

-- Cạnh của Knowledge Graph. `dich` không có FK: văn bản đích có thể chỉ được viện dẫn, chưa nạp vào kho.
CREATE TABLE IF NOT EXISTS quan_he (
    id                text PRIMARY KEY,
    nguon             text NOT NULL REFERENCES van_ban (so_hieu) ON DELETE CASCADE,
    dich              text NOT NULL,
    loai              text NOT NULL CHECK (loai IN ('thay_the', 'sua_doi', 'bo_sung', 'huong_dan', 'can_cu', 'bai_bo')),
    ngay_hieu_luc     date,
    trang_thai_duyet  text NOT NULL CHECK (trang_thai_duyet IN ('de_xuat', 'da_duyet', 'tu_choi')),
    nguon_dieu        text,
    dich_dieu         text,
    dich_khoan        text,
    noi_dung_moi      text,
    trich_dan         text NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS quan_he_dich ON quan_he (dich);

CREATE TABLE IF NOT EXISTS dinh_muc (
    ma_hieu         text PRIMARY KEY,
    ten_cong_tac    text NOT NULL,
    don_vi          text NOT NULL,
    can_cu_so_hieu  text NOT NULL,
    can_cu_phu_luc  text NOT NULL
);

CREATE TABLE IF NOT EXISTS hao_phi (
    id        serial PRIMARY KEY,
    ma_hieu   text NOT NULL REFERENCES dinh_muc (ma_hieu) ON DELETE CASCADE,
    loai      text NOT NULL CHECK (loai IN ('vat_lieu', 'nhan_cong', 'may')),
    ten       text NOT NULL,
    don_vi    text NOT NULL,
    gia_tri   double precision NOT NULL
);
