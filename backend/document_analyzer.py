"""Retrieve constitution context per clause and request a structured analysis."""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from clause_extractor import Clause
from groq_client import generate_text
from rag_utils import _lazy_init_models, retrieve_chunks
from risk_classifier import (
    Category,
    ClauseAnalysis,
    RiskLevel,
    normalize_and_validate,
)

logger = logging.getLogger(__name__)

CHUNK_CHAR_BUDGET = 2000
MAX_CONCURRENCY = 3
RATE_LIMIT_ATTEMPTS = 3
SCOPE_NOTE = (
    "The Constitution mainly governs state-citizen relations. "
    "A private-contract concern may need Labour Act or Contract Act review (Phase 2)."
)
ANALYSIS_UNAVAILABLE = "Analysis unavailable."

_BOILERPLATE_RE = re.compile(
    r"^(definitions?|interpretation|recitals?|whereas|preamble|"
    r"table of contents|schedules?)\b",
    re.IGNORECASE,
)
_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)


def analyze_document(clauses: list[Clause]) -> list[ClauseAnalysis]:
    """Analyze each clause. Retrieval is serialized; Groq calls are capped at 3."""
    _lazy_init_models()

    results: list[ClauseAnalysis | None] = [None] * len(clauses)
    jobs: list[tuple[int, Clause, list[dict]]] = []

    for index, clause in enumerate(clauses):
        if _is_trivial(clause):
            results[index] = _with_scope(_boilerplate_analysis(clause))
            continue
        chunks = retrieve_chunks(clause.text, top_k=3, language="en")
        jobs.append((index, clause, chunks))

    if jobs:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
            for index, analysis in pool.map(_analyze_job, jobs):
                results[index] = analysis

    completed: list[ClauseAnalysis] = []
    for index, clause in enumerate(clauses):
        analysis = results[index]
        if analysis is None:
            analysis = _with_scope(_unavailable(clause.clause_id))
        completed.append(analysis)
    return completed


def _analyze_job(
    job: tuple[int, Clause, list[dict]],
) -> tuple[int, ClauseAnalysis]:
    index, clause, chunks = job
    prompt = _build_prompt(clause, chunks)
    payload = _request_json(prompt)
    if payload is None:
        logger.info("clause analysis fallback clause_id=%s", clause.clause_id)
        analysis = _unavailable(clause.clause_id)
    else:
        analysis = normalize_and_validate(payload, chunks, clause_id=clause.clause_id)
    analysis.clause_id = clause.clause_id
    logger.info(
        "clause analyzed clause_id=%s category=%s",
        clause.clause_id,
        analysis.category.value,
    )
    return index, _with_scope(analysis)


def _request_json(prompt: str) -> dict[str, Any] | None:
    """Return parsed JSON. After one retry, give up so the clause can fall back."""
    for attempt in range(2):
        raw = _generate_with_backoff(prompt if attempt == 0 else _retry_prompt(prompt))
        try:
            return _parse_model_json(raw)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _generate_with_backoff(prompt: str) -> str:
    delay = 1.0
    use_json_mode = True
    last_error: Exception | None = None
    attempts = 0
    while attempts < RATE_LIMIT_ATTEMPTS:
        attempts += 1
        try:
            return generate_text(prompt, temperature=0, json_mode=use_json_mode)
        except Exception as exc:
            last_error = exc
            if use_json_mode and _is_json_mode_rejection(exc):
                use_json_mode = False
                continue
            if is_rate_limit(exc) and attempts < RATE_LIMIT_ATTEMPTS:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("Groq request failed")


def _retry_prompt(prompt: str) -> str:
    return (
        prompt
        + "\n\nYour previous reply was not valid JSON. "
        + "Respond with one JSON object only."
    )


def _parse_model_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    fenced = _FENCE_RE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("model JSON must be an object")
    return data


