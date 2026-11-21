# file_reader.py
# Reads text from uploaded study files (PDF, TXT, DOCX) and handles bad files safely.

import io
from pathlib import Path

ALLOWED_TYPES = ["pdf", "txt", "docx"]
MAX_FILE_MB = 10
MAX_STORED_CHARS = 150_000  # the most text we keep for one file


def read_pdf(data):
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))

    if reader.is_encrypted:
        # Try an empty password; many "locked" PDFs open with it
        if reader.decrypt("") == 0:
            raise ValueError("This PDF is password protected. Please upload an unlocked copy.")

    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")  # skip a page that cannot be read
    return "\n".join(pages)


def read_txt(data):
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError("The text file could not be decoded.")


def read_docx(data):
    from docx import Document

    document = Document(io.BytesIO(data))
    parts = [paragraph.text for paragraph in document.paragraphs]

    # Tables are not part of "paragraphs", so read them too
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def read_uploaded_file(uploaded_file):
    """
    Takes a file from st.file_uploader.
    Returns (text, error). If everything is fine, error is None.
    If something is wrong, text is None and error explains the problem.
    """
    name = uploaded_file.name
    extension = Path(name).suffix.lower().lstrip(".")

    if extension not in ALLOWED_TYPES:
        return None, "Unsupported file type. Please upload a PDF, TXT or DOCX file."

    data = uploaded_file.getvalue()

    if len(data) == 0:
        return None, "This file is empty."

    if len(data) > MAX_FILE_MB * 1024 * 1024:
        return None, f"This file is too large. Please upload a file smaller than {MAX_FILE_MB} MB."

    try:
        if extension == "pdf":
            text = read_pdf(data)
        elif extension == "docx":
            text = read_docx(data)
        else:
            text = read_txt(data)
    except ValueError as error:
        return None, str(error)
    except Exception:
        return None, (
            f"Sorry, I could not read '{name}'. The file may be damaged. "
            "Please try another file."
        )

    # Clean the text: remove empty lines and extra spaces
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    if not text:
        return None, (
            "No readable text was found in this file. "
            "If it is a scanned PDF (a photo of pages), please upload a text version instead."
        )

    return text[:MAX_STORED_CHARS], None