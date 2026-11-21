# Module 1 bàn giao gì cho Module 2 — Legal Knowledge API

> **Dành cho:** nhóm Module 2 (Copilot Chat & Dự toán) và **AI trợ lý** của nhóm.
> **Cách dùng với AI:** dán nguyên file này vào ChatGPT / Gemini / Claude / Cursor… rồi hỏi. File tự đủ ngữ cảnh — AI không cần đọc code Module 1.
> **Cập nhật:** 16/11/2026 · **Phiên bản API:** v1 (xem mục 9 — thay đổi so với mock v0) · **Liên hệ:** nhóm Module 1 (`sv-thinh`, `sv-truc`)

---

## 0. Tóm tắt 30 giây

- Module 1 là **"bộ não pháp lý"**: số hóa văn bản pháp luật, lưu phiên bản điều khoản theo thời gian, lược đồ quan hệ văn bản, định mức.
- Module 2 **chỉ được truy cập tri thức qua HTTP API** (README mục 4.1 nguyên tắc 6). Không đọc DB, không đọc file JSON của Module 1.
- **Hiện tại:** API chạy bằng Docker: 6 endpoint tra cứu + duyệt quan hệ + impact + webhook + Graph View (cổng 3000). Dữ liệu mặc định vẫn là **MINH HỌA (giả)**.
- **Tuần 8:** chuyển sang dữ liệu thật — **URL và format giữ nguyên**, Module 2 không phải sửa code.

> ⚠️ **Ví dụ trong tài liệu này dùng dữ liệu GIẢ** (`02/2026/TT-MINHHOA`, chỉ còn trong fixture test). API hiện chứa văn bản thật nạp từ .docx (NĐ 206/2026/NĐ-CP…) nhưng **chưa xác minh** nguồn chính thống. **Không** đưa vào luận văn, **không** hard-code vào prompt/test của Module 2 như kiến thức thật. Mọi bản ghi có `minh_hoa: true`.

---

## 1. Module 1 giao gì, khi nào

| Sản phẩm | Module 2 dùng để | Trạng thái / Tuần dự kiến |
|---|---|---|
| Mock server Legal Knowledge API (6 endpoint) | Code Router, Legal Research Agent, Citation Guard, Norm Mapping | ✅ Có rồi |
| OpenAPI spec (`/openapi.json`) | Sinh client, đưa AI đọc | ✅ Có rồi |
| API chạy dữ liệu thật (7 văn bản đã xác minh) | Chạy thật | Tuần 8 |
| Hybrid search (số hiệu + ngữ nghĩa) cho `POST /search` | Tìm đoạn văn bản tốt hơn | Tuần 7 |
| Bảng định mức thật (ưu tiên chương bê tông / BTCT) | Norm Mapping, dự toán | Tuần 6–7 (một phần) |
| `/citations/verify` trên dữ liệu thật | Citation Guard | Tuần 10 |
| Webhook `document.updated` + `GET /impact/{so_hieu}` | Gắn cờ câu trả lời/dự toán bị ảnh hưởng | ✅ Có rồi (mục 4.8, 5.1) |
| Graph View + trang embed (`/embed/graph`) | Hiển thị "Lược đồ văn bản" trong chat | ✅ Có rồi (mục 5.2) |
| Bộ câu hỏi kiểm thử chung (≥ 100 câu) | Đánh giá chat | Làm chung, từ tuần 4 |

---

## 2. Chạy mock server trên máy Module 2

```bash
git pull origin main
docker compose up --build        # chạy ở thư mục gốc repo
```

- API: `http://localhost:8000`
- Swagger UI (bấm thử từng endpoint): `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Gợi ý: đặt base URL vào biến môi trường của Module 2, ví dụ `LEGAL_API_URL=http://localhost:8000` (trong docker-compose cùng mạng thì `http://legal-api:8000`).

---

## 3. Khái niệm cần nắm (AI hay hiểu sai chỗ này)

### 3.1. Định danh điều khoản = (`so_hieu`, `dieu`, `khoan`)
- `so_hieu`: số hiệu văn bản, **có dấu `/`**, ví dụ `02/2026/TT-MINHHOA`. Đặt thẳng vào URL, **không** encode `/` thành `%2F`: `/documents/02/2026/TT-MINHHOA`.
- `dieu`, `khoan`: là **chuỗi** (`"2"`, `"1"`), không phải số.

