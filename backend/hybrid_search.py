"""Keyword rank, reciprocal rank fusion, and language partitions.

Pure functions. The FAISS call stays in rag_utils.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict

from article_parser import normalize_bn_article_token

RRF_K = 60
BM25_K1 = 1.2
BM25_B = 0.75

_TOKEN = re.compile(r"[A-Za-z0-9]+|[\u0980-\u09FF]+")
# Inflection endings, using the vowel sign ে rather than the letter এ.
# The surface word is kept. These only add the form that appears in the constitution.
_BN_SUFFIXES = ("গুলোর", "গুলো", "গুলি", "দের", "কৃত", "ের", "কে", "তে", "টি", "টা")
# Genitive র after া/ি/ী, as in চলাফেরার. ে+র is already the ের suffix.
_BN_GENITIVE_SIGNS = set("ািী")
# The constitution says গ্রহণ where a question says অধিগ্রহণ.
_BN_ALSO = {"অধিগ্রহণ": ("গ্রহণ",)}
# Frequent Bangla function words. They match almost every article and hide the real issue.
_BN_FUNCTION = {
    "এবং", "বা", "না", "কি", "কী", "এই", "সে", "তার", "জন্য", "করা", "করে",
    "করেছে", "হয়েছে", "হয়েছে", "কাউকে", "কিন্তু", "থেকে", "কোন", "কোনো",
    "একটি", "একই", "সেই", "আর", "কেন", "পারে", "ক্ষেত্রে", "দিনে", "হলে",
    "যদি", "যে", "যা", "তা", "এটি", "তাদের", "চাইতে", "খাটে", "নিয়ম",
    "ছাড়া", "ছাড়াই", "মধ্যে", "পর", "আগে",
}
_CITATION = re.compile(
    r"(?:article|art\.?|section|sec\.?|অনুচ্ছেদ|ধারা)\s*([0-9০-৯]+[A-Za-zক-হ]?)",
    re.IGNORECASE,
)


def normalize_query(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _fold_english(token: str) -> str:
    """Join threatening with threatens, without changing Bangla tokens."""
    if any("\u0980" <= char <= "\u09ff" for char in token):
        return token
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 7 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 6 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 5 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _bangla_forms(token: str) -> list[str]:
    """Surface form plus the stem. চলাফেরার then also matches চলাফেরা."""
    forms = [token]
    pending = [token]
    while pending:
        current = pending.pop()
        candidates: list[str] = []
        for suffix in _BN_SUFFIXES:
            if current.endswith(suffix) and len(current) - len(suffix) >= 4:
                candidates.append(current[: -len(suffix)])
        if (
            len(current) >= 6
            and current.endswith("র")
            and not current.endswith("ের")
            and current[-2] in _BN_GENITIVE_SIGNS
        ):
            stem = current[:-1]
            if len(stem) >= 5:
                candidates.append(stem)
        for stem in candidates:
            if stem not in forms:
                forms.append(stem)
                pending.append(stem)
    for form in list(forms):
        for extra in _BN_ALSO.get(form, ()):
            if extra not in forms:
                forms.append(extra)
    return forms


def tokenize(text: str) -> list[str]:
    folded = []
    for token in _TOKEN.findall(normalize_query(text)):
        word = _fold_english(token.lower())
        if word in _BN_FUNCTION:
            continue
        if any("\u0980" <= char <= "\u09ff" for char in word):
            folded.extend(_bangla_forms(word))
        else:
            folded.append(word)
    return folded


def cited_keys(query: str) -> list[str]:
    """Article or section numbers the query names, in order, canonical form."""
    keys: list[str] = []
    for match in _CITATION.finditer(normalize_query(query)):
        key = normalize_bn_article_token(match.group(1))
        if key and key not in keys:
            keys.append(key)
    return keys


def bm25_document(chunk: dict) -> str:
    """Text ranked by BM25. The article or section key is repeated so it outranks a cross-reference."""
    parts = [chunk.get("content") or ""]
    for field in ("article_key", "display_number", "section_number"):
        value = chunk.get(field)
        if value:
            token = str(value)
            parts.append(" ".join((token, token, token)))
    title = (chunk.get("section_title") or "").strip()
    if title:
        parts.append(title)
    return " ".join(parts)


def partition_ids(chunks: list[dict], language: str | None) -> list[int]:
    """Row ids to search.

    A language request searches that constitution collection only.
    Legacy indexes have no collection field: use language plus article_key.
    Footnotes stay out of both paths.
    """
    selected: list[int] = []
    for index, chunk in enumerate(chunks):
        if chunk.get("chunk_type") == "footnote":
            continue
        collection = chunk.get("collection")
        if language is None:
            selected.append(index)
            continue
        if collection:
            if collection == f"constitution-{language}":
                selected.append(index)
            continue
        if chunk.get("language") == language and chunk.get("article_key"):
            selected.append(index)
    return selected


class BM25Index:
    def __init__(self, documents: list[tuple[int, str]] | None = None):
        self.row_ids: list[int] = []
        self.lengths: list[int] = []
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.df: Counter[str] = Counter()
        self.n_docs = 0
        self.avgdl = 0.0
        self._open = True
        if documents:
            for row_id, text in documents:
                self.add(row_id, text)
            self.finish()

    def add(self, row_id: int, text: str) -> None:
        """Add one document. Passage text is not kept after the counts are stored."""
        if not self._open:
            raise RuntimeError("BM25 index is already finished")
        counts = Counter(tokenize(text))
        length = sum(counts.values()) or 1
        doc_index = len(self.row_ids)
        self.row_ids.append(row_id)
        self.lengths.append(length)
        self.df.update(counts.keys())
        for term, freq in counts.items():
            self.postings[term].append((doc_index, freq))

    def finish(self) -> None:
        if not self._open:
            return
        self.n_docs = len(self.row_ids)
        self.avgdl = sum(self.lengths) / self.n_docs if self.n_docs else 0.0
        self._open = False

    def rank(self, query: str, k: int = 20) -> list[int]:
        if self._open:
            self.finish()
        if self.n_docs == 0 or k <= 0:
            return []
        scores = [0.0] * self.n_docs
        for term in tokenize(query):
            posting = self.postings.get(term)
            if not posting:
                continue
            df = self.df[term]
            idf = math.log(1.0 + (self.n_docs - df + 0.5) / (df + 0.5))
            for doc_index, freq in posting:
                denom = freq + BM25_K1 * (
                    1.0 - BM25_B + BM25_B * self.lengths[doc_index] / self.avgdl
                )
                scores[doc_index] += idf * (freq * (BM25_K1 + 1.0)) / denom
        ranked = sorted(
            ((score, doc_index) for doc_index, score in enumerate(scores) if score > 0),
            key=lambda item: (-item[0], item[1]),
        )
        return [self.row_ids[doc_index] for _, doc_index in ranked[:k]]


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = RRF_K) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for position, row_id in enumerate(ranking):
            scores[row_id] = scores.get(row_id, 0.0) + 1.0 / (k + position + 1)
    return sorted(scores, key=lambda row_id: (-scores[row_id], row_id))


def _chunk_sort_key(chunk: dict) -> tuple:
    return (chunk.get("part_index") or 0, chunk.get("chunk_id") or "")


def matching_row_ids(chunks: list[dict], row_ids: list[int], key: str) -> list[int]:
    matched = [row_id for row_id in row_ids if _chunk_matches_key(chunks[row_id], key)]
    matched.sort(key=lambda row_id: _chunk_sort_key(chunks[row_id]))
    return matched


def _chunk_matches_key(chunk: dict, key: str) -> bool:
    article_key = chunk.get("article_key")
    if article_key and str(article_key) == key:
        return True
    section_number = chunk.get("section_number")
    if section_number and str(section_number) == key:
        return True
    display = chunk.get("display_number")
    if display and normalize_bn_article_token(str(display)) == key:
        return True
    return False


def fuse_hits(
    query: str,
    partition: list[int],
    semantic_ids: list[int],
    lexical_ids: list[int],
    chunks: list[dict],
    top_k: int,
) -> list[int]:
    """Pin named articles or sections, then fill with reciprocal rank fusion."""
    if top_k <= 0 or not partition:
        return []
    allowed = set(partition)
    semantic = [row_id for row_id in semantic_ids if row_id in allowed]
    lexical = [row_id for row_id in lexical_ids if row_id in allowed]
    fused = reciprocal_rank_fusion([semantic, lexical])

    ordered: list[int] = []
    seen: set[int] = set()

    def push(row_id: int) -> None:
        if row_id in seen or row_id not in allowed:
            return
        seen.add(row_id)
        ordered.append(row_id)

    for key in cited_keys(query):
        for row_id in matching_row_ids(chunks, partition, key):
            push(row_id)
            if len(ordered) >= top_k:
                return ordered
    for row_id in fused:
        push(row_id)
        if len(ordered) >= top_k:
            break
    return ordered
