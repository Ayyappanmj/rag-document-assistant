import pytest

from app.rag.document_processor import DocumentProcessor, PDFExtractionError
from tests.conftest import make_pdf

BODY = "Revenue increased by 18 percent in fiscal year 2025. " * 8


def test_extract_preserves_page_numbers_and_sections(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(make_pdf([("Introduction", BODY), ("Financial Results", BODY)]))
    result = DocumentProcessor().extract(pdf)
    assert result.page_count == 2
    assert [p.page_number for p in result.pages] == [1, 2]
    assert result.pages[0].section == "Introduction"
    assert result.pages[1].section == "Financial Results"
    assert "Revenue increased" in result.pages[0].text


def test_blank_pdf_raises(tmp_path):
    pdf = tmp_path / "blank.pdf"
    pdf.write_bytes(make_pdf([("", "")]))
    with pytest.raises(PDFExtractionError):
        DocumentProcessor().extract(pdf)


def test_corrupt_pdf_raises(tmp_path):
    pdf = tmp_path / "bad.pdf"
    pdf.write_bytes(b"%PDF-1.4 garbage")
    with pytest.raises(PDFExtractionError):
        DocumentProcessor().extract(pdf)


def test_clean_text():
    raw = "Hello   world\r\n\r\n\r\n\r\nrevenue-\ngrowth\t is  good  "
    cleaned = DocumentProcessor.clean_text(raw)
    assert "revenuegrowth" in cleaned
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_scanned_pdf_ocr_extraction(tmp_path):
    pdf = tmp_path / "scanned.pdf"
    # Create PDF with no digital text on the page
    pdf.write_bytes(make_pdf([("", "")]))

    # Mock OCR extraction function
    def mock_ocr(page):
        return "Scanned document text extracted successfully through OCR."

    processor = DocumentProcessor(ocr_enabled=True, ocr_fn=mock_ocr)
    result = processor.extract(pdf)
    assert result.page_count == 1
    assert len(result.pages) == 1
    assert "Scanned document text" in result.pages[0].text
