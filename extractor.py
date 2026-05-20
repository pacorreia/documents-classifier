"""Text extraction from PDF and DOCX files."""

from pathlib import Path

import pdfplumber
from docx import Document


def extract_text_pdf(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    return "\n".join(text_parts)


def _cell_text_recursive(cell, seen_tcs: set) -> str:
    """Return text from a cell and any nested tables within it.

    Uses the actual lxml _tc element (not id()) for deduplication so that
    garbage-collected proxy objects don't cause false duplicate hits.
    """
    parts = []
    if cell.text.strip():
        parts.append(cell.text)
    for nested_table in cell.tables:
        for row in nested_table.rows:
            for nested_cell in row.cells:
                tc = nested_cell._tc
                if tc not in seen_tcs:
                    seen_tcs.add(tc)
                    text = _cell_text_recursive(nested_cell, seen_tcs)
                    if text:
                        parts.append(text)
    return "\n".join(parts)


def extract_text_docx(path: Path) -> str:
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs]
    # Store the actual lxml _tc element (strong reference) to prevent GC from
    # reusing memory addresses and causing false duplicate hits across cells.
    seen_tcs: set = set()
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                tc = cell._tc
                if tc not in seen_tcs:
                    seen_tcs.add(tc)
                    text = _cell_text_recursive(cell, seen_tcs)
                    if text:
                        parts.append(text)
    return "\n".join(parts)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_pdf(path)
    if suffix == ".docx":
        return extract_text_docx(path)
    if suffix == ".doc":
        raise ValueError(
            f"{path.name}: legacy .doc format is not supported "
            "— please convert to .docx first."
        )
    raise ValueError(f"Unsupported file type: {suffix}")
