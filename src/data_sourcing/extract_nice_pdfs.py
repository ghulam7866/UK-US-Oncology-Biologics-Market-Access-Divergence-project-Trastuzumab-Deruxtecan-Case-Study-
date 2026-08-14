"""
Extracts raw text from NICE TA PDFs saved in data/raw/, cleans out
common boilerplate (page numbers, NICE copyright footers), and saves
plain-text versions to data/processed/ for downstream use:
  - manual reading to locate ICER/QALY figures for the discount model
  - NLP theme extraction on the discussion sections

Also writes data/processed/_extraction_log.txt, a one-glance manifest
of word counts and any warnings (e.g. scanned/image pages) per PDF,
so you can spot which TAs might need manual checking without scrolling
back through the console output.

Requires: pip install pdfplumber

Usage:
    python extract_nice_pdfs.py
"""

import re
from pathlib import Path

import pdfplumber

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "PDFs"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

# Lines matching these patterns get stripped out during cleaning —
# NICE PDFs repeat these on every page, and they're pure noise for NLP.
BOILERPLATE_PATTERNS = [
    r"^Page \d+ of \d+$",
    r"^© NICE \d{4}",
    r"^National Institute for Health and Care Excellence$",
    r"^\d+$",  # standalone page numbers
]


def extract_text_from_pdf(pdf_path: Path, warnings: list) -> str:
    """Extract all text from a PDF, page by page. Appends any warning
    messages (e.g. missing text on a page) to the given warnings list."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
            else:
                msg = (f"no extractable text on page {i + 1} "
                       f"of {pdf_path.name} (may be a scanned image)")
                print(f"  [warning] {msg}")
                warnings.append(msg)
    return "\n\n".join(text_parts)


def clean_text(raw_text: str) -> str:
    """Strip repeated boilerplate lines and collapse excess whitespace."""
    lines = raw_text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(re.match(pattern, stripped) for pattern in BOILERPLATE_PATTERNS):
            continue
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def process_all_pdfs():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(RAW_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {RAW_DIR}. "
              f"Check your files are actually saved there.")
        return

    log_entries = []

    for pdf_path in pdf_files:
        print(f"Processing {pdf_path.name}...")
        warnings = []
        raw_text = extract_text_from_pdf(pdf_path, warnings)
        cleaned = clean_text(raw_text)

        out_path = PROCESSED_DIR / f"{pdf_path.stem}.txt"
        out_path.write_text(cleaned, encoding="utf-8")

        word_count = len(cleaned.split())
        print(f"  -> saved {out_path.name} ({word_count} words)")

        entry_lines = [f"{pdf_path.name}: {word_count} words"]
        if warnings:
            entry_lines.append(f"  {len(warnings)} warning(s):")
            for w in warnings:
                entry_lines.append(f"    - {w}")
        else:
            entry_lines.append("  no warnings")
        log_entries.append("\n".join(entry_lines))

    log_path = PROCESSED_DIR / "_extraction_log.txt"
    log_path.write_text("\n\n".join(log_entries), encoding="utf-8")
    print(f"\nExtraction log saved to {log_path.name} "
          f"({len(pdf_files)} PDFs processed)")


if __name__ == "__main__":
    process_all_pdfs()