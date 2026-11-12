# Legal Knowledge API — MOCK (Module 1)

> ⚠️ **DỮ LIỆU MINH HỌA** — số hiệu, nội dung, ngày tháng trong `app/data/sample.json` đều giả, chưa xác minh nguồn chính thống.

## Chạy

```bash
docker compose up --build        # từ thư mục gốc repo
```

- Swagger UI: http://localhost:8000/docs
- OpenAPI spec (giao Module 2): http://localhost:8000/openapi.json

## Test

```bash
docker compose run --rm legal-api pytest -q
```

## Endpoint

| Method | Path | Ghi chú |
|---|---|---|
| POST | `/search` | `{query, as_of_date?, top_k?}` — keyword, chỉ phiên bản có hiệu lực tại ngày |
| GET | `/documents/{so_hieu}` | `so_hieu` có `/` dùng thẳng: `/documents/02/2026/TT-MINHHOA` |
| GET | `/articles/{so_hieu}/{dieu}/{khoan}?as_of_date=` | 404 nếu không tồn tại hoặc không có hiệu lực tại ngày |
| POST | `/citations/verify` | `status`: `valid` / `amended` / `not_in_force` / `not_found` |
| GET | `/graph/{so_hieu}?depth=1..3` | Chỉ quan hệ đã duyệt |
| GET | `/norms?ma_hieu=&keyword=` | `ma_hieu` khớp tiền tố |

## Lỗi

404 trả `{"detail": {"code": "...", "message": "..."}}`, `code` ∈ `document_not_found` | `article_not_found` | `not_in_force` — Module 2 rẽ nhánh theo `code`, không theo `message`. 422 là lỗi validate chuẩn FastAPI (`detail` là list).

`as_of_date` bỏ trống = hôm nay theo giờ Việt Nam (Asia/Ho_Chi_Minh).

Chưa có: webhook `document.updated`, Postgres, vector search.
