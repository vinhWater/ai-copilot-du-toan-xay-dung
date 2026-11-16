"""Relation Extraction Agent: đề xuất quan hệ văn bản / điều khoản từ text đã tách đoạn.

Mọi quan hệ trả ra ở trạng thái `de_xuat` — chỉ ghi vào graph sau khi người duyệt xác nhận.
ponytail: rule-based (regex trên mẫu câu chuẩn của văn bản QPPL); thêm LLM fallback cho câu
không khớp mẫu khi đo recall trên bộ 7 văn bản thấy thiếu.
"""
import re
from datetime import date

from .models import QuanHe

SO_HIEU = r"\d+/\d{4}/[A-ZĐ0-9]+(?:-[A-ZĐ0-9]+)*"
DIEU = re.compile(r"^Điều\s+(\d+[a-z]?)\.\s*(.*)")
CHUONG = re.compile(r"^Chương\s+[IVXLC]+\b")
NGAY = re.compile(r"ngày (\d{1,2}) tháng (\d{1,2}) năm (\d{4})")
REF = re.compile(r"(?:khoản (\d+[a-z]?) )?Điều (\d+[a-z]?)")
AMEND = re.compile(
    r"^\d+\.\s*(Sửa đổi, bổ sung|Sửa đổi|Bổ sung|Bãi bỏ)\s+(?:điểm \S+ )?(?:khoản (\d+[a-z]?) )?Điều (\d+[a-z]?)"
)


def split(paras: list[str]) -> tuple[list[str], dict[str, tuple[str, list[str]]]]:
    """Tách phần đầu (trước Chương I / Điều 1) và các Điều: {so_dieu: (tieu_de, cac_doan)}."""
    header: list[str] = []
    articles: dict[str, tuple[str, list[str]]] = {}
    cur: list[str] | None = None
    for p in paras:
        if m := DIEU.match(p):
            cur = []
            articles.setdefault(m[1], (m[2], cur))
        elif cur is not None:
            if not CHUONG.match(p):
                cur.append(p)
        elif CHUONG.match(p):
            cur = []  # đã qua phần đầu; đoạn tên chương trước Điều đầu tiên bỏ qua
        else:
            header.append(p)
    return header, articles


def _ngay(s: str) -> date | None:
    m = NGAY.search(s)
    return date(int(m[3]), int(m[2]), int(m[1])) if m else None


def _refs_truoc(p: str) -> list[tuple[str, list[tuple[str | None, str]]]]:
    """Mỗi số hiệu trong câu kèm các 'khoản X Điều Y' đứng ngay trước nó (sau số hiệu liền trước)."""
    out, start = [], 0
    for m in re.finditer(SO_HIEU, p):
        refs = [(r[1], r[2]) for r in REF.finditer(p[start:m.start()])]
        out.append((m[0], refs))
        start = m.end()
    return out


def extract(so_hieu: str, paras: list[str]) -> list[QuanHe]:
    header, articles = split(paras)
    found: dict[str, QuanHe] = {}

    def add(loai: str, dich: str, trich: str, **kw) -> None:
        if dich == so_hieu:
            return
        q = QuanHe(nguon=so_hieu, dich=dich, loai=loai, trang_thai_duyet="de_xuat", trich_dan=trich, **kw)
        found.setdefault(q.id, q)

    hieu_luc = next((b for t, b in articles.values() if "hiệu lực" in t.lower()), [])
    eff = next((d for p in hieu_luc if "có hiệu lực" in p and (d := _ngay(p))), None)

    # 1. Căn cứ: chỉ phần đầu văn bản; bỏ "được sửa đổi, bổ sung bởi ..." (quan hệ giữa các văn bản khác)
    for p in header:
        if p.startswith("Căn cứ"):
            for sh in re.findall(SO_HIEU, p.split("được sửa đổi")[0]):
                add("can_cu", sh, p)

    # 2. Hướng dẫn / quy định chi tiết: Điều 1 (phạm vi điều chỉnh)
    for p in articles.get("1", ("", []))[1]:
        if re.search(r"quy định chi tiết|hướng dẫn", p, re.I):
            for sh, refs in _refs_truoc(p):
                for khoan, dieu in refs or [(None, None)]:
                    add("huong_dan", sh, p, dich_dieu=dieu, dich_khoan=khoan, ngay_hieu_luc=eff)

    # 3. Điều hiệu lực: thay thế / hết hiệu lực / bãi bỏ
    for p in hieu_luc:
        low = p.lower()
        if not any(k in low for k in ("hết hiệu lực", "thay thế", "bãi bỏ")):
            continue
        for sh, refs in _refs_truoc(p):
            if refs:
                for khoan, dieu in refs:
                    add("bai_bo", sh, p, dich_dieu=dieu, dich_khoan=khoan, ngay_hieu_luc=eff)
            else:
                add("bai_bo" if "bãi bỏ" in low else "thay_the", sh, p, ngay_hieu_luc=eff)

    # 4. Văn bản sửa đổi: "1. Sửa đổi, bổ sung khoản 2 Điều 5 như sau:" + đoạn nội dung mới
    title_sh = re.findall(SO_HIEU, " ".join(h for h in header if not h.startswith("Căn cứ")).upper())
    for t, body in articles.values():
        target = (re.findall(SO_HIEU, t.upper()) or title_sh or [None])[-1]
        if target is None:
            continue
        for i, p in enumerate(body):
            if not (m := AMEND.match(p)):
                continue
            moi = []
            for q in body[i + 1:]:
                if AMEND.match(q) or re.match(r"^\d+\.\s", q):
                    break
                moi.append(q.strip("“”\""))
            verb = m[1]
            loai = "bai_bo" if verb == "Bãi bỏ" else "bo_sung" if verb == "Bổ sung" else "sua_doi"
            add(loai, target, p, dich_dieu=m[3], dich_khoan=m[2], ngay_hieu_luc=eff,
                noi_dung_moi="\n".join(moi) or None)
    return list(found.values())


def evaluate(pred: list[QuanHe], gold: list[QuanHe]) -> dict[str, float]:
    key = lambda q: (q.loai, q.dich, q.dich_dieu, q.dich_khoan)  # noqa: E731
    p, g = {key(q) for q in pred}, {key(q) for q in gold}
    tp = len(p & g)
    return {"tp": tp, "precision": tp / len(p) if p else 0.0, "recall": tp / len(g) if g else 0.0}
