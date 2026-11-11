# Legal Knowledge API (mock) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mock server Legal Knowledge API (6 endpoint README §4.2) chạy bằng Docker, dữ liệu **minh họa**, để Module 2 phát triển song song.

**Architecture:** FastAPI đọc 1 file JSON lúc khởi động vào model Pydantic `Corpus`. Logic nghiệp vụ là hàm thuần trong `store.py` (nhận `Corpus` làm tham số → test dễ), `main.py` chỉ map route → hàm. Không DB; sau này thay `store.py` bằng Postgres mà không đổi API.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, uvicorn, pytest, httpx (cho TestClient), Docker.

**Spec:** `README.md` §4.2 (endpoint), §5.2 (ERD); quyết định trong phiên chat 2026-11-11.

## Global Constraints

- Python 3.11+, type hint đầy đủ (CLAUDE.md).
- **Không bịa văn bản thật:** mọi văn bản mẫu dùng số hiệu giả có hậu tố `MINHHOA` (vd `02/2026/TT-MINHHOA`), nội dung ghi "Nội dung minh họa … — không phải văn bản thật". Mọi `VanBan` có `minh_hoa: true`.
- Đường dẫn endpoint giữ đúng README §4.2: `POST /search`, `GET /documents/{so_hieu}`, `GET /articles/{so_hieu}/{dieu}/{khoan}?as_of_date=`, `POST /citations/verify`, `GET /graph/{so_hieu}?depth=`, `GET /norms?ma_hieu=&keyword=`.
- `so_hieu` chứa `/` → dùng path converter `{so_hieu:path}`.
- Ngày dạng ISO `YYYY-MM-DD`; `as_of_date` mặc định = hôm nay.
- Hiệu lực: phiên bản có hiệu lực tại ngày D ⇔ `hieu_luc_tu <= D` và (`hieu_luc_den` là null hoặc `D < hieu_luc_den`).
- Graph chỉ trả quan hệ `trang_thai_duyet == "da_duyet"`.
- Commit nhỏ, mỗi task một commit. **Không push.**
- Ngoài phạm vi: webhook `document.updated`, Postgres, vector search, auth.

## Review Focus

1. `so_hieu` có `/` trong URL (`/articles/02/2026/TT-MINHHOA/2/1`) → phải route đúng, không 404. Test ở Task 2.
2. `as_of_date` đúng ngày biên `hieu_luc_tu` / `hieu_luc_den` → biên trái tính, biên phải không tính. Test ở Task 2.
3. `as_of_date` trước khi văn bản có hiệu lực → `/articles` trả 404 với detail khác "không tồn tại"; `/citations/verify` trả `status="not_in_force"`. Test ở Task 2, 4.
4. Quan hệ chưa duyệt (`de_xuat`) không xuất hiện trong graph. Test ở Task 5.
5. Tìm kiếm/keyword không phân biệt hoa thường với tiếng Việt có dấu ("Bê tông" khớp "bê tông"). Test ở Task 3, 6. (Bỏ dấu — chưa làm; `ponytail:` ghi chú trong code.)

---

## File Structure

```
backend/
  requirements.txt
  Dockerfile
  app/
    __init__.py
    models.py        # Pydantic: VanBan, DieuKhoan, PhienBan, QuanHe, DinhMuc, Corpus + I/O models
    store.py         # load() + hàm nghiệp vụ thuần
    main.py          # FastAPI routes
    data/sample.json # dữ liệu MINH HỌA
  tests/
    test_store.py
    test_api.py
docker-compose.yml
.gitignore
```

---

### Task 0: Commit CLAUDE.md + plan

- [ ] `git add CLAUDE.md docs/superpowers/plans/2026-11-11-legal-api-mock.md && git commit -m "docs: CLAUDE.md và plan mock Legal API"`

---

### Task 1: Models + dữ liệu minh họa + load

**Files:**
- Create: `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/models.py`, `backend/app/store.py`, `backend/app/data/sample.json`, `backend/tests/test_store.py`, `.gitignore`