### 3.2. `as_of_date` — thời điểm áp dụng
- Định dạng `YYYY-MM-DD`.
- Một khoản có thể có **nhiều phiên bản** theo thời gian (bị sửa đổi). API trả phiên bản thỏa `hieu_luc_tu <= as_of_date < hieu_luc_den`.
  - Đúng ngày văn bản sửa đổi có hiệu lực → đã dùng **bản mới**.
  - `hieu_luc_den = null` → còn hiệu lực đến nay.
- **Bỏ trống `as_of_date` = hôm nay theo giờ Việt Nam.** Nếu người dùng chat có nêu "thời điểm áp dụng", Module 2 **phải** truyền xuống.

### 3.3. Quan hệ văn bản (cạnh trong graph)
Cạnh có hướng `nguon → dich`, đọc là **"nguồn [loại] đích"**:

| `loai` | Đọc là |
|---|---|
| `can_cu` | Văn bản nguồn **căn cứ vào** văn bản đích (Thông tư → Nghị định) |
| `sua_doi` | Nguồn **sửa đổi** đích |
| `bo_sung` | Nguồn **bổ sung** đích |
| `thay_the` | Nguồn **thay thế** đích |
| `huong_dan` | Nguồn **hướng dẫn** đích |
| `bai_bo` | Nguồn **bãi bỏ** (một phần) đích |

API chỉ trả quan hệ **đã được người duyệt** (`trang_thai_duyet = "da_duyet"`).

Quan hệ có thể ở **cấp điều khoản**: `dich_dieu`, `dich_khoan` (VD Nghị định *hướng dẫn* khoản 7 Điều 76 Luật Xây dựng). `null` = cả văn bản. Mỗi quan hệ có `id` ổn định, `trich_dan` (câu gốc làm bằng chứng).

### 3.4. Tình trạng văn bản (`tinh_trang`)
`chua_co_hieu_luc` · `con_hieu_luc` · `het_hieu_luc_mot_phan` · `het_hieu_luc` · **`null`** → dùng để tô màu/ghi chú trong mục "[Tình trạng hiệu lực]" của câu trả lời.

- Tính **theo ngày** `as_of_date` (bỏ trống = hôm nay giờ VN) từ các quan hệ đã duyệt — cùng văn bản, khác ngày có thể khác tình trạng.
- `null` = văn bản **chỉ được viện dẫn**, chưa nạp vào kho → không biết tình trạng; khi đó `loai = ""`, `ngay_ban_hanh`/`ngay_hieu_luc` = `null`. **Không** được hiểu `null` là "còn hiệu lực".

### 3.5. Cờ `minh_hoa`
Có ở văn bản, kết quả tìm kiếm, điều khoản. `true` = dữ liệu giả/chưa xác minh. **Gợi ý cho Module 2:** nếu `minh_hoa = true` thì UI hiển thị nhãn "Dữ liệu minh họa" cạnh trích dẫn.

---

## 4. Hợp đồng API chi tiết

Tất cả request/response là JSON, UTF-8. Ví dụ dưới đây lấy **đúng** từ dữ liệu mock hiện tại.

### 4.1. `POST /search` — tìm đoạn văn bản

Request:
```json
{ "query": "chi phí dự phòng", "as_of_date": "2026-08-01", "top_k": 5 }
```
- `query`: bắt buộc, không rỗng (rỗng → 422).
- `top_k`: 1–50, mặc định 5.

Response `200` — **mảng** (có thể rỗng `[]`), sắp theo `score` giảm dần:
```json
[
  {
    "so_hieu": "02/2026/TT-MINHHOA",
    "dieu": "2",
    "khoan": "1",
    "tieu_de": "Chi phí dự phòng (minh họa)",
    "noi_dung": "Nội dung minh họa đã sửa đổi Điều 2 Khoản 1 — không phải văn bản thật.",
    "hieu_luc_tu": "2026-07-01",
    "hieu_luc_den": null,
    "score": 4.0,
    "minh_hoa": true
  }
]
```
Lưu ý:
- Chỉ trả phiên bản **có hiệu lực tại `as_of_date`**.
- Mock hiện tìm **từ khóa** (không phân biệt hoa/thường, chưa hỗ trợ gõ không dấu). Tuần 7 thành hybrid search — format giữ nguyên, `score` không cố định thang đo → **đừng** dùng ngưỡng `score` cứng trong code.
- Câu hỏi có chứa số hiệu văn bản → đoạn của văn bản đó được ưu tiên.

