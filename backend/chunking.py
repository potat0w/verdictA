"""Clause-sized chunking for the statute index. No model calls."""

from __future__ import annotations

import re
import unicodedata

MAX_CHUNK_CHARS = 1200

_CLAUSE_BOUNDARY = re.compile(r"(?=(?:\(\d{1,2}\)|\([০-৯]{1,2}\)))")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[।.!?])\s+")
_SECTION_NUMBER = re.compile(
    r"^(?:[0-9০-৯]+\[)?([0-9০-৯]+)\s*[\.।]"
)


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").strip()


def detect_language(text: str) -> str | None:
    """Return bn when Bangla letters dominate, otherwise en. Empty text is None."""
    sample = normalize_text(text)[:2000]
    letters = [char for char in sample if char.isalpha()]
    if not letters:
        return None
    bangla = sum(1 for char in letters if "\u0980" <= char <= "\u09ff")
    if bangla / len(letters) >= 0.3:
        return "bn"
    return "en"


def section_number_from_text(text: str) -> str | None:
    match = _SECTION_NUMBER.match(normalize_text(text))
    if not match:
        return None
    return match.group(1).translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))


def compose_section_text(section_title: str | None, section_content: str) -> str:
    content = normalize_text(section_content)
    title = normalize_text(section_title or "")
    if not title:
        return content
    if content.startswith(title):
        return content
    return f"{title}\n{content}"


def split_passage(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Keep short passages whole. Split longer ones on clause markers, then sentences."""
    cleaned = normalize_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    marked = [part.strip() for part in _CLAUSE_BOUNDARY.split(cleaned) if part.strip()]
    if len(marked) <= 1:
        return _hard_wrap(cleaned, max_chars)

    grouped: list[str] = []
    buffer = ""
    for part in marked:
        if not buffer:
            buffer = part
            continue
        combined = f"{buffer}\n{part}"
        if len(combined) <= max_chars:
            buffer = combined
        else:
            grouped.append(buffer)
            buffer = part
    if buffer:
        grouped.append(buffer)

    pieces: list[str] = []
    for part in grouped:
        if len(part) <= max_chars:
            pieces.append(part)
        else:
            pieces.extend(_hard_wrap(part, max_chars))
    return pieces


def _hard_wrap(text: str, max_chars: int) -> list[str]:
    sentences = [part.strip() for part in _SENTENCE_BOUNDARY.split(text) if part.strip()]
    if len(sentences) <= 1:
        return [text[offset : offset + max_chars].strip() for offset in range(0, len(text), max_chars)]

    pieces: list[str] = []
    buffer = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if buffer:
                pieces.append(buffer)
                buffer = ""
            pieces.extend(
                sentence[offset : offset + max_chars].strip()
                for offset in range(0, len(sentence), max_chars)
            )
            continue
        combined = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(combined) <= max_chars:
            buffer = combined
        else:
            if buffer:
                pieces.append(buffer)
            buffer = sentence
    if buffer:
        pieces.append(buffer)
    return [piece for piece in pieces if piece]
