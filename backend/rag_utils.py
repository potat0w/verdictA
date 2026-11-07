import json
import os
import logging
import pickle
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
from legal_status import attach_legal_status_flags
from hybrid_search import BM25Index, bm25_document, fuse_hits, reciprocal_rank_fusion

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBED_DIR = os.path.join(BASE_DIR, "embeddings")
INDEX_PATH = os.path.join(EMBED_DIR, "faiss.index")
META_PATH = os.path.join(EMBED_DIR, "chunk_metadata.pkl")
INDEX_META_PATH = os.path.join(EMBED_DIR, "index_meta.json")
BM25_INDEX_DIR = os.path.join(BASE_DIR, "bm25_indexes")
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_MODEL_NAME = DEFAULT_EMBED_MODEL
# Per-channel candidate depth for hybrid search (semantic and BM25 each).
CHANNEL_K = 40
# Fused shortlist per corpus before answer-quality filters.
FUSE_K = 20
# Max other-acts passages kept for the LLM after statute filters.
STATUTE_CONTEXT_LIMIT = 4
SEMANTIC_CANDIDATES = CHANNEL_K
LEXICAL_CANDIDATES = CHANNEL_K

_embed_model = None
_remote_chunks = False
_partition_cache: dict[str, list[tuple[int, dict]]] = {}
_models_initialized = False
_init_start_time = None
_index_meta = {
    "model_name": DEFAULT_EMBED_MODEL,
    "query_prefix": "",
    "passage_prefix": "",
}
_bm25_cache: dict[str, BM25Index] = {}
_init_lock = threading.Lock()
_bm25_lock = threading.Lock()


def _chunk_ref(chunk: dict) -> str:
    """Short id for logs: article/section key, else act title, else chunk_id."""
    for field in ("article_key", "section_number", "display_number"):
        value = chunk.get(field)
        if value not in (None, ""):
            return str(value)
    title = (chunk.get("act_title") or "").strip()
    if title:
        return title[:48]
    return str(chunk.get("chunk_id") or "?")


def _chunk_refs(chunks: list[dict], limit: int = 8) -> str:
    refs = [_chunk_ref(chunk) for chunk in chunks[:limit]]
    return ",".join(refs) if refs else "-"


def _rag_log(event: str, **fields) -> None:
    """One-line structured retrieval/answer observability. Grep: 'rag event='."""
    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, float):
            parts.append(f"{key}={value:.3f}")
        elif isinstance(value, (list, tuple)):
            parts.append(f"{key}={','.join(str(item) for item in value) if value else '-'}")
        elif isinstance(value, str) and (" " in value or "=" in value):
            parts.append(f'{key}="{value[:120]}"')
        else:
            parts.append(f"{key}={value}")
    logging.info("rag %s", " ".join(parts))


def _load_index_meta() -> None:
    global _index_meta, EMBED_MODEL_NAME
    from embedding_provider import (
        STORED_DIMENSION,
        STORED_DISTANCE,
        STORED_MODEL,
        model_name,
        provider_name,
    )

    # Voyage queries use input_type=query; no local MiniLM prefix file.
    if provider_name() == "voyage":
        EMBED_MODEL_NAME = model_name()
        _index_meta = {
            "model_name": EMBED_MODEL_NAME,
            "query_prefix": "",
            "passage_prefix": "",
        }
        return

    EMBED_MODEL_NAME = STORED_MODEL
    if not os.path.exists(INDEX_META_PATH):
        return
    with open(INDEX_META_PATH, encoding="utf-8") as handle:
        loaded = json.load(handle)
    model = loaded.get("model_name") or STORED_MODEL
    if model != STORED_MODEL:
        raise RuntimeError(
            f"{INDEX_META_PATH} names {model}, but retrieval requires {STORED_MODEL}."
        )
    dimension = loaded.get("dimension")
    if dimension is not None and int(dimension) != STORED_DIMENSION:
        raise RuntimeError(
            f"{INDEX_META_PATH} records dimension {dimension}, expected {STORED_DIMENSION}."
        )
    distance = loaded.get("distance")
    if distance is not None and str(distance).lower() != STORED_DISTANCE.lower():
        raise RuntimeError(
            f"{INDEX_META_PATH} records distance {distance}, expected {STORED_DISTANCE}."
        )
    _index_meta = {
        "model_name": model,
        "query_prefix": loaded.get("query_prefix") or "",
        "passage_prefix": loaded.get("passage_prefix") or "",
    }
    EMBED_MODEL_NAME = model


