"""Legal status flags for Bangladesh Constitution article chunks."""

from typing import Dict, List


# Articles declared void by the High Court Division judgment of 17 Dec 2024
# (partial challenge to the Constitution (Fifteenth Amendment) Act, 2011).
# These flags are NOT in the BD Laws consolidated text; they are overlay notes.
HC_DEC2024_DECLARED_VOID = "hc_dec2024_declared_void"

SOURCE_IS_BDLAWS_CONSOLIDATION_THROUGH_2018 = (
    "source_is_bdlaws_consolidation_through_2018"
)

FLAGS_BY_ARTICLE_KEY = {
    "7A": [HC_DEC2024_DECLARED_VOID],
    "7B": [HC_DEC2024_DECLARED_VOID],
}


def flags_for_article(article_key: str | None) -> List[str]:
    """Return legal_status_flags for a constitution article_key."""
    if not article_key:
        return []

    flags = [SOURCE_IS_BDLAWS_CONSOLIDATION_THROUGH_2018]
    flags.extend(FLAGS_BY_ARTICLE_KEY.get(article_key, []))
    return flags


def attach_legal_status_flags(chunk: Dict) -> Dict:
    """
    Return a shallow copy of chunk with legal_status_flags set.

    Non-constitution chunks (no article_key) get an empty list.
    Does not mutate the original metadata row.
    """
    enriched = dict(chunk)
    article_key = enriched.get("article_key")
    if article_key:
        enriched["legal_status_flags"] = flags_for_article(article_key)
    else:
        enriched["legal_status_flags"] = []
    return enriched