**Interfaces — Produces (models.py):**
- `TinhTrang = Literal["con_hieu_luc","het_hieu_luc_mot_phan","het_hieu_luc"]`
- `VanBan(so_hieu: str, loai: str, co_quan_ban_hanh: str, ngay_ban_hanh: date, ngay_hieu_luc: date, tinh_trang: TinhTrang, minh_hoa: bool = True)`
- `NguonSuaDoi(so_hieu: str, dieu: str, khoan: str | None = None)`
- `PhienBan(noi_dung: str, hieu_luc_tu: date, hieu_luc_den: date | None = None, nguon_sua_doi: NguonSuaDoi | None = None)`
- `DieuKhoan(van_ban: str, dieu: str, khoan: str, tieu_de: str = "", phien_ban: list[PhienBan])`
- `QuanHe(nguon: str, dich: str, loai: Literal["thay_the","sua_doi","bo_sung","huong_dan","can_cu","bai_bo"], ngay_hieu_luc: date | None = None, trang_thai_duyet: Literal["de_xuat","da_duyet","tu_choi"])`
- `HaoPhi(loai: Literal["vat_lieu","nhan_cong","may"], ten: str, don_vi: str, gia_tri: float)`
- `DinhMuc(ma_hieu: str, ten_cong_tac: str, don_vi: str, hao_phi: list[HaoPhi], can_cu_so_hieu: str, can_cu_phu_luc: str)`
- `Corpus(van_ban: list[VanBan], dieu_khoan: list[DieuKhoan], quan_he: list[QuanHe], dinh_muc: list[DinhMuc])`
- store.py: `load(path: Path) -> Corpus`, `DATA_PATH: Path` (= `app/data/sample.json`)

**sample.json phải chứa (tests dựa vào):**
- VanBan: `01/2026/ND-MINHHOA` (nghi_dinh, hiệu lực 2026-02-01), `02/2026/TT-MINHHOA` (thong_tu, hiệu lực 2026-03-01, `het_hieu_luc_mot_phan`), `03/2026/TT-MINHHOA` (thong_tu, hiệu lực 2026-07-01).
- DieuKhoan:
  - `01/2026/ND-MINHHOA` Điều 1 Khoản 1: 1 phiên bản từ 2026-02-01.
  - `02/2026/TT-MINHHOA` Điều 1 Khoản 1: 1 phiên bản từ 2026-03-01, nội dung chứa "bê tông".
  - `02/2026/TT-MINHHOA` Điều 2 Khoản 1: 2 phiên bản — (a) 2026-03-01 → 2026-07-01, nội dung "Nội dung minh họa gốc Điều 2 Khoản 1 — không phải văn bản thật."; (b) từ 2026-07-01, `nguon_sua_doi={so_hieu:"03/2026/TT-MINHHOA", dieu:"1"}`, nội dung "Nội dung minh họa đã sửa đổi Điều 2 Khoản 1 — không phải văn bản thật."
- QuanHe: `02→01 can_cu da_duyet`; `03→02 sua_doi da_duyet` (ngày 2026-07-01); `03→01 can_cu de_xuat`.
- DinhMuc: `MH.0001` "Bê tông móng minh họa" (m3), `MH.0002` "Cốt thép minh họa" (tấn), căn cứ `02/2026/TT-MINHHOA` "Phụ lục I".
- Top-level `"_canh_bao": "DỮ LIỆU MINH HỌA — chưa xác minh nguồn chính thống"` (Corpus bỏ qua field thừa).

- [ ] **Step 1: Test**

```python
def test_load_sample():
    c = load(DATA_PATH)
    assert len(c.van_ban) == 3
    assert all(v.minh_hoa for v in c.van_ban)
    assert all("MINHHOA" in v.so_hieu for v in c.van_ban)
```

