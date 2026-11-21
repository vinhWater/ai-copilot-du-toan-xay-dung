"""Test dùng bộ dữ liệu MINH HỌA cố định (đủ tình huống sửa đổi/bãi bỏ), không dùng app/data/sample.json."""
from pathlib import Path

import pytest

import app.main as main
from app.store import load

MINH_HOA = Path(__file__).parent / "fixtures" / "minh_hoa.json"


@pytest.fixture(autouse=True)
def corpus_minh_hoa(monkeypatch):
    monkeypatch.setattr(main, "CORPUS", load(MINH_HOA))
    monkeypatch.setattr(main, "STATE", None)
