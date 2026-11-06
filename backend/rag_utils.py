import json
import os
import logging
import threading
import time
from typing import List, Dict, Optional
from legal_status import attach_legal_status_flags
from hybrid_search import BM25Index, bm25_document, fuse_hits

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBED_DIR = os.path.join(BASE_DIR, "embeddings")
INDEX_PATH = os.path.join(EMBED_DIR, "faiss.index")
META_PATH = os.path.join(EMBED_DIR, "chunk_metadata.pkl")
INDEX_META_PATH = os.path.join(EMBED_DIR, "index_meta.json")
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_MODEL_NAME = DEFAULT_EMBED_MODEL
SEMANTIC_CANDIDATES = 20
LEXICAL_CANDIDATES = 20

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


def _load_index_meta() -> None:
    global _index_meta, EMBED_MODEL_NAME
    from embedding_provider import STORED_DIMENSION, STORED_DISTANCE, STORED_MODEL

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
    cached = _bm25_cache.get(cache_key)
    if cached is not None:
        return cached
    index = BM25Index((row_id, bm25_document(chunk)) for row_id, chunk in rows)
    _bm25_cache[cache_key] = index
    return index


def _retrieve_remote(query: str, top_k: int, language: Optional[str]) -> List[Dict]:
    """Constitution hybrid search using one Qdrant collection, not the full index."""
    from answer_quality import semantic_admit_ids
    from qdrant_store import search_collection_scored

    if language not in ("en", "bn"):
        return []
    rows = _constitution_rows(language)
    if not rows:
        return []
    by_id = {row_id: chunk for row_id, chunk in rows}
    row_ids = [row_id for row_id, _chunk in rows]
    semantic_k = min(max(top_k * 4, SEMANTIC_CANDIDATES), len(row_ids))
    lexical_k = min(max(top_k * 4, LEXICAL_CANDIDATES), len(row_ids))
    collection = f"constitution-{language}"
    # The stored MiniLM vectors are English. Bangla scores sit in one high band
    # and the nearest articles are the wrong ones, so Bangla rank is the word match.
    if language == "bn":
        scored = []
    else:
        scored = search_collection_scored(_query_vector(query), collection, semantic_k)
    admit = semantic_admit_ids(scored)
    semantic = [row_id for row_id, _score in scored]
    lexical = _bm25_pairs(collection, rows).rank(query, lexical_k)
    chosen = fuse_hits(query, row_ids, semantic, lexical, by_id, top_k)
    logging.info(
        "hybrid retrieve language=%s partition=%s returned=%s",
        language,
        len(row_ids),
        len(chosen),
    )
    results = []
    for row_id in chosen:
        if row_id not in by_id:
            continue
        chunk = dict(by_id[row_id])
        if row_id in admit:
            chunk["semantic_admit"] = True
        results.append(attach_legal_status_flags(chunk))
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
    """Same-language statute passages that share the question's words."""
    if language not in ("en", "bn"):
        return []
    return _remote_statute_chunks(query, language)


def _remote_statute_chunks(query: str, language: str) -> list[dict]:
    """BM25 over one language of Other Acts. The raw passages are not retained."""
    from answer_quality import (
        prefer_general_statutes,
        select_relevant_chunks,
        statutes_about_the_issue,
    )
    from qdrant_store import fetch_payloads, iter_payloads

    cache_key = f"other-acts-{language}"
    index = _bm25_cache.get(cache_key)
    if index is None:
        index = BM25Index()
        count = 0
        for row_id, chunk in iter_payloads("other-acts", language=language):
            if chunk.get("chunk_type") == "footnote":
                continue
            if "content" not in chunk:
                raise FileNotFoundError(
                    "Qdrant other-acts payloads have no passage text. Run upload_qdrant.py."
                )
            index.add(row_id, bm25_document(chunk))
            count += 1
        index.finish()
        _bm25_cache[cache_key] = index
        logging.info("Qdrant statute BM25 language=%s rows=%s", language, count)
    ranked_ids = index.rank(query, 40)
    payloads = fetch_payloads(ranked_ids)
    ranked = [
        attach_legal_status_flags(payloads[row_id])
        for row_id in ranked_ids
        if row_id in payloads
    ]
    matched = select_relevant_chunks(query, ranked, limit=12)
    matched = statutes_about_the_issue(query, matched)
    return prefer_general_statutes(query, matched)[:3]


def _answer_chunks(query: str, language: Optional[str], history) -> list[dict]:
    from answer_quality import (
        context_limit,
        on_the_same_issue,
        retrieval_language,
        retrieval_text,
        select_relevant_chunks,
    )

    search_text = retrieval_text(query, history)
    search_language = retrieval_language(query, language)
    ranked = retrieve_chunks(search_text, top_k=20, language=search_language)
    selected = select_relevant_chunks(search_text, ranked, limit=context_limit())
    constitution: list[dict] = []
    seen: set[str] = set()
    for chunk in selected:
        identity = str(chunk.get("chunk_id") or id(chunk))
        if identity in seen:
            continue
        seen.add(identity)
        constitution.append(attach_legal_status_flags(chunk))
    statutes = _statute_chunks(query, search_language)
    constitution = on_the_same_issue(search_text, statutes, constitution)
    logging.info(
        "answer sources constitution=%s statute=%s",
        len(constitution),
        len(statutes),
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
    if question_script(query) is None:
        logging.info("RAG query completed in %.2fs", time.time() - start_time)
        return unrecognized_question(reply_language)
    chunks = _answer_chunks(query, language, history)
    if not chunks:
        logging.info("RAG query completed in %.2fs", time.time() - start_time)
        return insufficient_answer(reply_language)

    system = legal_system_prompt(reply_language)
    prompt = build_answer_prompt(query, chunks, reply_language, history)

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

    answer = repair_answer(complete(prompt), chunks)
    problems = answer_problems(answer, chunks)
    if problems:
        rewritten = complete(
            prompt
            + "\n\nThe previous answer used "
            + ", ".join(problems)
            + ", which are not in the legal texts. Rewrite the full answer without those. Name only provisions from the list above, and do not name a court or office the texts do not name.\nAnswer:"
        )
        if rewritten and len(answer_problems(rewritten, chunks)) <= len(problems):
            answer = rewritten
        problems = answer_problems(answer, chunks)
        if problems:
            answer = append_citation_note(answer, problems, reply_language)

    if not answer:
        answer = insufficient_answer(reply_language)
    if voice:
        answer = summarize_for_voice(answer, reply_language)
    logging.info("RAG query completed in %.2fs", time.time() - start_time)
    return answer
