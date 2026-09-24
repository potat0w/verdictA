"""Parse Bangladesh Constitution section headings into article keys."""

import re
from typing import Optional


BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

BN_LETTER_TO_LATIN = {
    "ক": "A",
    "খ": "B",
    "গ": "C",
    "ঘ": "D",
    "ঙ": "E",
    "চ": "F",
    "ছ": "G",
    "জ": "H",
}

# Require a real article delimiter (. or danda). Do not treat "33[***]" as article 33.
EN_ARTICLE_RE = re.compile(r"^(?:\d+\[\s*)?(\d+[A-Z]?)\s*\.\s*")
BN_ARTICLE_RE = re.compile(r"^(?:\d+\[\s*)?([০-৯]+[ক-হ]?)\s*[।\.৷]\s*")

OMITTED_RE = re.compile(
    r"^(?:"
    r"\d+\[\s*\*{3}\s*\]"
    r"|Omitted by\b"
    r"|সংবিধান\s*\(পঞ্চদশ"
    r"|\[\s*সংবিধান\s*\(পঞ্চদশ"
    r")",
    re.IGNORECASE,
)


def normalize_bn_article_token(raw: str) -> str:
    """Convert a Bangla article token like '২ক' into a Latin key like '2A'."""
    text = raw.strip().translate(BN_DIGITS)
    match = re.match(r"^(\d+)([ক-হ]*)$", text)
    if not match:
        return text
    number = match.group(1)
    letters = match.group(2)
    suffix = "".join(BN_LETTER_TO_LATIN.get(ch, ch) for ch in letters)
    return number + suffix


def parse_en_article_key(text: str) -> Optional[str]:
    """Return Latin article_key from English section text, or None."""
    match = EN_ARTICLE_RE.match(text.strip())
    if not match:
        return None
    return match.group(1)


def parse_bn_article_key(text: str) -> Optional[tuple]:
    """Return (article_key, display_number) from Bangla section text, or None."""
    match = BN_ARTICLE_RE.match(text.strip())
    if not match:
        return None
    raw = match.group(1)
    return normalize_bn_article_token(raw), raw


def is_omitted_placeholder(text: str) -> bool:
    """True when the section is a repealed/omitted placeholder, not an article body."""
    stripped = text.strip()
    if not stripped:
        return False
    if OMITTED_RE.match(stripped):
        return True
    if re.match(r"^\d+\[\*{3}\]$", stripped):
        return True
    # Short Bangla omission notes that say the chapter/article was repealed.
    if "বিলুপ্ত" in stripped and len(stripped) < 200:
        return True
    return False


def classify_constitution_section(text: str, language: str) -> dict:
    """
    Classify one constitution section.

    Returns:
      {
        "kind": "article" | "omitted_placeholder" | "unparsed" | "empty",
        "article_key": str | None,      # canonical Latin key, e.g. "4A"
        "display_number": str | None,   # as shown in source, e.g. "৪ক" or "4A"
      }
    """
    stripped = (text or "").strip()
    if not stripped:
        return {
            "kind": "empty",
            "article_key": None,
            "display_number": None,
        }

    # Parse article heading first so repealed stubs like "৯২ক। [...বিলুপ্ত]"
    # still get an article_key and pair EN/BN.
    if language == "en":
        key = parse_en_article_key(stripped)
        if key:
            return {
                "kind": "article",
                "article_key": key,
                "display_number": key,
            }
    elif language == "bn":
        parsed = parse_bn_article_key(stripped)
        if parsed:
            key, raw = parsed
            return {
                "kind": "article",
                "article_key": key,
                "display_number": raw,
            }
    else:
        raise ValueError(f"Unsupported language: {language}")

    if is_omitted_placeholder(stripped):
        return {
            "kind": "omitted_placeholder",
            "article_key": None,
            "display_number": None,
        }

    return {
        "kind": "unparsed",
        "article_key": None,
        "display_number": None,
    }
