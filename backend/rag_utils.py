import json
import os
import logging
import threading
import time
from typing import List, Dict, Optional
from legal_status import attach_legal_status_flags
from hybrid_search import BM25Index, bm25_document, fuse_hits, partition_ids

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
_index = None
_metadata: List[Dict] | None = None
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
    if not os.path.exists(INDEX_META_PATH):
        return
    with open(INDEX_META_PATH, encoding="utf-8") as handle:
        loaded = json.load(handle)
    _index_meta = {
        "model_name": loaded.get("model_name") or DEFAULT_EMBED_MODEL,
        "query_prefix": loaded.get("query_prefix") or "",
        "passage_prefix": loaded.get("passage_prefix") or "",
    }
    EMBED_MODEL_NAME = _index_meta["model_name"]


def _lazy_init_models() -> None:
    global _embed_model, _index, _metadata, _models_initialized, _init_start_time

    if _models_initialized:
        return

    with _init_lock:
        if _models_initialized:
            return

        if _init_start_time is None:
            _init_start_time = time.time()
            logging.info("Starting model initialization...")

        try:
            import pickle
            import faiss
            from fastembed import TextEmbedding
            from groq_client import get_groq_api_key, get_groq_model

            _load_index_meta()

            if _index is None:
                if not os.path.exists(INDEX_PATH):
                    raise FileNotFoundError(f"FAISS index not found at {INDEX_PATH}")
                logging.info("Loading FAISS index (memory-mapped)...")
                _index = faiss.read_index(
                    INDEX_PATH, faiss.IO_FLAG_MMAP | faiss.IO_FLAG_READ_ONLY
                )
                logging.info("FAISS index loaded")

            if _metadata is None:
                if not os.path.exists(META_PATH):
                    raise FileNotFoundError(f"Chunk metadata not found at {META_PATH}")
                logging.info("Loading metadata...")
                with open(META_PATH, "rb") as handle:
                    _metadata = pickle.load(handle)
                logging.info("Metadata loaded (%s chunks)", len(_metadata))

            if _embed_model is None:
                logging.info("Loading embedding model %s", EMBED_MODEL_NAME)
                _embed_model = TextEmbedding(model_name=EMBED_MODEL_NAME)
                logging.info("Embedding model loaded")

            get_groq_api_key()
            get_groq_model()
            logging.info("Groq client configured")

            _models_initialized = True
            init_time = time.time() - _init_start_time
            logging.info("All models initialized in %.2f seconds", init_time)

        except Exception as exc:
            logging.error("Model initialization failed: %s", type(exc).__name__)
            raise


def _bm25_for(cache_key: str, row_ids: list[int]) -> BM25Index:
    cached = _bm25_cache.get(cache_key)
    if cached is not None:
        return cached
    index = BM25Index((row_id, bm25_document(_metadata[row_id])) for row_id in row_ids)
    _bm25_cache[cache_key] = index
    return index


def _semantic_ids(query: str, row_ids: list[int], k: int) -> list[int]:
    import numpy as np
    import faiss

    prefixed = f"{_index_meta.get('query_prefix') or ''}{query}"
    query_vec = np.array(list(_embed_model.embed([prefixed])), dtype="float32")
    id_array = np.array(row_ids, dtype="int64")
    params = faiss.SearchParameters()
    params.sel = faiss.IDSelectorBatch(id_array)
    _scores, found = _index.search(query_vec, k, params=params)
    hits: list[int] = []
    allowed = set(row_ids)
    for row_id in found[0].tolist():
        if row_id < 0 or row_id not in allowed:
            continue
        hits.append(int(row_id))
    return hits


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    language: Optional[str] = None,
) -> List[Dict]:
    """Hybrid search inside one language partition.

    Signature is unchanged. A language value searches that constitution
    collection before any ranking, then fuses cosine and BM25.
    """
    _lazy_init_models()
    if top_k <= 0 or not (query or "").strip():
        return []

    row_ids = partition_ids(_metadata, language)
    if not row_ids:
        return []

    cache_key = language or "all"
    semantic_k = min(max(top_k * 4, SEMANTIC_CANDIDATES), len(row_ids))
    lexical_k = min(max(top_k * 4, LEXICAL_CANDIDATES), len(row_ids))
    semantic = _semantic_ids(query, row_ids, semantic_k)
    lexical = _bm25_for(cache_key, row_ids).rank(query, lexical_k)
    chosen = fuse_hits(query, row_ids, semantic, lexical, _metadata, top_k)
    logging.info(
        "hybrid retrieve language=%s partition=%s returned=%s",
        language,
        len(row_ids),
        len(chosen),
    )
    return [attach_legal_status_flags(_metadata[row_id]) for row_id in chosen]


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
    """Stored parts of one constitution article, capped so a long article cannot crowd out the others."""
    key = chunk.get("article_key")
    collection = chunk.get("collection")
    if not key or not str(collection or "").startswith("constitution") or not _metadata:
        return [chunk]
    parts = [
        row
        for row in _metadata
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
    from answer_quality import (
        prefer_general_statutes,
        select_relevant_chunks,
        statutes_about_the_issue,
    )

    if language not in ("en", "bn") or not _metadata:
        return []
    row_ids = [
        index
        for index, chunk in enumerate(_metadata)
        if chunk.get("collection") == "other-acts" and chunk.get("language") == language
    ]
    if not row_ids:
        return []
    ranked_ids = _bm25_for(f"other-acts-{language}", row_ids).rank(query, 40)
    ranked = [attach_legal_status_flags(_metadata[row_id]) for row_id in ranked_ids]
    matched = select_relevant_chunks(query, ranked, limit=12)
    matched = statutes_about_the_issue(query, matched)
    return prefer_general_statutes(query, matched)[:3]


def _answer_chunks(query: str, language: Optional[str], history) -> list[dict]:
    from answer_quality import (
        on_the_same_issue,
        retrieval_language,
        retrieval_text,
        select_relevant_chunks,
    )

    search_text = retrieval_text(query, history)
    search_language = retrieval_language(query, language)
    ranked = retrieve_chunks(search_text, top_k=20, language=search_language)
    selected = select_relevant_chunks(search_text, ranked)
    constitution: list[dict] = []
    seen: set[str] = set()
    for chunk in selected:
        for part in _same_article_parts(chunk):
            identity = str(part.get("chunk_id") or id(part))
            if identity in seen:
                continue
            seen.add(identity)
            constitution.append(attach_legal_status_flags(part))
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