def _lazy_init_models() -> None:
    global _embed_model, _remote_chunks, _models_initialized, _init_start_time

    if _models_initialized:
        return

    with _init_lock:
        if _models_initialized:
            return

        if _init_start_time is None:
            _init_start_time = time.time()
            logging.info("Starting model initialization...")

        try:
            from embedding_provider import require_stored_configuration
            from groq_client import get_groq_api_key, get_groq_model
            from qdrant_store import qdrant_configured

            _load_index_meta()
            require_stored_configuration()
            if not qdrant_configured():
                raise RuntimeError("QDRANT_URL is not set")
            # Local faiss.index and chunk_metadata.pkl are not read.
            # Passage text is requested later for one collection, or for the
            # point ids a search returns. Query vectors come from the
            # configured embedding provider, not an in-process model.
            _remote_chunks = True
            logging.info("Query embeddings use %s", EMBED_MODEL_NAME)

            get_groq_api_key()
            get_groq_model()
            logging.info("Groq client configured")

            _models_initialized = True
            init_time = time.time() - _init_start_time
            logging.info("All models initialized in %.2f seconds", init_time)

        except Exception as exc:
            logging.error("Model initialization failed: %s", type(exc).__name__)
            raise


def _query_vector(query: str) -> list[float]:
    from embedding_provider import embed_query

    prefixed = f"{_index_meta.get('query_prefix') or ''}{query}"
    return embed_query(prefixed)


def _constitution_rows(language: str) -> list[tuple[int, dict]]:
    collection = f"constitution-{language}"
    cached = _partition_cache.get(collection)
    if cached is not None:
        return cached
    from qdrant_store import iter_payloads

    rows = [
        (row_id, chunk)
        for row_id, chunk in iter_payloads(collection)
        if chunk.get("chunk_type") != "footnote" and chunk.get("content")
    ]
    _partition_cache[collection] = rows
    logging.info("Qdrant constitution partition %s rows=%s", collection, len(rows))
    return rows


def _bm25_pairs(cache_key: str, rows: list[tuple[int, dict]]) -> BM25Index:
    with _bm25_lock:
        cached = _bm25_cache.get(cache_key)
        if cached is not None:
            return cached
        index = BM25Index((row_id, bm25_document(chunk)) for row_id, chunk in rows)
        _bm25_cache[cache_key] = index
        return index


def _statute_bm25_index(language: str) -> BM25Index:
    """Load other-acts BM25 from disk when present; otherwise build from Qdrant once."""
    from qdrant_store import iter_payloads

    cache_key = f"other-acts-{language}"
    with _bm25_lock:
        cached = _bm25_cache.get(cache_key)
        if cached is not None:
            return cached

        disk_path = os.path.join(BM25_INDEX_DIR, f"other-acts-{language}.pkl")
        if os.path.isfile(disk_path):
            with open(disk_path, "rb") as handle:
                index = pickle.load(handle)
            if not isinstance(index, BM25Index):
                raise TypeError(f"{disk_path} is not a BM25Index")
            _bm25_cache[cache_key] = index
            logging.info(
                "Loaded statute BM25 from disk language=%s rows=%s path=%s",
                language,
                index.n_docs,
                disk_path,
            )
            return index

        index = BM25Index()
        count = 0
        for row_id, chunk in iter_payloads("other-acts", language=language):
            if chunk.get("chunk_type") == "footnote":
                continue
            if "content" not in chunk:
                raise FileNotFoundError(
                    "Qdrant other-acts payloads have no passage text. "
                    "Run build_bm25_indexes.py or build_index.py."
                )
            index.add(row_id, bm25_document(chunk))
            count += 1
        index.finish()
        _bm25_cache[cache_key] = index
        logging.info(
            "Built statute BM25 from Qdrant language=%s rows=%s (disk miss)",
            language,
            count,
        )
        return index