### 4.2. `GET /documents/{so_hieu}` — thông tin văn bản

`GET /documents/02/2026/TT-MINHHOA?as_of_date=2026-08-01` → `200` (`as_of_date` tùy chọn, chỉ ảnh hưởng `tinh_trang`):
```json
{
  "so_hieu": "02/2026/TT-MINHHOA",
  "loai": "thong_tu",
  "co_quan_ban_hanh": "Cơ quan minh họa",
  "ngay_ban_hanh": "2026-02-01",
  "ngay_hieu_luc": "2026-03-01",
  "tinh_trang": "het_hieu_luc_mot_phan",
  "minh_hoa": true
}
```
Không có → `404` code `document_not_found`.

### 4.3. `GET /articles/{so_hieu}/{dieu}/{khoan}?as_of_date=` — nội dung khoản tại một ngày

`GET /articles/02/2026/TT-MINHHOA/2/1?as_of_date=2026-05-01` → `200` (bản **gốc**):
```json
{
  "so_hieu": "02/2026/TT-MINHHOA",
  "dieu": "2",
  "khoan": "1",
  "tieu_de": "Chi phí dự phòng (minh họa)",
  "noi_dung": "Nội dung minh họa gốc Điều 2 Khoản 1 — không phải văn bản thật.",
  "hieu_luc_tu": "2026-03-01",
  "hieu_luc_den": "2026-07-01",
  "nguon_sua_doi": null,
  "as_of_date": "2026-05-01",
  "minh_hoa": true
}
```
Cùng khoản với `as_of_date=2026-08-01` → bản **đã sửa đổi**, `hieu_luc_tu = 2026-07-01`, `nguon_sua_doi = {"so_hieu": "03/2026/TT-MINHHOA", "dieu": "1", "khoan": null}`.

Lỗi:
- Không có khoản → `404` `article_not_found`.
- Có khoản nhưng chưa/không còn hiệu lực tại ngày đó → `404` `not_in_force`.

### 4.4. `POST /citations/verify` — kiểm chứng trích dẫn (cho Citation Guard)

Request:
```json
{
  "so_hieu": "02/2026/TT-MINHHOA",
  "dieu": "2",
  "khoan": "1",
  "quote": "Nội dung minh họa gốc Điều 2 Khoản 1",
  "as_of_date": "2026-08-01"
}
```
`quote` có thể rỗng; `as_of_date` bỏ trống = hôm nay.

Response `200` (luôn 200, kết luận nằm trong `status`):
```json
{
  "citation": { "...": "echo lại request" },
  "exists": true,
  "quote_match": 0.62,
  "valid_as_of": "2026-08-01",
  "status": "amended",
  "amended_by": [
    { "so_hieu": "03/2026/TT-MINHHOA", "dieu": "1", "khoan": null, "effective_date": "2026-07-01" }
  ],
  "current_text": "Nội dung minh họa đã sửa đổi Điều 2 Khoản 1 — không phải văn bản thật."
}
```
(`quote_match` thấp vì câu trích là bản gốc, còn `current_text` là bản đã sửa.)

| `status` | Nghĩa | Citation Guard nên làm |
|---|---|---|
| `valid` | Tồn tại, có hiệu lực, chưa bị sửa tới ngày đó | Giữ trích dẫn nếu `quote_match` đủ cao |
| `amended` | Tồn tại, có hiệu lực nhưng **đã bị sửa**; `current_text` là bản đang áp dụng | Thay quote bằng `current_text` hoặc ghi chú "đã được sửa đổi bởi …" |
| `not_in_force` | Tồn tại nhưng không có hiệu lực tại ngày | Loại hoặc gắn cờ "hết hiệu lực" |
| `not_found` | Không tồn tại (`exists: false`) | **Loại bỏ** — đây là trích dẫn bịa |

