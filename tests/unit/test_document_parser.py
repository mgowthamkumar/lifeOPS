import sys
from pathlib import Path
import tempfile

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.services.document_parser import DocumentParser

def test_extract_csv_with_leading_blank_rows():
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        # Leading blank and whitespace-only rows
        f.write("\n")
        f.write("   ,   \n")
        f.write("Role, Skill, Deadline\n")
        f.write("\n")  # Interspersed blank line
        f.write("AI Engineer, Python and RAG, 2026-11-01\n")
        f.write("Data Scientist, SQL and Statistics, 2026-12-01\n")
        temp_csv_path = Path(f.name)

    try:
        sections = DocumentParser.extract_text(temp_csv_path)
        assert len(sections) == 1
        text = sections[0]["text"]
        assert "Role: AI Engineer, Skill: Python and RAG, Deadline: 2026-11-01" in text
        assert "Role: Data Scientist, Skill: SQL and Statistics, Deadline: 2026-12-01" in text
    finally:
        if temp_csv_path.exists():
            temp_csv_path.unlink()

def test_extract_plain_text_and_cleaning():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Line 1\x00\n\n\n\nLine 2   with   spaces\n")
        temp_txt_path = Path(f.name)

    try:
        sections = DocumentParser.extract_text(temp_txt_path)
        assert len(sections) == 1
        text = sections[0]["text"]
        assert "\x00" not in text
        assert "Line 1\n\nLine 2 with spaces" in text
    finally:
        if temp_txt_path.exists():
            temp_txt_path.unlink()
