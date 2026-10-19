import fitz
import pytest

from app.rag.document_processor import DocumentProcessor, PDFExtractionError
from tests.conftest import make_pdf

BODY = "Revenue increased by 18 percent in fiscal year 2025. " * 8


def test_blank_page_is_skipped_but_page_numbers_stay_correct(tmp_path):
    pdf = tmp_path / "gap.pdf"
    pdf.write_bytes(make_pdf([("Intro", BODY), ("", ""), ("Results", BODY)]))
    result = DocumentProcessor().extract(pdf)
    assert result.page_count == 3                       # blank page still counts
    assert [p.page_number for p in result.pages] == [1, 3]


def test_section_carries_over_to_pages_without_a_heading(tmp_path):
    pdf = tmp_path / "carry.pdf"
    pdf.write_bytes(make_pdf([("Introduction", BODY), ("", BODY)]))
    result = DocumentProcessor().extract(pdf)
    assert result.pages[1].section == "Introduction"


def test_password_protected_pdf_is_rejected_with_clear_message(tmp_path):
    plain = tmp_path / "plain.pdf"
    plain.write_bytes(make_pdf([("Secret", BODY)]))
    locked = tmp_path / "locked.pdf"
    with fitz.open(str(plain)) as doc:
        doc.save(str(locked), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="user-pass", owner_pw="owner-pass")
    with pytest.raises(PDFExtractionError, match="password"):
        DocumentProcessor().extract(locked)


def test_missing_file_is_a_safe_error(tmp_path):
    with pytest.raises(PDFExtractionError):
        DocumentProcessor().extract(tmp_path / "does-not-exist.pdf")


def test_clean_text_keeps_single_line_breaks_and_numbers():
    cleaned = DocumentProcessor.clean_text("Line one\nLine two 1,842\n\n\n\nNext paragraph")
    assert cleaned == "Line one\nLine two 1,842\n\nNext paragraph"
