"""Assemble the document-analysis report returned by POST /analyze."""

from __future__ import annotations

from clause_extractor import Clause
from risk_classifier import Category, ClauseAnalysis, RiskLevel

DISCLAIMER = (
    "This is an automated analysis, not legal advice. Consult a qualified lawyer."
)

_RISK_ORDER = {
    RiskLevel.HIGH.value: 0,
    RiskLevel.MEDIUM.value: 1,
    RiskLevel.LOW.value: 2,
}


def build_report(
    clauses: list[Clause],
    analyses: list[ClauseAnalysis],
    truncated: bool = False,
) -> dict:
    """Build the report. `clauses` stays in original order; `by_risk` groups ids."""
    if len(clauses) != len(analyses):
        raise ValueError("Clause and analysis counts do not match.")

    category_counts = {category.value: 0 for category in Category}
    risk_counts = {level.value: 0 for level in RiskLevel}
    rendered: list[dict] = []

    for index, (clause, analysis) in enumerate(zip(clauses, analyses)):
        category_counts[analysis.category.value] += 1
        risk_counts[analysis.risk_level.value] += 1
        rendered.append(_render_clause(index, clause, analysis))

    by_risk = {level.value: [] for level in RiskLevel}
    for item in sorted(
        rendered,
        key=lambda row: (
            _RISK_ORDER.get(row["risk_level"], 9),
            row["original_index"],
        ),
    ):
        by_risk[item["risk_level"]].append(item["clause_id"])

    return {
        "summary": {
            "total_clauses": len(rendered),
            "truncated": truncated,
            "categories": category_counts,
            "risk_levels": risk_counts,
        },
        "clauses": rendered,
        "by_risk": by_risk,
        "disclaimer": DISCLAIMER,
    }


def _render_clause(index: int, clause: Clause, analysis: ClauseAnalysis) -> dict:
    return {
        "clause_id": clause.clause_id,
        "heading": clause.heading,
        "original_text": clause.text,
        "original_index": index,
        "category": analysis.category.value,
        "status": analysis.status,
        "risk_level": analysis.risk_level.value,
        "related_articles": [
            {
                "article_key": article.article_key,
                "display_number": article.display_number,
                "quote": article.quote,
                "legal_status_flags": list(article.legal_status_flags),
            }
            for article in analysis.related_articles
        ],
        "why_flagged": analysis.why_flagged,
        "analysis": analysis.analysis,
        "recommendation": analysis.recommendation,
        "scope_note": analysis.scope_note,
        "skipped": analysis.skipped,
    }
