import re
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

class DocumentParser:
    """Extracts, cleans, and chunks multi-format documents (PDF, DOCX, TXT, CSV, MD)."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".md"}

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Removes null bytes, normalizes whitespace and line breaks."""
        if not text:
            return ""
        text = text.replace("\x00", " ")
        # Normalize multiple spaces and tabs
        text = re.sub(r"[ \t]+", " ", text)
        # Strip trailing/leading spaces surrounding line breaks
        text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def extract_text(cls, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extracts content from a file.
        Returns a list of section dictionaries:
        [{"page_number": int or None, "text": str}]
        """
        ext = file_path.suffix.lower()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if ext == ".pdf":
            return cls._extract_pdf(file_path)
        elif ext == ".docx":
            return cls._extract_docx(file_path)
        elif ext == ".csv":
            return cls._extract_csv(file_path)
        elif ext in (".txt", ".md"):
            return cls._extract_plain(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @classmethod
    def _extract_pdf(cls, file_path: Path) -> List[Dict[str, Any]]:
        if pypdf is None:
            raise ImportError("pypdf is required to extract PDF files.")
        sections = []
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                cleaned = cls.clean_text(page_text)
                if cleaned:
                    sections.append({"page_number": idx + 1, "text": cleaned})
        if not sections:
            # Fallback for empty or scanned PDF
            sections.append({"page_number": 1, "text": "[No extractable text found in PDF]"})
        return sections

    @classmethod
    def _extract_docx(cls, file_path: Path) -> List[Dict[str, Any]]:
        if docx is None:
            raise ImportError("python-docx is required to extract DOCX files.")
        doc = docx.Document(file_path)
        paragraphs = []
        for p in doc.paragraphs:
            if p.text.strip():
                paragraphs.append(p.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        full_text = "\n\n".join(paragraphs)
        return [{"page_number": 1, "text": cls.clean_text(full_text)}]

    @classmethod
    def _extract_csv(cls, file_path: Path) -> List[Dict[str, Any]]:
        rows = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = None
            for row in reader:
                if not row or not any(cell.strip() for cell in row):
                    continue
                if header is None:
                    header = [h.strip() for h in row]
                    continue
                row_repr = ", ".join(f"{h}: {val.strip()}" for h, val in zip(header, row) if val.strip())
                if row_repr:
                    rows.append(row_repr)
        return [{"page_number": 1, "text": cls.clean_text("\n".join(rows))}]

    @classmethod
    def _extract_plain(cls, file_path: Path) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return [{"page_number": 1, "text": cls.clean_text(content)}]

    @classmethod
    def chunk_sections(
        cls,
        sections: List[Dict[str, Any]],
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Splits extracted sections into chunks with page numbers and overlap.
        Returns:
        [{"chunk_index": int, "page_number": int or None, "content": str, "token_count": int}]
        """
        chunks = []
        chunk_index = 0

        for section in sections:
            page = section.get("page_number")
            text = section.get("text", "")
            if not text:
                continue

            # If text is smaller than chunk_size, keep whole
            if len(text) <= chunk_size:
                chunks.append({
                    "chunk_index": chunk_index,
                    "page_number": page,
                    "content": text,
                    "token_count": len(text.split()),
                })
                chunk_index += 1
                continue

            # Sliding window chunking
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                # Try breaking at newline or space
                if end < len(text):
                    last_space = text.rfind(" ", start, end)
                    if last_space > start + (chunk_size // 2):
                        end = last_space

                chunk_str = text[start:end].strip()
                if chunk_str:
                    chunks.append({
                        "chunk_index": chunk_index,
                        "page_number": page,
                        "content": chunk_str,
                        "token_count": len(chunk_str.split()),
                    })
                    chunk_index += 1

                if end >= len(text):
                    break
                start = max(end - chunk_overlap, start + 1)

        return chunks
