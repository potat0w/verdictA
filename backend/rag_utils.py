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
CONTEXT_CHAR_BUDGET = 2000
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


def answer_with_rag(query: str, language: Optional[str] = None) -> str:
    from groq_client import generate_text

    _lazy_init_models()

    start_time = time.time()

    top_chunks = retrieve_chunks(query, top_k=3, language=language)

    context_parts = []
    for c in top_chunks:
        content = c["content"]
        if len(content) > CONTEXT_CHAR_BUDGET:
            content = content[:CONTEXT_CHAR_BUDGET] + "..."
        block = f"{c['chunk_type'].capitalize()} from {c['act_title']}:\n{content}"
        flags = c.get("legal_status_flags") or []
        if flags:
            block += f"\nLegal status notes: {', '.join(flags)}"
        context_parts.append(block)

    context = "\n\n".join(context_parts)

    prompt = f"""You are VerdictAI, a guide to the Constitution and laws of Bangladesh.
Answer ONLY from the Bangladesh legal texts below.
Do not use or mention United States, UK, or any other foreign law.
If the texts are not enough, say briefly what is missing and stay within Bangladesh constitutional principles.
Answer in the same language as the question (Bangla or English). Be concise and name article numbers when the texts include them.

Legal texts:
{context}

Question: {query}
Answer:"""

    answer = generate_text(prompt)

    total_time = time.time() - start_time
    logging.info(f"RAG query completed in {total_time:.2f}s")

    return answer
