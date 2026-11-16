// Kiểu dữ liệu theo OpenAPI của Legal Knowledge API (module_1/app/models.py).

export type TinhTrang = "chua_co_hieu_luc" | "con_hieu_luc" | "het_hieu_luc_mot_phan" | "het_hieu_luc";
export type LoaiQuanHe = "thay_the" | "sua_doi" | "bo_sung" | "huong_dan" | "can_cu" | "bai_bo";

export interface VanBan {
  so_hieu: string;
  loai: string;
  co_quan_ban_hanh: string;
  ngay_ban_hanh: string | null;
  ngay_hieu_luc: string | null; // null = chỉ được viện dẫn, chưa nạp vào kho
  tinh_trang: TinhTrang | null;
  minh_hoa: boolean;
}

export interface QuanHe {
  id: string;
  nguon: string;
  dich: string;
  loai: LoaiQuanHe;
  ngay_hieu_luc: string | null;
  trang_thai_duyet: "de_xuat" | "da_duyet" | "tu_choi";
  nguon_dieu: string | null;
  dich_dieu: string | null;
  dich_khoan: string | null;
  noi_dung_moi: string | null;
  trich_dan: string;
}

export interface GraphOut {
  root: string;
  nodes: VanBan[];
  edges: QuanHe[];
}

export const LOAI_LABEL: Record<LoaiQuanHe, string> = {
  can_cu: "căn cứ",
  huong_dan: "hướng dẫn",
  thay_the: "thay thế",
  sua_doi: "sửa đổi",
  bo_sung: "bổ sung",
  bai_bo: "bãi bỏ",
};

export const TINH_TRANG: Record<TinhTrang | "khong_ro", { label: string; color: string }> = {
  con_hieu_luc: { label: "Còn hiệu lực", color: "#16a34a" },
  het_hieu_luc_mot_phan: { label: "Hết hiệu lực một phần", color: "#d97706" },
  het_hieu_luc: { label: "Hết hiệu lực", color: "#dc2626" },
  chua_co_hieu_luc: { label: "Chưa có hiệu lực", color: "#2563eb" },
  khong_ro: { label: "Chưa có dữ liệu (chỉ được viện dẫn)", color: "#9ca3af" },
};

export async function api<T>(path: string, init?: RequestInit, base = "/api"): Promise<T> {
  const res = await fetch(`${base}${path}`, init);
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail?.message ?? `Lỗi ${res.status}`);
  return body as T;
}

/** "Điều 74", "khoản 7 Điều 76" */
export function dieuKhoan(q: Pick<QuanHe, "dich_dieu" | "dich_khoan">): string {
  if (!q.dich_dieu) return "";
  return q.dich_khoan ? `khoản ${q.dich_khoan} Điều ${q.dich_dieu}` : `Điều ${q.dich_dieu}`;
}