- [ ] **Step 2:** `cd backend && python -m pytest -q` → FAIL (import error)
- [ ] **Step 3:** Viết models, `load` (`Corpus.model_validate_json(path.read_text(encoding="utf-8"))`), sample.json, requirements (`fastapi`, `uvicorn[standard]`, `pytest`, `httpx` — pin bản cụ thể đang cài), `.gitignore` (`__pycache__/`, `.venv/`, `.env`, `.pytest_cache/`).
- [ ] **Step 4:** pytest → PASS
- [ ] **Step 5:** `git commit -m "feat(api): models Pydantic và dữ liệu minh họa"`

---

### Task 2: Hiệu lực theo ngày — `/documents`, `/articles`

**Files:** Modify `backend/app/store.py`; Create `backend/app/main.py`, `backend/tests/test_api.py`; Modify `backend/tests/test_store.py`

**Interfaces — Produces:**
- `phien_ban_tai(dk: DieuKhoan, as_of: date) -> PhienBan | None`
- `tim_van_ban(c: Corpus, so_hieu: str) -> VanBan | None`
- `tim_dieu_khoan(c: Corpus, so_hieu: str, dieu: str, khoan: str) -> DieuKhoan | None`
- models: `ArticleOut(so_hieu, dieu, khoan, tieu_de, noi_dung, hieu_luc_tu, hieu_luc_den, nguon_sua_doi, as_of_date: date, minh_hoa: bool)`
- main.py: `app = FastAPI(title="Legal Knowledge API (MOCK — dữ liệu minh họa)")`, `CORPUS = load(DATA_PATH)`
- `GET /documents/{so_hieu:path}` → `VanBan` | 404 `"Không tìm thấy văn bản"`
- `GET /articles/{so_hieu:path}/{dieu}/{khoan}?as_of_date=` → `ArticleOut` | 404 `"Không tìm thấy điều khoản"` | 404 `"Điều khoản không có hiệu lực tại ngày <as_of>"`

- [ ] **Step 1: Tests**

```python
# test_store.py
DK = tim_dieu_khoan(C, "02/2026/TT-MINHHOA", "2", "1")
def test_bien_trai_tinh():   assert phien_ban_tai(DK, date(2026,3,1)).nguon_sua_doi is None
def test_bien_phai_khong():  assert phien_ban_tai(DK, date(2026,7,1)).nguon_sua_doi.so_hieu == "03/2026/TT-MINHHOA"
def test_ngay_truoc_cuoi():  assert phien_ban_tai(DK, date(2026,6,30)).nguon_sua_doi is None
def test_truoc_hieu_luc():   assert phien_ban_tai(DK, date(2026,1,1)) is None

# test_api.py  (client = TestClient(app))
def test_document_slash():   assert client.get("/documents/02/2026/TT-MINHHOA").json()["minh_hoa"] is True
def test_document_404():     assert client.get("/documents/99/2026/X").status_code == 404
def test_article_as_of():
    r = client.get("/articles/02/2026/TT-MINHHOA/2/1", params={"as_of_date": "2026-08-01"})
    assert r.status_code == 200 and "đã sửa đổi" in r.json()["noi_dung"]
def test_article_not_in_force():
    r = client.get("/articles/02/2026/TT-MINHHOA/2/1", params={"as_of_date": "2026-01-01"})
    assert r.status_code == 404 and "không có hiệu lực" in r.json()["detail"]
def test_article_missing():
    assert client.get("/articles/02/2026/TT-MINHHOA/9/9").json()["detail"] == "Không tìm thấy điều khoản"
```

- [ ] **Step 2:** pytest → FAIL
- [ ] **Step 3:** Implement theo interfaces; quy tắc hiệu lực ở Global Constraints.
- [ ] **Step 4:** pytest → PASS
- [ ] **Step 5:** `git commit -m "feat(api): /documents và /articles theo as_of_date"`

---

### Task 3: `POST /search`

