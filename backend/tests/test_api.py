from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_document_slash():
    assert client.get("/documents/02/2026/TT-MINHHOA").json()["minh_hoa"] is True


def test_document_404():
    assert client.get("/documents/99/2026/X").status_code == 404


def test_article_as_of():
    r = client.get("/articles/02/2026/TT-MINHHOA/2/1", params={"as_of_date": "2026-08-01"})
    assert r.status_code == 200 and "đã sửa đổi" in r.json()["noi_dung"]


def test_article_not_in_force():
    r = client.get("/articles/02/2026/TT-MINHHOA/2/1", params={"as_of_date": "2026-01-01"})
    assert r.status_code == 404 and "không có hiệu lực" in r.json()["detail"]


def test_article_missing():
    assert client.get("/articles/02/2026/TT-MINHHOA/9/9").json()["detail"] == "Không tìm thấy điều khoản"


def test_search_api_top_k():
    assert len(client.post("/search", json={"query": "minh họa", "top_k": 1}).json()) == 1


def test_search_api_empty_query_422():
    assert client.post("/search", json={"query": ""}).status_code == 422
