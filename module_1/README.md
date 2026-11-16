# Legal Knowledge API + Graph View (Module 1)

> ⚠️ `app/data/sample.json` là **DỮ LIỆU MINH HỌA** (giả). Bản ghi `minh_hoa: true` = minh họa hoặc chưa xác minh nguồn chính thống.

## Chạy

```bash
docker compose up --build        # từ thư mục gốc repo
```

- Swagger UI: http://localhost:8000/docs
- OpenAPI spec (giao Module 2): http://localhost:8000/openapi.json
- Lược đồ văn bản: http://localhost:3000/?so_hieu=… · nhúng: http://localhost:3000/embed/graph?so_hieu=…
- Trạng thái (quan hệ đã duyệt) lưu ở volume `legal-state`; `WEBHOOK_URLS=url1,url2` để nhận `document.updated`

## Test

```bash
docker compose run --rm legal-api pytest -q
```

## Endpoint

| Method | Path | Ghi chú |
|---|---|---|
| POST | `/search` | `{query, as_of_date?, top_k?}` — keyword, chỉ phiên bản có hiệu lực tại ngày |
| GET | `/documents/{so_hieu}?as_of_date=` | `so_hieu` có `/` dùng thẳng; `tinh_trang` tính tại ngày |
| GET | `/articles/{so_hieu}/{dieu}/{khoan}?as_of_date=` | 404 nếu không tồn tại hoặc không có hiệu lực tại ngày |
| POST | `/citations/verify` | `status`: `valid` / `amended` / `not_in_force` / `not_found` |
| GET | `/graph/{so_hieu}?depth=1..3&as_of_date=` | Chỉ quan hệ đã duyệt; có node văn bản chỉ được viện dẫn (trường `null`) |
| GET | `/relations?trang_thai=&so_hieu=` | Quan hệ (AI đề xuất / đã duyệt / từ chối) |
| POST | `/relations/{id}/approve` · `/reject` | Duyệt → vào graph + áp phiên bản điều khoản + webhook; 409 nếu đã xử lý |
| GET | `/impact/{so_hieu}` | Điều khoản / văn bản / định mức bị văn bản này ảnh hưởng |
| GET | `/norms?ma_hieu=&keyword=` | `ma_hieu` khớp tiền tố |

## Lỗi

404/409 trả `{"detail": {"code": "...", "message": "..."}}`, `code` ∈ `document_not_found` | `article_not_found` | `not_in_force` | `relation_not_found` | `relation_not_pending` — Module 2 rẽ nhánh theo `code`, không theo `message`. 422 là lỗi validate chuẩn FastAPI (`detail` là list).

`as_of_date` bỏ trống = hôm nay theo giờ Việt Nam (Asia/Ho_Chi_Minh).

Chưa có: Postgres, vector search, OCR/PDF.
