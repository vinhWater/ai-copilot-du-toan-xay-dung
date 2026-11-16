"""Đọc đoạn văn bản từ .docx bằng stdlib (không cần python-docx). File .doc cũ: mở Word → Save As .docx."""
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import BinaryIO

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def paragraphs(src: Path | BinaryIO) -> list[str]:
    root = ET.fromstring(zipfile.ZipFile(src).read("word/document.xml"))
    out = []
    for p in root.iter(W + "p"):
        text = "".join(t.text or "" for t in p.iter(W + "t"))
        text = " ".join(unicodedata.normalize("NFC", text).split())
        text = re.sub(r"(\d) /(\d{4}/)", r"\1/\2", text)  # "Số: 91 /2026/…" (văn bản thật hay gõ vậy)
        if text:
            out.append(text)
    return out