def _constitution_hits_from_channels(
    query: str,
    language: str,
    scored: list[tuple[int, float]],
    lexical: list[int],
    top_k: int,
) -> list[dict]:
    from answer_quality import semantic_admit_ids

    rows = _constitution_rows(language)
    if not rows:
        return []
    by_id = {row_id: chunk for row_id, chunk in rows}
    row_ids = [row_id for row_id, _chunk in rows]
    admit = semantic_admit_ids(scored)
    semantic = [row_id for row_id, _score in scored]
    chosen = fuse_hits(query, row_ids, semantic, lexical, by_id, top_k)
    results = []
    for row_id in chosen:
        if row_id not in by_id:
            continue
        chunk = dict(by_id[row_id])
        if row_id in admit:
            chunk["semantic_admit"] = True
        results.append(attach_legal_status_flags(chunk))
    return results


def _statute_hits_from_channels(
    query: str,
    language: str,
    scored: list[tuple[int, float]],
    lexical: list[int],
    top_k: int,
) -> list[dict]:
    from qdrant_store import fetch_payloads

    semantic = [row_id for row_id, _score in scored]
    candidate_ids = list(dict.fromkeys([*semantic, *lexical]))
    if not candidate_ids:
        return []
    payloads = fetch_payloads(candidate_ids)
    by_id: dict[int, dict] = {}
    for row_id, chunk in payloads.items():
        if chunk.get("chunk_type") == "footnote":
            continue
        if chunk.get("language") not in (None, language):
            continue
        if not (chunk.get("content") or "").strip():
            continue
        by_id[row_id] = chunk
    partition = list(by_id.keys())
    if not partition:
        return []
    semantic_f = [row_id for row_id in semantic if row_id in by_id]
    lexical_f = [row_id for row_id in lexical if row_id in by_id]
    chosen = fuse_hits(query, partition, semantic_f, lexical_f, by_id, top_k)
    return [
        attach_legal_status_flags(dict(by_id[row_id]))
        for row_id in chosen
        if row_id in by_id
    ]


def _finalize_statutes(query: str, ranked: list[dict]) -> list[dict]:
    """Keep fused top statutes. Keyword select filters are not applied."""
    del query  # reserved for future light ranking; top-k only for now
    return ranked[:STATUTE_CONTEXT_LIMIT]


def _merge_scored_rankings(
    scored_lists: list[list[tuple[int, float]]],
) -> list[tuple[int, float]]:
    """RRF-merge several (id, score) lists; keep the best raw score per id for logs."""
    if not scored_lists:
        return []
    if len(scored_lists) == 1:
        return scored_lists[0]
    best_score: dict[int, float] = {}
    id_rankings: list[list[int]] = []
    for scored in scored_lists:
        ids: list[int] = []
        for row_id, score in scored:
            ids.append(row_id)
            prev = best_score.get(row_id)
            if prev is None or score > prev:
                best_score[row_id] = score
        id_rankings.append(ids)
    ordered = reciprocal_rank_fusion(id_rankings)
    return [(row_id, best_score.get(row_id, 0.0)) for row_id in ordered]


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name, "1" if default else "0").strip().lower()
    if not raw:
        return default
    return raw not in ("0", "false", "no", "off")


def _use_bm25_for_language(language: str) -> bool:
    """English/Bangla can run Voyage-only when EN_SEMANTIC_ONLY / BN_SEMANTIC_ONLY."""
    if language == "bn":
        return not _env_flag("BN_SEMANTIC_ONLY", True)
    if language == "en":
        return not _env_flag("EN_SEMANTIC_ONLY", False)
    return True