`quote_match` (0–1): `1.0` khi câu trích nằm nguyên văn trong nội dung (đã chuẩn hóa khoảng trắng/hoa thường); còn lại là độ giống chuỗi. Ngưỡng chấp nhận do Module 2 tự chọn và ghi vào báo cáo (gợi ý bắt đầu ~0.9).

### 4.5. `GET /graph/{so_hieu}?depth=1..3&as_of_date=` — lược đồ văn bản

`GET /graph/02/2026/TT-MINHHOA?depth=1` → `200`:
```json
{
  "root": "02/2026/TT-MINHHOA",
  "nodes": [
    { "so_hieu": "01/2026/ND-MINHHOA", "loai": "nghi_dinh", "tinh_trang": "con_hieu_luc", "...": "đủ field như /documents" },
    { "so_hieu": "02/2026/TT-MINHHOA", "...": "..." },
    { "so_hieu": "03/2026/TT-MINHHOA", "...": "..." }
  ],
  "edges": [
    { "nguon": "02/2026/TT-MINHHOA", "dich": "01/2026/ND-MINHHOA", "loai": "can_cu", "ngay_hieu_luc": null, "trang_thai_duyet": "da_duyet" },
    { "nguon": "03/2026/TT-MINHHOA", "dich": "02/2026/TT-MINHHOA", "loai": "sua_doi", "ngay_hieu_luc": "2026-07-01", "trang_thai_duyet": "da_duyet" }
  ]
}
```
- `depth` mặc định 1, ngoài 1–3 → 422. Văn bản không có trong kho và không có quan hệ nào → `404` `document_not_found`.
- `nodes` có thể gồm văn bản **chỉ được viện dẫn** (VD các Luật làm căn cứ): `tinh_trang` có thể `null` hoặc tính từ quan hệ (VD bị thay thế → `het_hieu_luc`).
- `edges` có thêm `id`, `nguon_dieu`, `dich_dieu`, `dich_khoan`, `noi_dung_moi`, `trich_dan`; nhiều cạnh cùng cặp văn bản là bình thường (mỗi điều/khoản một cạnh).
- Từ `edges` suy ra: văn bản **ban hành trước** liên quan = các `dich` khi `nguon == root`; **ban hành sau** = các `nguon` khi `dich == root`.
- Module 1 đã có trang vẽ sẵn (mục 5.2) → Module 2 **không cần tự vẽ graph**.

### 4.6. `GET /norms?ma_hieu=&keyword=` — tra cứu định mức

`GET /norms?keyword=bê tông` → `200`, mảng:
```json
[
  {
    "ma_hieu": "MH.0001",
    "ten_cong_tac": "Bê tông móng minh họa",
    "don_vi": "m3",
    "hao_phi": [
      { "loai": "vat_lieu",  "ten": "Vật liệu minh họa A", "don_vi": "m3",   "gia_tri": 1.0 },
      { "loai": "nhan_cong", "ten": "Nhân công minh họa",  "don_vi": "công", "gia_tri": 1.0 },
      { "loai": "may",       "ten": "Máy minh họa",        "don_vi": "ca",   "gia_tri": 0.1 }
    ],
    "can_cu_so_hieu": "02/2026/TT-MINHHOA",
    "can_cu_phu_luc": "Phụ lục I"
  }
]
```
- `ma_hieu` khớp **tiền tố** (`MH.00` → cả MH.0001, MH.0002). `keyword` khớp chuỗi con trong `ten_cong_tac`. Bỏ cả hai → trả tất cả.
- `hao_phi[].loai` ∈ `vat_lieu | nhan_cong | may`.
- `can_cu_so_hieu` + `can_cu_phu_luc` → dùng cho cột "Căn cứ pháp lý" trong bảng dự toán Excel.
- API **không** có đơn giá (giá tiền). Estimate Calculator của Module 2 cần nguồn đơn giá riêng → báo Module 1 nếu cần thêm endpoint.

### 4.7. Định dạng lỗi

`404` luôn có dạng:
```json
{ "detail": { "code": "not_in_force", "message": "Điều khoản không có hiệu lực tại ngày 2026-01-01" } }
```
- `code` ∈ `document_not_found` | `article_not_found` | `not_in_force` | `relation_not_found` | `relation_not_pending` (409) → **rẽ nhánh theo `code`**, `message` có thể đổi.
- `422` = request sai format (chuẩn FastAPI, `detail` là **mảng**).

