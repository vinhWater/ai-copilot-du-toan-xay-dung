# Dự án
Khóa luận: AI Copilot Dự toán Xây dựng. Tôi làm MODULE 1 (Legal Knowledge Base & Lược đồ văn bản). Đề bài gốc: README.md.

# Phạm vi Module 1
Parse văn bản pháp luật, đề xuất quan hệ bằng AI, người duyệt xác nhận, lưu phiên bản điều khoản theo thời gian, trả nội dung theo ngày, Legal Knowledge API cho Module 2, Graph View.

# Quy tắc
- Python 3.11+, FastAPI, Pydantic, type hint. Frontend: Next.js + TypeScript.
- KHÔNG bịa nội dung văn bản pháp luật, số điều, ngày hiệu lực. Dữ liệu mẫu phải ghi rõ "minh họa" cho đến khi tôi xác minh nguồn chính thống.
- Chạy local bằng Docker trước (chưa chắc có credit Google Cloud).
- Commit nhỏ, mỗi commit một việc.
- KHÔNG push (chỉ commit local) trừ khi tôi yêu cầu.

# Phân công SV1 / SV2 (nhánh `sv-thinh` = tôi là SV2)
SV2 (tôi): Relation Extraction, Knowledge Graph, Validity Agent, Impact Analysis, Legal Knowledge API, Graph View → được commit.
SV1 (`sv-truc`): Parse Agent, chunking & indexing, Norm Database, pipeline cập nhật (ingest), màn hình duyệt → được code nhưng **KHÔNG commit trên `sv-thinh`**, để untracked cho SV1 tự commit.

File SV1 hiện có (luôn bỏ ra khi `git add`, không dùng `git add .`/`-A`):
- `module_1/app/parse.py`, `module_1/app/ingest.py`, `module_1/app/ocr.py`
- `module_1/tests/test_parse.py`, `module_1/tests/test_ingest.py`, `module_1/tests/test_ocr.py`
- `module_1/frontend/app/review/`
Thêm file SV1 mới → bổ sung vào danh sách này. Code đã commit không được import cứng file SV1 (main.py chỉ nạp `ingest` nếu có).

Báo cáo: sau mỗi chức năng lớn viết md vào `docs/bao-cao-tien-do/` (docs/ bị gitignore, chỉ giữ local). Tài liệu bàn giao SV1: `docs/ban-giao/`.