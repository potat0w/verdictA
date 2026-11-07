"""Parse backend/gold_eval.txt into retrieval cases.

Expected article numbers are for scoring only. They are never passed into
retrieval. Clause suffixes like 21(2) or 15(a) normalize to the article key
stored in the index (21, 15, 2A).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_GOLD_PATH = BASE_DIR / "gold_eval.txt"

_ARTICLE_RE = re.compile(
    r"(?:Article|Art\.?|অনুচ্ছেদ)\s*([0-9০-৯]+[A-Za-zক-হ]?)",
    re.IGNORECASE,
)
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_BN_LETTER = {
    "ক": "A",
    "খ": "B",
    "গ": "C",
    "ঘ": "D",
    "ঙ": "E",
    "চ": "F",
    "ছ": "G",
    "জ": "H",
}

_NUMBERED_CASE = re.compile(r"^(\d+)\.\s+(.+)\s*$")
# Topic titles use an em/en dash between EN and BN names — not gold Article lines.
_TOPIC_CASE = re.compile(r"^(.+?)\s+[—–-]\s+(.+)\s*$")
_NOT_A_CASE_TITLE = re.compile(
    r"^(?:Article|Art\.?|অনুচ্ছেদ|Expected|ব্যাখ্যা|The exact)\b",
    re.IGNORECASE,
)
_LABELS = {
    "english_question": re.compile(
        r"^(?:English Question|Question \(English\))\s*:?\s*$", re.IGNORECASE
    ),
    "bangla_question": re.compile(
        r"^(?:বাংলা প্রশ্ন|প্রশ্ন \(বাংলা\))\s*:?\s*$"
    ),
    "expected": re.compile(r"^Expected [Aa]nswer\s*:?\s*$"),
    "explanation": re.compile(r"^ব্যাখ্যা\s*:"),
}


@dataclass(frozen=True)
class GoldCase:
    case_id: str
    title: str
    language: str  # "en" | "bn"
    query: str
    expected_articles: tuple[str, ...]


def normalize_article_key(raw: str) -> str:
    """Map gold mentions to index article_key form (e.g. ২৯ক -> 29A, 21(2) -> 21)."""
    text = (raw or "").strip().translate(_BN_DIGITS)
    text = re.split(r"[(\[]", text, maxsplit=1)[0].strip()
    match = re.match(r"^(\d+)([A-Za-zক-হ]*)$", text)
    if not match:
        return text.upper() if text else text
    number, letters = match.group(1), match.group(2)
    suffix = "".join(
        _BN_LETTER.get(ch, ch.upper()) if "ক" <= ch <= "হ" else ch.upper()
        for ch in letters
    )
    return number + suffix


def expected_articles_from_text(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for match in _ARTICLE_RE.finditer(text or ""):
        key = normalize_article_key(match.group(1))
        if key and key not in found:
            found.append(key)
    return tuple(found)


def _slug(title: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()[:48]


def _parse_blocks(raw: str) -> list[tuple[str, dict[str, str]]]:
    lines = raw.splitlines()
    blocks: list[tuple[str, dict[str, str]]] = []
    title: str | None = None
    fields: dict[str, list[str]] = {}
    current: str | None = None

    def flush() -> None:
        nonlocal title, fields, current
        if not title:
            return
        text_fields = {
            key: "\n".join(parts).strip() for key, parts in fields.items() if parts
        }
        blocks.append((title, text_fields))
        title = None
        fields = {}
        current = None

    for line in lines:
        stripped = line.strip()
        numbered = _NUMBERED_CASE.match(stripped)
        topic = _TOPIC_CASE.match(stripped)
        is_case = False
        new_title = ""
        if numbered and not _NOT_A_CASE_TITLE.match(numbered.group(2)):
            is_case = True
            new_title = f"{numbered.group(1)}. {numbered.group(2).strip()}"
        elif (
            topic
            and not _NOT_A_CASE_TITLE.match(stripped)
            and not any(label.match(stripped) for label in _LABELS.values())
        ):
            is_case = True
            new_title = stripped

        if is_case:
            flush()
            title = new_title
            fields = {
                "english_question": [],
                "bangla_question": [],
                "expected": [],
            }
            current = None
            continue

        labeled = False
        for name, pattern in _LABELS.items():
            if pattern.match(stripped):
                current = name if name != "explanation" else None
                labeled = True
                break
        if labeled:
            continue
        if title is None or current is None:
            continue
        if current in fields:
            fields[current].append(line)

    flush()
    return blocks


def load_gold_cases(path: Path | str | None = None) -> list[GoldCase]:
    """Load EN and BN retrieval cases. Expected keys are scoring labels only."""
    gold_path = Path(path) if path else DEFAULT_GOLD_PATH
    raw = gold_path.read_text(encoding="utf-8")
    cases: list[GoldCase] = []
    for title, fields in _parse_blocks(raw):
        expected = expected_articles_from_text(fields.get("expected", ""))
        if not expected:
            continue
        slug = _slug(title)
        en_q = fields.get("english_question", "").strip()
        bn_q = fields.get("bangla_question", "").strip()
        if en_q:
            cases.append(
                GoldCase(
                    case_id=f"{slug}-en",
                    title=title,
                    language="en",
                    query=en_q,
                    expected_articles=expected,
                )
            )
        if bn_q:
            cases.append(
                GoldCase(
                    case_id=f"{slug}-bn",
                    title=title,
                    language="bn",
                    query=bn_q,
                    expected_articles=expected,
                )
            )
    return cases
