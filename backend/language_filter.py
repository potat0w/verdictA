"""Filter retrieved RAG chunks by language (strict: drop untagged chunks)."""

import logging
from typing import Dict, List


logger = logging.getLogger(__name__)

# How often a language-filtered retrieve returned fewer than requested top_k.
_language_filter_shortfall_count = 0


def get_language_filter_shortfall_count() -> int:
    """Return how many filtered retrieves returned fewer than top_k chunks."""
    return _language_filter_shortfall_count


def filter_chunks_by_language(
    chunks: List[Dict],
    language: str,
    top_k: int,
) -> List[Dict]:
    """
    Keep only chunks whose language field equals `language`.

    Chunks with no language field are dropped (strict filter).
    Returns at most top_k chunks, in the same order as input.

    When the result is shorter than top_k, increments a process-wide
    shortfall counter and logs it (no cross-language fallback).
    """
    global _language_filter_shortfall_count

    matched = []
    for chunk in chunks:
        if chunk.get("language") == language:
            matched.append(chunk)
        if len(matched) >= top_k:
            break

    if len(matched) < top_k:
        _language_filter_shortfall_count += 1
        logger.info(
            "language_filter shortfall: language=%s returned=%s "
            "requested_top_k=%s total_shortfalls=%s",
            language,
            len(matched),
            top_k,
            _language_filter_shortfall_count,
        )

    return matched
