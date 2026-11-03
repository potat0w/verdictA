"""In-memory parsers for uploaded legal documents. Nothing is written to disk."""

import os
from io import BytesIO

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class DocumentParseError(Exception):
    """Base error for document parsing. Messages must not include document text."""


class UnsupportedFileType(DocumentParseError):
    pass


class FileTooLarge(DocumentParseError):
    pass


class EmptyDocument(DocumentParseError):
    pass


def parse_document(filename: str, data: bytes) -> str:
    """Return extracted text for a PDF, DOCX, or TXT payload."""
    if len(data) > MAX_DOCUMENT_BYTES:
        raise FileTooLarge("File exceeds the 5 MB limit.")

    extension = os.path.splitext(filename or "")[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileType(
            "Unsupported file type. Upload a PDF, DOCX, or TXT file."
        )

    if extension == ".pdf":
        text = _parse_pdf(data)
    elif extension == ".docx":
        text = _parse_docx(data)
    else:
        text = _parse_txt(data)

    cleaned = text.strip()
    if not cleaned:
        if extension == ".pdf":
            raise EmptyDocument("Scanned PDFs are not supported yet.")
        raise EmptyDocument("The document has no extractable text.")
    return cleaned


def _parse_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise RuntimeError("PDF parsing dependency is not installed.") from exc

    try:
        reader = PdfReader(BytesIO(data))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception as exc:
                raise EmptyDocument(
                    "Scanned PDFs are not supported yet."
                ) from exc
        parts: list[str] = []
        for page in reader.pages:
            extracted = page.extract_text() or ""
            parts.append(extracted)
    except EmptyDocument:
        raise
    except PdfReadError as exc:
        raise EmptyDocument("Scanned PDFs are not supported yet.") from exc
    except Exception as exc:
        raise EmptyDocument("Scanned PDFs are not supported yet.") from exc

    return "\n".join(parts)


def _parse_docx(data: bytes) -> str:
    try:
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError
    except ImportError as exc:
        raise RuntimeError("DOCX parsing dependency is not installed.") from exc

    try:
        document = Document(BytesIO(data))
    except PackageNotFoundError as exc:
        raise EmptyDocument("The document has no extractable text.") from exc
    except Exception as exc:
        raise EmptyDocument("The document has no extractable text.") from exc

    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" ".join(cells))
    return "\n".join(parts)


def _parse_txt(data: bytes) -> str:
    payload = data[3:] if data.startswith(b"\xef\xbb\xbf") else data
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("latin-1")
