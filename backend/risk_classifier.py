"""Validate model output against retrieved constitution chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Category(str, Enum):
    POTENTIAL_CONTRADICTION = "POTENTIAL_CONTRADICTION"
    POTENTIAL_RIGHTS_VIOLATION = "POTENTIAL_RIGHTS_VIOLATION"
    POTENTIALLY_UNFAIR = "POTENTIALLY_UNFAIR"
    AMBIGUOUS = "AMBIGUOUS"
    NO_CLEAR_ISSUE = "NO_CLEAR_ISSUE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


NO_CLEAR_ISSUE_STATUS = "No Clear Issue Found"

_CATEGORY_ALIASES = {
    "POTENTIAL_CONTRADICTION": Category.POTENTIAL_CONTRADICTION,
    "CONSTITUTIONAL_CONFLICT": Category.POTENTIAL_CONTRADICTION,
    "POTENTIAL_RIGHTS_VIOLATION": Category.POTENTIAL_RIGHTS_VIOLATION,
    "POTENTIALLY_UNFAIR": Category.POTENTIALLY_UNFAIR,
    "UNFAIR": Category.POTENTIALLY_UNFAIR,
    "AMBIGUOUS": Category.AMBIGUOUS,
    "NO_CLEAR_ISSUE": Category.NO_CLEAR_ISSUE,
    "NO_CLEAR_ISSUE_FOUND": Category.NO_CLEAR_ISSUE,
}

_ARTICLE_RE = re.compile(r"\b(?:Article|article)\s+(\d+[A-Za-z]?)\b")
_ILLEGAL_RE = re.compile(r"\b(?:illegal|unlawful)\b", re.IGNORECASE)
_UNCONSTITUTIONAL_RE = re.compile(r"\bunconstitutional\b", re.IGNORECASE)
_KEY_PREFIX_RE = re.compile(r"^(?:article\s+)", re.IGNORECASE)


@dataclass
class RelatedArticle:
    article_key: str
    quote: str
    display_number: str | None = None
    legal_status_flags: list[str] = field(default_factory=list)


@dataclass
class ClauseAnalysis:
    clause_id: str
    category: Category
    risk_level: RiskLevel
    related_articles: list[RelatedArticle]
    why_flagged: str
    analysis: str
    recommendation: str
    status: str
    scope_note: str = ""
    skipped: bool = False


def normalize_and_validate(
    llm_result: Any,
    retrieved_chunks: list[dict] | None,
    clause_id: str = "",
) -> ClauseAnalysis:
    """Drop citations whose article_key was not retrieved for this clause.

    When no grounded citation remains, the clause is forced to
    "No Clear Issue Found" at LOW risk.
    """
    payload = llm_result if isinstance(llm_result, dict) else {}
    chunks_by_key = _index_chunks(retrieved_chunks or [])
    category = _coerce_category(payload.get("category"))
    risk_level = _coerce_risk(payload.get("risk_level"))
    articles = _ground_articles(payload.get("related_articles"), chunks_by_key)
    allowed_keys = {article.article_key for article in articles}

    why_flagged = _soften(str(payload.get("why_flagged") or ""), allowed_keys)
    analysis = _soften(str(payload.get("analysis") or ""), allowed_keys)
    recommendation = _soften(str(payload.get("recommendation") or ""), allowed_keys)

    if not articles:
        category = Category.NO_CLEAR_ISSUE
        risk_level = RiskLevel.LOW
        why_flagged = _soften(why_flagged, set())
        analysis = _soften(analysis, set())
        recommendation = _soften(recommendation, set())
    elif category is Category.NO_CLEAR_ISSUE:
        risk_level = RiskLevel.LOW

    status = (
        NO_CLEAR_ISSUE_STATUS
        if category is Category.NO_CLEAR_ISSUE
        else category.value
    )
    return ClauseAnalysis(
        clause_id=str(payload.get("clause_id") or clause_id),
        category=category,
        risk_level=risk_level,
        related_articles=articles,
        why_flagged=why_flagged,
        analysis=analysis,
        recommendation=recommendation,
        status=status,
    )


def _index_chunks(chunks: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for chunk in chunks:
        key = _canon_key(str(chunk.get("article_key") or ""))
        if key and key not in indexed:
            indexed[key] = chunk
    return indexed


def _canon_key(raw: str) -> str:
    text = raw.strip()
    text = _KEY_PREFIX_RE.sub("", text).strip()
    return text


def _coerce_category(value: Any) -> Category:
    if isinstance(value, Category):
        return value
    token = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
    return _CATEGORY_ALIASES.get(token, Category.NO_CLEAR_ISSUE)


def _coerce_risk(value: Any) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    token = str(value or "").strip().upper()
    try:
        return RiskLevel(token)
    except ValueError:
        return RiskLevel.LOW


def _ground_articles(raw: Any, chunks_by_key: dict[str, dict]) -> list[RelatedArticle]:
    if not isinstance(raw, list):
        return []

    grounded: list[RelatedArticle] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            key = _canon_key(item)
            quote = ""
        elif isinstance(item, dict):
            key = _canon_key(str(item.get("article_key") or ""))
            quote = str(item.get("quote") or "").strip()
        else:
            continue
        if not key or key not in chunks_by_key or key in seen:
            continue
        seen.add(key)
        chunk = chunks_by_key[key]
        content = str(chunk.get("content") or "")
        if quote and not _quote_in_content(quote, content):
            quote = _excerpt(content)
        elif not quote:
            quote = _excerpt(content)
        flags = list(chunk.get("legal_status_flags") or [])
        display = chunk.get("display_number") or key
        grounded.append(
            RelatedArticle(
                article_key=key,
                quote=quote,
                display_number=str(display) if display is not None else None,
                legal_status_flags=[str(flag) for flag in flags],
            )
        )
    return grounded


def _quote_in_content(quote: str, content: str) -> bool:
    if quote in content:
        return True
    collapsed_quote = " ".join(quote.split())
    collapsed_content = " ".join(content.split())
    return bool(collapsed_quote) and collapsed_quote in collapsed_content


def _excerpt(content: str, limit: int = 280) -> str:
    text = " ".join(content.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _soften(text: str, allowed_keys: set[str]) -> str:
    if not text:
        return ""

    def replace_article(match: re.Match[str]) -> str:
        if match.group(1) in allowed_keys:
            return match.group(0)
        return "the supplied constitutional text"

    softened = _ARTICLE_RE.sub(replace_article, text)
    softened = _UNCONSTITUTIONAL_RE.sub(
        "a potential conflict with the Constitution", softened
    )
    softened = _ILLEGAL_RE.sub("a potential concern", softened)
    return softened.strip()
