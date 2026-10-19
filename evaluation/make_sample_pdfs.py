"""Creates the fictional sample PDFs in evaluation/sample_docs/ (needs PyMuPDF, already in requirements).

Run from the project root:   python evaluation/make_sample_pdfs.py
"""
from pathlib import Path

import fitz  # PyMuPDF

from sample_content import SAMPLE_DOCS

OUT_DIR = Path(__file__).resolve().parent / "sample_docs"


def build_pdf(pages: list[tuple[str, str]]) -> bytes:
    doc = fitz.open()
    for heading, body in pages:
        page = doc.new_page()  # A4
        page.insert_text((72, 80), heading, fontsize=22)
        leftover = page.insert_textbox(fitz.Rect(72, 110, 523, 780), body, fontsize=11)
        if leftover < 0:
            raise RuntimeError(f"Text does not fit on the page: {heading}")
    data = doc.tobytes()
    doc.close()
    return data


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for name, pages in SAMPLE_DOCS.items():
        (OUT_DIR / name).write_bytes(build_pdf(pages))
        print(f"created {OUT_DIR / name} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