def _build_prompt(clause: Clause, chunks: list[dict]) -> str:
    context = "\n\n".join(_format_chunk(chunk) for chunk in chunks) or "(no provisions retrieved)"
    heading = clause.heading or ""
    return f"""You are VerdictAI. Compare one clause of a private document with the Constitution of Bangladesh passages below.
Use ONLY the supplied constitutional texts. Do not use foreign law.
Cite only article_key values that appear in the context. If none of the passages is relevant, say so.
Never describe the clause as illegal or unconstitutional. A concern is a potential conflict, a potential rights concern, or general unfairness — keep those separate.
Constitutional conflict -> POTENTIAL_CONTRADICTION.
A right named in a supplied article -> POTENTIAL_RIGHTS_VIOLATION.
Unfairness that is not a conflict with a supplied article -> POTENTIALLY_UNFAIR.
Too vague to match the supplied texts -> AMBIGUOUS.
Nothing relevant -> NO_CLEAR_ISSUE and an empty related_articles array.
Respond with JSON only, no markdown, using this shape:
{{"category":"POTENTIAL_CONTRADICTION|POTENTIAL_RIGHTS_VIOLATION|POTENTIALLY_UNFAIR|AMBIGUOUS|NO_CLEAR_ISSUE","risk_level":"LOW|MEDIUM|HIGH","related_articles":[{{"article_key":"","quote":""}}],"why_flagged":"","analysis":"","recommendation":""}}
The quote must be copied from the supplied passage.

Constitution passages:
{context}

Clause id: {clause.clause_id}
Heading: {heading}
Clause text:
{clause.text}
"""


def _format_chunk(chunk: dict) -> str:
    content = str(chunk.get("content") or "")
    if len(content) > CHUNK_CHAR_BUDGET:
        content = content[:CHUNK_CHAR_BUDGET] + "..."
    flags = chunk.get("legal_status_flags") or []
    key = chunk.get("article_key") or ""
    display = chunk.get("display_number") or key
    block = (
        f"article_key: {key}\n"
        f"display_number: {display}\n"
        f"{str(chunk.get('chunk_type') or 'section').capitalize()} from {chunk.get('act_title') or ''}:\n"
        f"{content}"
    )
    if flags:
        block += "\nLegal status notes: " + ", ".join(str(flag) for flag in flags)
    return block


def _is_trivial(clause: Clause) -> bool:
    text = clause.text.strip()
    if not text:
        return True
    heading = (clause.heading or "").strip()
    if heading and text.casefold() == heading.casefold():
        return True
    first = text.splitlines()[0].strip()
    first = re.sub(
        r"^(?:\d+(?:\.\d+)*\.?|\([A-Za-z0-9]+\)|(?:Clause|Article|Section)\s+\d+[A-Za-z]?)\s*",
        "",
        first,
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .:;-")
    if _BOILERPLATE_RE.match(heading.strip(" .:;-")) or _BOILERPLATE_RE.match(first):
        return True
    body = text
    if heading and text.startswith(heading):
        body = text[len(heading) :].strip(" \n:.-")
    if not body:
        return True
    return False


def _boilerplate_analysis(clause: Clause) -> ClauseAnalysis:
    return ClauseAnalysis(
        clause_id=clause.clause_id,
        category=Category.NO_CLEAR_ISSUE,
        risk_level=RiskLevel.LOW,
        related_articles=[],
        why_flagged="",
        analysis="Skipped. The clause looks like a heading or boilerplate.",
        recommendation="",
        status="No Clear Issue Found",
        skipped=True,
    )


def _unavailable(clause_id: str) -> ClauseAnalysis:
    return ClauseAnalysis(
        clause_id=clause_id,
        category=Category.NO_CLEAR_ISSUE,
        risk_level=RiskLevel.LOW,
        related_articles=[],
        why_flagged="",
        analysis=ANALYSIS_UNAVAILABLE,
        recommendation="",
        status="No Clear Issue Found",
    )


def _with_scope(analysis: ClauseAnalysis) -> ClauseAnalysis:
    analysis.scope_note = SCOPE_NOTE
    return analysis


def is_rate_limit(exc: Exception) -> bool:
    if exc.__class__.__name__ == "RateLimitError":
        return True
    if getattr(exc, "status_code", None) == 429:
        return True
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 429


def _is_json_mode_rejection(exc: Exception) -> bool:
    if is_rate_limit(exc):
        return False
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    return status in {400, 422}