**Interfaces — Produces:**
- models: `SearchIn(query: str (min_length=1), as_of_date: date | None = None, top_k: int = Field(5, ge=1, le=50))`, `SearchHit(so_hieu, dieu, khoan, tieu_de, noi_dung, hieu_luc_tu, hieu_luc_den, score: float, minh_hoa: bool)`
- `search(c: Corpus, query: str, as_of: date, top_k: int) -> list[SearchHit]`

Thuật toán: chỉ xét phiên bản có hiệu lực tại `as_of`. `score` = số token (tách theo khoảng trắng, `casefold()`) của query xuất hiện trong `casefold(so_hieu + tieu_de + noi_dung)`; cộng 10 nếu `so_hieu` nằm nguyên trong query. Bỏ hit score 0, sắp giảm dần, cắt `top_k`. Comment `# ponytail: keyword đếm token, thay bằng hybrid pgvector + full-text khi có Postgres`.

- [ ] **Step 1: Tests**

```python
def test_search_casefold():
    hits = search(C, "Bê Tông", date(2026,8,1), 5)
    assert hits and hits[0].so_hieu == "02/2026/TT-MINHHOA" and hits[0].dieu == "1"
def test_search_as_of_loc_phien_ban():
    texts = [h.noi_dung for h in search(C, "Điều 2 Khoản 1", date(2026,8,1), 50)]
    assert not any("gốc" in t for t in texts)
def test_search_api_top_k():
    assert client.post("/search", json={"query": "minh họa", "top_k": 1}).json().__len__() == 1
def test_search_api_empty_query_422():
    assert client.post("/search", json={"query": ""}).status_code == 422
```

- [ ] Step 2 FAIL → Step 3 implement + route → Step 4 PASS
- [ ] **Step 5:** `git commit -m "feat(api): POST /search keyword theo as_of_date"`

---

### Task 4: `POST /citations/verify`

**Interfaces — Produces:**
- models: `CitationIn(so_hieu: str, dieu: str, khoan: str, quote: str = "", as_of_date: date | None = None)`, `AmendRef(so_hieu: str, dieu: str, khoan: str | None, effective_date: date)`, `VerifyOut(citation: CitationIn, exists: bool, quote_match: float, valid_as_of: date, status: Literal["valid","amended","not_in_force","not_found"], amended_by: list[AmendRef], current_text: str | None)` — khớp ví dụ JSON README §4.2.
- `verify(c: Corpus, cit: CitationIn, as_of: date) -> VerifyOut`

Quy tắc:
- Không có điều khoản → `exists=False, status="not_found", quote_match=0, current_text=None`.
- Không có phiên bản tại `as_of` → `status="not_in_force"`, `current_text=None`.
- Có → `current_text` = nội dung phiên bản đó; `amended_by` = các phiên bản có `nguon_sua_doi` và `hieu_luc_tu <= as_of`; `status="amended"` nếu `amended_by` khác rỗng, ngược lại `"valid"`.
- `quote_match`: quote rỗng → 0.0; quote (casefold, gộp khoảng trắng) nằm trong `current_text` → 1.0; ngược lại `difflib.SequenceMatcher(None, q, text).ratio()` làm tròn 2 số.

- [ ] **Step 1: Tests**

```python
def test_verify_amended():
    r = client.post("/citations/verify", json={"so_hieu":"02/2026/TT-MINHHOA","dieu":"2","khoan":"1",
        "quote":"đã sửa đổi Điều 2","as_of_date":"2026-08-01"}).json()
    assert r["status"]=="amended" and r["quote_match"]==1.0 and r["amended_by"][0]["so_hieu"]=="03/2026/TT-MINHHOA"
def test_verify_valid_truoc_sua_doi():
    r = verify(C, CitationIn(so_hieu="02/2026/TT-MINHHOA",dieu="2",khoan="1",quote="gốc"), date(2026,4,1))
    assert r.status=="valid" and r.amended_by==[]
def test_verify_not_found():
    assert verify(C, CitationIn(so_hieu="X",dieu="1",khoan="1"), date(2026,8,1)).status=="not_found"
def test_verify_not_in_force():
    assert verify(C, CitationIn(so_hieu="02/2026/TT-MINHHOA",dieu="2",khoan="1"), date(2026,1,1)).status=="not_in_force"
```

