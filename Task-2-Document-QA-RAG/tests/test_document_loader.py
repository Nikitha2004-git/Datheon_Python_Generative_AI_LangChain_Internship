import pytest

from app.document_loader import load_file, validate_upload
from app.utils import DocumentLoadError
from tests.conftest import make_pdf

MAX = 1024 * 1024


def test_txt_extraction():
    loaded = load_file("notes.txt", b"Hello world. This is a test.", MAX)
    assert loaded.filename == "notes.txt"
    assert len(loaded.pages) == 1
    assert "Hello world" in loaded.pages[0].page_content
    assert loaded.pages[0].metadata["source"] == "notes.txt"
    assert loaded.pages[0].metadata["page"] is None


def test_txt_utf8_with_bom_and_latin1():
    assert "café" in load_file("a.txt", "café".encode("utf-8-sig"), MAX).pages[0].page_content
    assert "café" in load_file("b.txt", "café".encode("latin-1"), MAX).pages[0].page_content


def test_pdf_extraction_keeps_page_numbers(pdf_bytes):
    loaded = load_file("energy.pdf", pdf_bytes, MAX)
    assert [p.metadata["page"] for p in loaded.pages] == [1, 2]
    assert "Solar panels" in loaded.pages[0].page_content
    assert "Wind turbines" in loaded.pages[1].page_content
    assert all(p.metadata["source"] == "energy.pdf" for p in loaded.pages)


def test_pdf_skips_blank_pages_but_keeps_real_numbering():
    data = make_pdf(["", "Second page has text."])
    loaded = load_file("x.pdf", data, MAX)
    assert [p.metadata["page"] for p in loaded.pages] == [2]


def test_scanned_pdf_without_text_explains_ocr():
    data = make_pdf(["", ""])
    with pytest.raises(DocumentLoadError, match="OCR"):
        load_file("scan.pdf", data, MAX)


def test_corrupted_pdf_is_handled_gracefully():
    with pytest.raises(DocumentLoadError, match="corrupted"):
        load_file("bad.pdf", b"%PDF-1.4 this is not really a pdf", MAX)


def test_empty_file_rejected():
    with pytest.raises(DocumentLoadError, match="empty"):
        load_file("empty.txt", b"", MAX)


def test_whitespace_only_txt_rejected():
    with pytest.raises(DocumentLoadError, match="no readable text"):
        load_file("blank.txt", b"   \n\n  ", MAX)


def test_binary_file_with_txt_extension_rejected():
    with pytest.raises(DocumentLoadError, match="binary"):
        load_file("fake.txt", b"abc\x00def", MAX)


@pytest.mark.parametrize("name", ["report.docx", "image.png", "noextension", "archive.zip"])
def test_unsupported_file_types(name):
    with pytest.raises(DocumentLoadError, match="not supported"):
        validate_upload(name, b"data", MAX)


def test_extension_check_is_case_insensitive():
    assert validate_upload("NOTES.TXT", b"x", MAX) == ".txt"


def test_file_size_limit_enforced():
    with pytest.raises(DocumentLoadError, match="larger than"):
        validate_upload("big.txt", b"x" * 2048, 1024)


def test_same_content_gives_same_hash():
    a = load_file("a.txt", b"same content", MAX)
    b = load_file("b.txt", b"same content", MAX)
    assert a.file_hash == b.file_hash