### 4.8. `GET /impact/{so_hieu}` — văn bản này ảnh hưởng gì

Chỉ tính quan hệ **đã duyệt** làm đổi nội dung (`sua_doi`, `bo_sung`, `bai_bo`, `thay_the`):
```json
{
  "so_hieu": "03/2026/TT-MINHHOA",
  "van_ban": ["02/2026/TT-MINHHOA"],
  "dieu_khoan": [{ "so_hieu": "02/2026/TT-MINHHOA", "dieu": "2", "khoan": "1", "loai": "sua_doi", "ngay_hieu_luc": "2026-07-01" }],
  "dinh_muc": ["MH.0001", "MH.0002"]
}
```
`dinh_muc` = định mức có căn cứ là văn bản bị ảnh hưởng → **cần rà soát** (có thể thừa, không sót).

### 4.9. Quan hệ & duyệt (dùng nội bộ Module 1, Module 2 chỉ cần đọc)

| Endpoint | Ghi chú |
|---|---|
| `GET /relations?trang_thai=de_xuat\|da_duyet\|tu_choi&so_hieu=` | Danh sách quan hệ |
| `POST /relations/{id}/approve` | Người duyệt Module 1 xác nhận → vào graph, áp vào phiên bản điều khoản, bắn webhook |
| `POST /relations/{id}/reject` | Từ chối |

---

## 5. Webhook & Graph View (đã có)

### 5.1. Webhook `document.updated`
- Đăng ký: biến môi trường của service Module 1 `WEBHOOK_URLS` (nhiều URL cách nhau dấu phẩy), VD `WEBHOOK_URLS=http://module2-api:8001/hooks/legal docker compose up`.
- Gửi `POST` JSON khi người duyệt **xác nhận** một quan hệ làm đổi nội dung:
```json
{
  "event": "document.updated",
  "quan_he": { "id": "…", "nguon": "<văn bản mới>", "dich": "…", "loai": "sua_doi", "dich_dieu": "2", "dich_khoan": "1", "ngay_hieu_luc": "YYYY-MM-DD", "...": "…" },
  "impact":  { "so_hieu": "<văn bản mới>", "van_ban": ["…"], "dieu_khoan": [{ "so_hieu": "…", "dieu": "…", "khoan": "…", "loai": "sua_doi", "ngay_hieu_luc": "…" }], "dinh_muc": ["…"] }
}
```
- **Chưa có** retry, HMAC, `event_id`: Module 2 down lúc đó là mất sự kiện → khi khởi động lại nên gọi `GET /impact/{so_hieu}` để đồng bộ. Chống trùng bằng `quan_he.id`.
- Module 2 dùng `impact.dieu_khoan` để gắn cờ câu trả lời / dự toán đã lưu có trích dẫn bị ảnh hưởng.

### 5.2. Graph View
- Nhúng iframe: `<iframe src="http://localhost:3000/embed/graph?so_hieu=206/2026/NĐ-CP&as_of_date=2026-07-01&depth=1">` (service `graph-view` trong docker compose).
- Màu node: xanh lá còn hiệu lực · cam hết hiệu lực một phần · đỏ hết hiệu lực · xanh dương chưa có hiệu lực · xám viền đứt chỉ được viện dẫn.
- Trang tra cứu đầy đủ: `http://localhost:3000/?so_hieu=…`.

### 5.3. Thay đổi khác
- `/search` thành hybrid (tuần 7): có thể thêm field tùy chọn, **không bỏ** field cũ.
- Thêm `GET /health` (tuần 8) để kiểm tra API sống.
- Mọi thay đổi phá vỡ hợp đồng sẽ được báo trước + tăng version.

---

## 6. Gợi ý cho Module 2 dùng API (ADK tools)

Client Python tối thiểu, dùng làm tool cho ADK agent:

