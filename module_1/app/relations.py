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
REF = re.compile(r"(?:khoản (\d+[a-z]?) )?[Đđ]iều ((?:\d+[a-z]?(?:, | và ))*\d+[a-z]?)")  # "các điều 2, 3 và 19"
# Câu thay thế / bãi bỏ: có thể nằm ở bất kỳ điều nào, kể cả ngay dòng "Điều 4. Thông tư này thay thế …"
THAY = re.compile(r"này (?:thay thế|bãi bỏ)|được thay thế|hết hiệu lực|^(?:\d+\.\s*)?Bãi bỏ")
CHU_DONG = re.compile(r"này (?:thay thế|bãi bỏ)|Bãi bỏ")  # đối tượng đứng SAU động từ; bị động thì đứng trước
MO_TA = re.compile(r"\bvề\b|hướng dẫn|quy định|thi hành|sửa đổi")  # số hiệu sau các từ này là phần mô tả
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
        refs = [(r[1], d) for r in REF.finditer(p[start:m.start()]) for d in re.split(r", | và ", r[2])]
        out.append((m[0], refs))
        start = m.end()
    return out


def _doi_tuong(p: str) -> list[tuple[str, list[tuple[str | None, str]]]]:
    """Số hiệu là đối tượng của câu thay thế/bãi bỏ; bỏ số hiệu nằm trong phần mô tả văn bản trước.

    VD "Bãi bỏ … Thông tư số 10/2021/TT-BXD … hướng dẫn … thi hành Nghị định số 06/2021/NĐ-CP" → chỉ 10/2021.
    ponytail: heuristic theo từ mô tả + dấu phẩy/chấm phẩy; câu ngoài mẫu → người duyệt bắt, thêm LLM nếu đo thấy tụt.
    """
    m = CHU_DONG.search(p)
    start = m.end() if m else 0
    out, prev, mo_ta = [], None, False
    for sm in re.finditer(SO_HIEU, p[start:]):
        if prev is not None:
            gap = p[start + prev:start + sm.start()]
            if re.search(r"[,;]", gap):
                gap, mo_ta = re.split(r"[,;]", gap)[-1], False
            mo_ta = mo_ta or bool(MO_TA.search(gap))
        if not mo_ta:
            truoc = p[start + (prev or 0):start + sm.start()]
            out.append((sm[0], [(r[1], d) for r in REF.finditer(truoc) for d in re.split(r", | và ", r[2])]))
        prev = sm.end()
    return out


def ngay_hieu_luc(articles: dict[str, tuple[str, list[str]]]) -> date | None:
    """Ngày trong câu "<Văn bản> này có hiệu lực … từ ngày …" — ở bất kỳ điều nào (tiêu đề điều khác nhau)."""
    return next((d for t, b in articles.values() for p in (t, *b) if "này có hiệu lực" in p and (d := _ngay(p))), None)


def extract(so_hieu: str, paras: list[str]) -> list[QuanHe]:
    header, articles = split(paras)
    found: dict[str, QuanHe] = {}

    def add(loai: str, dich: str, trich: str, **kw) -> None:
        if dich == so_hieu:
            return
        q = QuanHe(nguon=so_hieu, dich=dich, loai=loai, trang_thai_duyet="de_xuat", trich_dan=trich, **kw)
        found.setdefault(q.id, q)

    eff = ngay_hieu_luc(articles)

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
                    add("huong_dan", sh, p, nguon_dieu="1", dich_dieu=dieu, dich_khoan=khoan, ngay_hieu_luc=eff)

    # 3. Thay thế / hết hiệu lực / bãi bỏ (thường ở điều cuối, tiêu đề điều không cố định)
    for so_dieu, (t, body) in articles.items():
        for p in (t, *body):
            if not THAY.search(p):
                continue
            for sh, refs in _doi_tuong(p):
                # bãi bỏ → bai_bo; thay thế → thay_the; "hết hiệu lực" một phần (có điều/khoản) → bai_bo
                loai = "bai_bo" if "bãi bỏ" in p.lower() or ("thay thế" not in p and refs) else "thay_the"
                for khoan, dieu in refs or [(None, None)]:
                    add(loai, sh, p, nguon_dieu=so_dieu, dich_dieu=dieu, dich_khoan=khoan, ngay_hieu_luc=eff)

    # 4. Văn bản sửa đổi: "1. Sửa đổi, bổ sung khoản 2 Điều 5 như sau:" + đoạn nội dung mới
    title_sh = re.findall(SO_HIEU, " ".join(h for h in header if not h.startswith("Căn cứ")).upper())
    for so_dieu, (t, body) in articles.items():
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
            add(loai, target, p, nguon_dieu=so_dieu, dich_dieu=m[3], dich_khoan=m[2], ngay_hieu_luc=eff,
                noi_dung_moi="\n".join(moi) or None)

    # 5. Sửa đổi cả văn bản chỉ nêu ở tên văn bản (VD sửa đổi định mức ở phụ lục, không theo điều/khoản)
    for h in header:
        if h.isupper() and "SỬA ĐỔI" in h and (sh := re.findall(SO_HIEU, h)):  # tên văn bản viết hoa
            if not any(q.dich == sh[-1] and q.loai in ("sua_doi", "bo_sung") for q in found.values()):
                add("sua_doi", sh[-1], h, ngay_hieu_luc=eff)
            break
    return list(found.values())


def evaluate(pred: list[QuanHe], gold: list[QuanHe]) -> dict[str, float]:
    key = lambda q: (q.loai, q.dich, q.dich_dieu, q.dich_khoan)  # noqa: E731
    p, g = {key(q) for q in pred}, {key(q) for q in gold}
    tp = len(p & g)
    return {"tp": tp, "precision": tp / len(p) if p else 0.0, "recall": tp / len(g) if g else 0.0}
