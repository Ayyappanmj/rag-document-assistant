"""PDF text extraction with PyMuPDF and OCR support for scanned documents. Preserves page numbers and detects headings."""
import io
import logging
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from app.config import get_settings

logger = logging.getLogger(__name__)

HEADING_SIZE_RATIO = 1.15  # a line this much larger than body text counts as a heading
MAX_HEADING_LEN = 100


class PDFExtractionError(Exception):
    """Raised with a user-safe message when a PDF cannot be processed."""


@dataclass
class PageText:
    page_number: int  # 1-based
    text: str
    section: str | None = None


@dataclass
class ExtractionResult:
    page_count: int
    pages: list[PageText] = field(default_factory=list)


class DocumentProcessor:
    """Turns a PDF file into cleaned, page-tagged text, with OCR fallback for scanned pages."""

    def __init__(
        self,
        ocr_enabled: bool | None = None,
        ocr_language: str | None = None,
        min_char_count: int | None = None,
        ocr_fn: Callable[[fitz.Page], str] | None = None,
    ):
        settings = get_settings()
        self.ocr_enabled = ocr_enabled if ocr_enabled is not None else settings.ocr_enabled
        self.ocr_language = ocr_language if ocr_language is not None else settings.ocr_language
        self.min_char_count = min_char_count if min_char_count is not None else settings.ocr_min_char_count
        self.tesseract_cmd = settings.ocr_tesseract_cmd
        self._ocr_fn = ocr_fn

    def extract(self, path: str | Path) -> ExtractionResult:
        try:
            doc = fitz.open(str(path))
        except Exception as exc:
            raise PDFExtractionError("The PDF could not be opened (it may be corrupted).") from exc

        ocr_pages_count = 0
        with doc:
            if doc.needs_pass:
                raise PDFExtractionError("The PDF is password-protected.")
            result = ExtractionResult(page_count=doc.page_count)
            current_section: str | None = None
            for index, page in enumerate(doc, start=1):
                text = self.clean_text(page.get_text("text", sort=True))
                headings = self._detect_headings(page)
                if headings:
                    current_section = headings[0]

                # If text is missing or extremely short, attempt OCR on scanned pages with images
                has_images = bool(page.get_images())
                if len(text.strip()) < self.min_char_count and self.ocr_enabled and (has_images or self._ocr_fn is not None):
                    ocr_text = self._ocr_page(page)
                    if len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        ocr_pages_count += 1

                if text:
                    result.pages.append(PageText(index, text, current_section))

        if not result.pages:
            raise PDFExtractionError(
                "No extractable text found. The document appears to be a scanned PDF, and OCR (Tesseract) is not configured."
            )
        logger.info(
            "pdf_extracted pages=%d pages_with_text=%d ocr_used_pages=%d",
            result.page_count,
            len(result.pages),
            ocr_pages_count,
        )
        return result

    def _ocr_page(self, page: fitz.Page) -> str:
        """Attempt to extract text from a scanned page using custom OCR, PyMuPDF OCR, or pytesseract."""
        if self._ocr_fn:
            try:
                raw = self._ocr_fn(page)
                return self.clean_text(raw)
            except Exception as exc:
                logger.warning("custom_ocr_failed page=%d err=%s", page.number + 1, exc)

        # 1. Try PyMuPDF built-in OCR
        try:
            textpage = page.get_textpage_ocr(language=self.ocr_language, dpi=150, full=True)
            ocr_text = self.clean_text(textpage.extractText())
            if ocr_text:
                return ocr_text
        except Exception as exc:
            logger.debug("pymupdf_ocr_unavailable page=%d err=%s", page.number + 1, exc)

        # 2. Try pytesseract with Pillow
        try:
            import pytesseract
            from PIL import Image

            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_text = self.clean_text(pytesseract.image_to_string(img, lang=self.ocr_language))
            if ocr_text:
                return ocr_text
        except Exception as exc:
            logger.debug("pytesseract_ocr_failed page=%d err=%s", page.number + 1, exc)

        return ""

    @staticmethod
    def clean_text(text: str) -> str:
        text = text.replace("\r", "\n").replace("\x00", "")
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)      # re-join words hyphenated across lines
        text = re.sub(r"[ \t\f\v]+", " ", text)            # collapse spaces/tabs
        text = "\n".join(line.strip() for line in text.split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text)             # collapse blank lines
        return text.strip()

    @staticmethod
    def _detect_headings(page: fitz.Page) -> list[str]:
        """Heuristic: short lines set in a clearly larger font than the page's body text."""
        sizes: Counter = Counter()
        lines: list[tuple[str, float]] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:  # skip images
                continue
            for line in block.get("lines", []):
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = " ".join(s["text"].strip() for s in spans)
                size = max(s["size"] for s in spans)
                sizes[round(size, 1)] += len(text)
                lines.append((text, size))
        if not sizes:
            return []
        body_size = sizes.most_common(1)[0][0]
        return [t for t, s in lines if s >= body_size * HEADING_SIZE_RATIO and 3 <= len(t) <= MAX_HEADING_LEN]