def _parallel_hybrid_retrieve(
    query: str, language: str
) -> tuple[list[dict], list[dict], dict]:
    """Multi-aspect hybrid search, then fuse per corpus.

    A cheap Groq rewrite may add 1–2 search aspects (no article numbers).
    For each aspect: constitution semantic (+ BM25 unless language semantic-only)
    and other-acts the same way. Rankings across aspects are RRF-merged, then fused.
    """
    from answer_quality import retrieval_aspect_queries
    from qdrant_store import search_collection_scored

    aspects = retrieval_aspect_queries(query, language) or [query]
    rows = _constitution_rows(language)
    use_bm25 = _use_bm25_for_language(language)
    const_bm25 = (
        _bm25_pairs(f"constitution-{language}", rows)
        if rows and use_bm25
        else None
    )
    statute_bm25 = _statute_bm25_index(language) if use_bm25 else None

    const_n = len(rows)
    const_channel = min(CHANNEL_K, const_n) if const_n else 0
    const_coll = f"constitution-{language}"
    t0 = time.time()

    const_scored_lists: list[list[tuple[int, float]]] = []
    const_lexical_lists: list[list[int]] = []
    statute_scored_lists: list[list[tuple[int, float]]] = []
    statute_lexical_lists: list[list[int]] = []

    workers = min(12, max(4, (2 if not use_bm25 else 4) * len(aspects)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = []
        for aspect in aspects:
            vector = _query_vector(aspect)
            fut_cs = (
                pool.submit(
                    search_collection_scored, vector, const_coll, const_channel
                )
                if const_channel
                else None
            )
            fut_cb = (
                pool.submit(const_bm25.rank, aspect, const_channel)
                if const_channel and const_bm25 is not None
                else None
            )
            fut_ss = pool.submit(
                search_collection_scored,
                vector,
                "other-acts",
                CHANNEL_K,
                language,
            )
            fut_sb = (
                pool.submit(statute_bm25.rank, aspect, CHANNEL_K)
                if statute_bm25 is not None
                else None
            )
            jobs.append((fut_cs, fut_cb, fut_ss, fut_sb))

        for fut_cs, fut_cb, fut_ss, fut_sb in jobs:
            const_scored_lists.append(fut_cs.result() if fut_cs else [])
            const_lexical_lists.append(fut_cb.result() if fut_cb else [])
            statute_scored_lists.append(fut_ss.result())
            statute_lexical_lists.append(fut_sb.result() if fut_sb else [])

    parallel_ms = int((time.time() - t0) * 1000)
    const_scored = _merge_scored_rankings(const_scored_lists)
    statute_scored = _merge_scored_rankings(statute_scored_lists)
    if use_bm25:
        const_lexical = (
            reciprocal_rank_fusion(const_lexical_lists)
            if len(const_lexical_lists) > 1
            else (const_lexical_lists[0] if const_lexical_lists else [])
        )
        statute_lexical = (
            reciprocal_rank_fusion(statute_lexical_lists)
            if len(statute_lexical_lists) > 1
            else (statute_lexical_lists[0] if statute_lexical_lists else [])
        )
    else:
        # Semantic-only: fused list follows Voyage order (no BM25 RRF dilution).
        const_lexical = []
        statute_lexical = []

    # Citation pinning uses the original user question text.
    constitution = _constitution_hits_from_channels(
        query, language, const_scored, const_lexical, FUSE_K
    )
    statutes_raw = _statute_hits_from_channels(
        query, language, statute_scored, statute_lexical, FUSE_K
    )
    statutes = _finalize_statutes(query, statutes_raw)

    const_by_id = {row_id: chunk for row_id, chunk in rows}
    stats = {
        "parallel_ms": parallel_ms,
        "aspects": aspects,
        "aspect_count": len(aspects),
        "semantic_only": not use_bm25,
        "bn_semantic_only": language == "bn" and not use_bm25,
        "en_semantic_only": language == "en" and not use_bm25,
        "use_bm25": use_bm25,
        "const_semantic_k": const_channel,
        "const_bm25_k": const_channel if use_bm25 else 0,
        "statute_semantic_k": CHANNEL_K,
        "statute_bm25_k": CHANNEL_K if use_bm25 else 0,
        "const_semantic_hits": len(const_scored),
        "const_bm25_hits": len(const_lexical),
        "statute_semantic_hits": len(statute_scored),
        "statute_bm25_hits": len(statute_lexical),
        "const_fused": len(constitution),
        "statute_fused": len(statutes_raw),
        "statute_final": len(statutes),
        "top_const_semantic": [
            f"{_chunk_ref(const_by_id[row_id])}:{score:.3f}"
            for row_id, score in const_scored[:5]
            if row_id in const_by_id
        ],
        "top_const_bm25": [
            _chunk_ref(const_by_id[row_id])
            for row_id in const_lexical[:5]
            if row_id in const_by_id
        ],
        "constitution_refs": _chunk_refs(constitution),
        "statute_refs": _chunk_refs(statutes),
    }
    return constitution, statutes, stats


def _retrieve_remote(query: str, top_k: int, language: Optional[str]) -> List[Dict]:
    """Constitution hybrid search using one Qdrant collection, not the full index."""
    from qdrant_store import search_collection_scored

    if language not in ("en", "bn"):
        return []
    rows = _constitution_rows(language)
    if not rows:
        return []
    row_ids = [row_id for row_id, _chunk in rows]
    semantic_k = min(CHANNEL_K, len(row_ids))
    lexical_k = min(CHANNEL_K, len(row_ids))
    collection = f"constitution-{language}"
    t0 = time.time()
    scored = search_collection_scored(_query_vector(query), collection, semantic_k)
    lexical = _bm25_pairs(collection, rows).rank(query, lexical_k)
    results = _constitution_hits_from_channels(
        query, language, scored, lexical, top_k
    )
    by_id = {row_id: chunk for row_id, chunk in rows}
    _rag_log(
        "retrieve.constitution",
        language=language,
        partition=len(row_ids),
        semantic_k=semantic_k,
        bm25_k=lexical_k,
        fused=len(results),
        top_semantic=[
            f"{_chunk_ref(by_id[row_id])}:{score:.3f}"
            for row_id, score in scored[:5]
            if row_id in by_id
        ],
        top_bm25=[
            _chunk_ref(by_id[row_id]) for row_id in lexical[:5] if row_id in by_id
        ],
        fused_refs=_chunk_refs(results),
        ms=int((time.time() - t0) * 1000),
    )
    return results


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    language: Optional[str] = None,
) -> List[Dict]:
    """Hybrid search inside one language partition.

    Signature is unchanged. A language value searches that constitution
    collection before any ranking, then fuses cosine and BM25.
    """
    if top_k <= 0 or not (query or "").strip():
        return []
    _lazy_init_models()
    return _retrieve_remote(query, top_k, language)


ANSWER_TOKEN_BUDGET = 2200


def voice_answer_token_budget() -> int:
    """Spoken-answer token cap. Smaller than the text budget so less text reaches TTS."""
    raw = os.getenv("VOICE_ANSWER_TOKEN_BUDGET", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return 180


def spoken_character_limit(token_budget: int) -> int:
    """Rough speech length for a token budget. Four characters is about one token."""
    return token_budget * 4


def _same_article_parts(chunk: dict) -> list[dict]:
    """Other stored parts of one article. The answer path does not call this.

    A second chunk is included only when that chunk itself passes selection.
    """
    key = chunk.get("article_key")
    collection = chunk.get("collection")
    if not key or not str(collection or "").startswith("constitution"):
        return [chunk]
    source = [row for _row_id, row in _partition_cache.get(str(collection), [])]
    parts = [
        row
        for row in source
        if row.get("collection") == collection and str(row.get("article_key")) == str(key)
    ]
    parts.sort(key=lambda row: row.get("chunk_id") or "")
    kept: list[dict] = []
    total = 0
    for part in parts:
        text = (part.get("content") or "").strip()
        if len(text) < 40:
            continue
        if total >= 2000:
            break
        kept.append(part)
        total += len(text)
    return kept or [chunk]


def _statute_chunks(query: str, language: Optional[str]) -> list[dict]:
    """Same-language statute passages via hybrid semantic + BM25."""
    if language not in ("en", "bn"):
        return []
    return _remote_statute_chunks(query, language)


def _remote_statute_chunks(query: str, language: str) -> list[dict]:
    """Hybrid other-acts search (standalone path; ask uses the parallel helper)."""
    from qdrant_store import search_collection_scored

    t0 = time.time()
    index = _statute_bm25_index(language)
    vector = _query_vector(query)
    scored = search_collection_scored(vector, "other-acts", CHANNEL_K, language)
    lexical = index.rank(query, CHANNEL_K)
    ranked = _statute_hits_from_channels(query, language, scored, lexical, FUSE_K)
    final = _finalize_statutes(query, ranked)
    _rag_log(
        "retrieve.statutes",
        language=language,
        semantic_hits=len(scored),
        bm25_hits=len(lexical),
        fused=len(ranked),
        final=len(final),
        refs=_chunk_refs(final),
        ms=int((time.time() - t0) * 1000),
    )
    return final


def _answer_chunks(query: str, language: Optional[str], history) -> list[dict]:
    """Hybrid fuse, then send fused top-k to the LLM. No keyword/issue filters."""
    from answer_quality import context_limit, retrieval_language, retrieval_text

    search_text = retrieval_text(query, history)
    search_language = retrieval_language(query, language)
    limit = context_limit()
    _rag_log(
        "retrieve.plan",
        search_language=search_language,
        query_chars=len(query or ""),
        search_chars=len(search_text or ""),
        history_turns=len(history or []),
        channel_k=CHANNEL_K,
        fuse_k=FUSE_K,
        context_limit=limit,
    )
    if search_language not in ("en", "bn"):
        return []

    ranked, statutes, stats = _parallel_hybrid_retrieve(search_text, search_language)
    _rag_log(
        "retrieve.aspects",
        language=search_language,
        count=stats.get("aspect_count"),
        queries=stats.get("aspects"),
    )
    _rag_log(
        "retrieve.parallel",
        language=search_language,
        parallel_ms=stats["parallel_ms"],
        aspects=stats.get("aspect_count"),
        use_bm25=stats.get("use_bm25"),
        semantic_only=stats.get("semantic_only"),
        bn_semantic_only=stats.get("bn_semantic_only"),
        en_semantic_only=stats.get("en_semantic_only"),
        const_semantic=stats["const_semantic_hits"],
        const_bm25=stats["const_bm25_hits"],
        statute_semantic=stats["statute_semantic_hits"],
        statute_bm25=stats["statute_bm25_hits"],
        const_fused=stats["const_fused"],
        statute_fused=stats["statute_fused"],
        top_const_semantic=stats["top_const_semantic"],
        top_const_bm25=stats["top_const_bm25"],
    )

    constitution: list[dict] = []
    seen: set[str] = set()
    for chunk in ranked[:limit]:
        identity = str(chunk.get("chunk_id") or id(chunk))
        if identity in seen:
            continue
        seen.add(identity)
        constitution.append(attach_legal_status_flags(chunk))
    _rag_log(
        "retrieve.topk",
        fused=len(ranked),
        constitution=len(constitution),
        statutes=len(statutes),
        constitution_refs=_chunk_refs(constitution),
        statute_refs=_chunk_refs(statutes),
        context_limit=limit,
        statute_limit=STATUTE_CONTEXT_LIMIT,
    )
    return constitution + statutes


def summarize_for_voice(answer: str, language: Optional[str]) -> str:
    """Short speech from a finished legal answer. The long text is not what gets spoken.

    Retrieval and the legal answer stay as they are. This only limits the words
    sent onward for text-to-speech.
    """
    from answer_quality import (
        build_voice_summary_prompt,
        clean_answer,
        spoken_form,
        trim_spoken,
        voice_summary_instructions,
        without_new_references,
    )
    from groq_client import generate_text, get_groq_model

    budget = voice_answer_token_budget()
    limit = spoken_character_limit(budget)
    plain = spoken_form(answer)
    if len(plain) <= limit:
        return plain

    effort = "low" if "gpt-oss" in get_groq_model() else None
    instructions = voice_summary_instructions(language)
    prompt = build_voice_summary_prompt(answer)

    def complete(max_tokens: int) -> str:
        return clean_answer(
            generate_text(
                prompt,
                system=instructions,
                temperature=0,
                max_tokens=max_tokens,
                reasoning_effort=effort,
            )
        )

    # The model may spend part of max_tokens on reasoning. The spoken cap below
    # is what limits the characters sent to text-to-speech.
    summary = complete(budget + 256)
    if not summary and effort is not None:
        summary = complete((budget + 256) * 2)
    spoken = without_new_references(answer, spoken_form(summary))
    if not spoken:
        return trim_spoken(plain, limit)
    return trim_spoken(spoken, limit)


def answer_with_rag(
    query: str,
    language: Optional[str] = None,
    *,
    history=None,
    voice: bool = False,
) -> str:
    """Legal answer for POST /ask. Voice receives a spoken summary of that answer."""
    from answer_quality import (
        append_citation_note,
        answer_problems,
        build_answer_prompt,
        clean_answer,
        insufficient_answer,
        legal_system_prompt,
        question_script,
        repair_answer,
        response_language,
        unrecognized_question,
    )
    from groq_client import generate_text, get_groq_model

    _lazy_init_models()
    start_time = time.time()
    reply_language = response_language(query, language)
    script = question_script(query)
    _rag_log(
        "ask.start",
        voice=bool(voice),
        requested_language=language or "-",
        reply_language=reply_language or "-",
        script=script or "-",
        query_chars=len(query or ""),
        history_turns=len(history or []),
    )
    if script is None:
        _rag_log(
            "ask.done",
            outcome="unrecognized",
            ms=int((time.time() - start_time) * 1000),
        )
        return unrecognized_question(reply_language)
    chunks = _answer_chunks(query, language, history)
    if not chunks:
        _rag_log(
            "ask.done",
            outcome="insufficient_sources",
            ms=int((time.time() - start_time) * 1000),
        )
        return insufficient_answer(reply_language)

    system = legal_system_prompt(reply_language)
    prompt = build_answer_prompt(query, chunks, reply_language, history)
    _rag_log(
        "generate.start",
        sources=len(chunks),
        source_refs=_chunk_refs(chunks),
        prompt_chars=len(prompt),
    )

    effort = "low" if "gpt-oss" in get_groq_model() else None

    def complete(text: str) -> str:
        answer_text = clean_answer(
            generate_text(
                text,
                system=system,
                temperature=0,
                max_tokens=ANSWER_TOKEN_BUDGET,
                reasoning_effort=effort,
            )
        )
        if answer_text or effort is None:
            return answer_text
        return clean_answer(
            generate_text(
                text,
                system=system,
                temperature=0,
                max_tokens=ANSWER_TOKEN_BUDGET * 2,
                reasoning_effort=effort,
            )
        )

    t_gen = time.time()
    answer = repair_answer(complete(prompt), chunks)
    problems = answer_problems(answer, chunks)
    repaired = False
    noted = False
    if problems:
        _rag_log("generate.problems", count=len(problems), problems=problems[:6])
        rewritten = complete(
            prompt
            + "\n\nThe previous answer used "
            + ", ".join(problems)
            + ", which are not in the legal texts. Rewrite the full answer without those. Name only provisions from the list above, and do not name a court or office the texts do not name.\nAnswer:"
        )
        if rewritten and len(answer_problems(rewritten, chunks)) <= len(problems):
            answer = rewritten
            repaired = True
        problems = answer_problems(answer, chunks)
        if problems:
            answer = append_citation_note(answer, problems, reply_language)
            noted = True

    if not answer:
        answer = insufficient_answer(reply_language)
        outcome = "empty_after_generate"
    else:
        outcome = "ok"
    if voice:
        t_voice = time.time()
        answer = summarize_for_voice(answer, reply_language)
        _rag_log(
            "voice.summary",
            answer_chars=len(answer or ""),
            ms=int((time.time() - t_voice) * 1000),
        )
    _rag_log(
        "ask.done",
        outcome=outcome,
        sources=len(chunks),
        repaired=repaired,
        citation_note=noted,
        answer_chars=len(answer or ""),
        generate_ms=int((time.time() - t_gen) * 1000),
        ms=int((time.time() - start_time) * 1000),
    )
    return answer