- [ ] Step 2 FAIL → Step 3 implement + route → Step 4 PASS
- [ ] **Step 5:** `git commit -m "feat(api): POST /citations/verify"`

---

### Task 5: `GET /graph/{so_hieu}?depth=`

**Interfaces — Produces:**
- models: `GraphOut(root: str, nodes: list[VanBan], edges: list[QuanHe])`
- `graph(c: Corpus, so_hieu: str, depth: int) -> GraphOut | None` (None nếu không có văn bản)
- Route: `depth: int = Query(1, ge=1, le=3)`; 404 `"Không tìm thấy văn bản"`.

BFS vô hướng từ `so_hieu` qua các `QuanHe` đã duyệt, tối đa `depth` bước; `nodes` gồm root, `edges` không trùng.

- [ ] **Step 1: Tests**

```python
def test_graph_bo_de_xuat():
    g = graph(C, "03/2026/TT-MINHHOA", 1)
    assert {e.dich for e in g.edges} == {"02/2026/TT-MINHHOA"}   # 03→01 de_xuat bị loại
def test_graph_depth2():
    g = graph(C, "03/2026/TT-MINHHOA", 2)
    assert {n.so_hieu for n in g.nodes} == {"01/2026/ND-MINHHOA","02/2026/TT-MINHHOA","03/2026/TT-MINHHOA"}
def test_graph_api_depth_qua_lon(): assert client.get("/graph/02/2026/TT-MINHHOA?depth=9").status_code == 422
```

- [ ] Step 2 FAIL → Step 3 implement + route → Step 4 PASS
- [ ] **Step 5:** `git commit -m "feat(api): GET /graph lược đồ văn bản"`

---

### Task 6: `GET /norms`

**Interfaces — Produces:** `norms(c: Corpus, ma_hieu: str | None, keyword: str | None) -> list[DinhMuc]` — `ma_hieu` khớp tiền tố (casefold), `keyword` là chuỗi con của `ten_cong_tac` (casefold); cả hai None → tất cả.

- [ ] **Step 1: Tests**

```python
def test_norms_ma_hieu(): assert [d.ma_hieu for d in norms(C, "mh.0001", None)] == ["MH.0001"]
def test_norms_keyword(): assert [d.ma_hieu for d in norms(C, None, "BÊ TÔNG")] == ["MH.0001"]
def test_norms_api_all(): assert len(client.get("/norms").json()) == 2
```

- [ ] Step 2 FAIL → Step 3 implement + route → Step 4 PASS
- [ ] **Step 5:** `git commit -m "feat(api): GET /norms tra cứu định mức"`

---

### Task 7: Docker

**Files:** Create `backend/Dockerfile`, `docker-compose.yml`; Modify `README.md`? **Không** (README là đề bài) — thêm mục chạy vào `backend/README.md` ngắn.

- `Dockerfile`: `python:3.11-slim`, `pip install -r requirements.txt`, `CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]`.
- `docker-compose.yml`: service `legal-api`, build `./backend`, port `8000:8000`.
- `backend/README.md`: `docker compose up --build` → `http://localhost:8000/docs`; dòng cảnh báo dữ liệu minh họa; OpenAPI tại `/openapi.json` (giao cho Module 2).

- [ ] **Step 1:** `docker compose up --build -d` rồi `curl -s localhost:8000/documents/02/2026/TT-MINHHOA` → JSON có `"minh_hoa":true`
- [ ] **Step 2:** `curl -s localhost:8000/openapi.json` → có đủ 6 path
- [ ] **Step 3:** `docker compose down`
- [ ] **Step 4:** `git commit -m "chore: Dockerfile và docker-compose cho mock API"`