```python
import os
import httpx

BASE = os.getenv("LEGAL_API_URL", "http://localhost:8000")
client = httpx.Client(base_url=BASE, timeout=10)


def search_legal(query: str, as_of_date: str | None = None, top_k: int = 5) -> list[dict]:
    """Tìm đoạn văn bản pháp luật có hiệu lực tại as_of_date (YYYY-MM-DD)."""
    r = client.post("/search", json={"query": query, "as_of_date": as_of_date, "top_k": top_k})
    r.raise_for_status()
    return r.json()


def get_article(so_hieu: str, dieu: str, khoan: str, as_of_date: str | None = None) -> dict:
    """Nội dung điều/khoản tại một ngày. Trả {'error': code} nếu 404."""
    params = {"as_of_date": as_of_date} if as_of_date else {}
    r = client.get(f"/articles/{so_hieu}/{dieu}/{khoan}", params=params)  # không encode dấu /
    if r.status_code == 404:
        return {"error": r.json()["detail"]["code"]}
    r.raise_for_status()
    return r.json()


def verify_citation(so_hieu: str, dieu: str, khoan: str, quote: str = "", as_of_date: str | None = None) -> dict:
    """Kiểm chứng một trích dẫn trước khi đưa vào câu trả lời."""
    r = client.post("/citations/verify", json={
        "so_hieu": so_hieu, "dieu": dieu, "khoan": khoan, "quote": quote, "as_of_date": as_of_date,
    })
    r.raise_for_status()
    return r.json()
```

Hoặc sinh client từ OpenAPI: `npx openapi-typescript http://localhost:8000/openapi.json -o legal-api.d.ts` (frontend TS).

### Nên / không nên
- ✅ Mọi trích dẫn đi qua `POST /citations/verify` trước khi hiển thị.
- ✅ Truyền `as_of_date` khi người dùng có nêu thời điểm áp dụng.
- ✅ Câu trả lời chỉ dựa trên nội dung API trả về; API không trả gì → "không tìm thấy căn cứ".
- ✅ Viết test của Module 2 dựa trên **hành vi** (status, field), không dựa vào nội dung chữ minh họa — vì tuần 8 dữ liệu sẽ đổi.
- ❌ Không để LLM tự "nhớ" số hiệu/điều/khoản/ngày hiệu lực — luôn lấy từ API.
- ❌ Không encode `/` trong `so_hieu` thành `%2F`.
- ❌ Không giả định `score` có thang cố định.

---

## 7. Prompt mẫu để dán cho AI trợ lý của Module 2

```text
Tôi làm Module 2 (Copilot Chat & Dự toán) dùng Google ADK (Python) và Next.js.
Module 1 cung cấp Legal Knowledge API, hợp đồng mô tả trong tài liệu dán bên dưới.
Quy tắc: chỉ truy cập tri thức pháp lý qua API này; không bịa số hiệu, điều, khoản,
ngày hiệu lực; mọi trích dẫn phải qua POST /citations/verify; dữ liệu hiện tại là
minh họa nên không hard-code nội dung chữ.
Nhiệm vụ: <ví dụ: viết Citation Guard agent dùng tool verify_citation, loại trích
dẫn status=not_found, thay current_text khi status=amended>.

<dán toàn bộ file HUONG_DAN_CHO_MODULE_2.md ở đây>
```

---

## 8. Cần gì thêm từ Module 1?

Mở issue trên GitHub (gắn nhãn `module-1`) hoặc nhắn nhóm Module 1, ghi: endpoint, input mẫu, output mong muốn, cần trước tuần nào. Thay đổi trong `shared/` phải thống nhất 2 nhóm trước (CONTRIBUTING.md).

---

## 9. Thay đổi so với mock v0 (16/11/2026)

Tương thích ngược với code đọc field cũ, **trừ** các điểm cần kiểm tra:
- ⚠️ `VanBan.ngay_ban_hanh`, `ngay_hieu_luc`, `tinh_trang` **có thể `null`** (văn bản chỉ được viện dẫn).
- ⚠️ `tinh_trang` có thêm giá trị `chua_co_hieu_luc`, và giờ **tính theo `as_of_date`**.
- Mới: `?as_of_date=` ở `/documents`, `/graph`; `GET /impact`; `GET /relations`, `POST /relations/{id}/approve|reject`; webhook; Graph View.
- `QuanHe` thêm: `id`, `nguon_dieu`, `dich_dieu`, `dich_khoan`, `noi_dung_moi`, `trich_dan`.
- Mã lỗi mới: `relation_not_found` (404), `relation_not_pending` (409).
