import os
import logging
import time
from typing import List, Dict, Optional
from language_filter import filter_chunks_by_language
from legal_status import attach_legal_status_flags

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBED_DIR = os.path.join(BASE_DIR, "embeddings")
INDEX_PATH = os.path.join(EMBED_DIR, "faiss.index")
META_PATH = os.path.join(EMBED_DIR, "chunk_metadata.pkl")
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_embed_model = None
_index = None
_metadata: List[Dict] | None = None
_models_initialized = False
_init_start_time = None


def _lazy_init_models() -> None:
    global _embed_model, _index, _metadata, _models_initialized, _init_start_time

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
            with open(META_PATH, "rb") as f:
                _metadata = pickle.load(f)
            logging.info("Metadata loaded")

        if _embed_model is None:
            logging.info("Loading embedding model...")
            _embed_model = TextEmbedding(model_name=EMBED_MODEL_NAME)
            logging.info("Embedding model loaded")

        get_groq_api_key()
        get_groq_model()
        logging.info("Groq client configured")

        _models_initialized = True
        init_time = time.time() - _init_start_time
        logging.info(f"All models initialized in {init_time:.2f} seconds")

    except Exception as e:
        logging.error(f"Model initialization failed: {e}")
        raise


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    language: Optional[str] = None,
) -> List[Dict]:
    import numpy as np

    _lazy_init_models()
    query_vec = np.array(list(_embed_model.embed([query])), dtype="float32")

    search_k = top_k
    if language is not None:
        search_k = min(top_k * 5, len(_metadata))

    _, indices = _index.search(query_vec, search_k)

    raw_chunks = []
    for index in indices[0]:
        if index < 0:
            continue
        raw_chunks.append(_metadata[index])

    if language is not None:
        raw_chunks = filter_chunks_by_language(raw_chunks, language, top_k)
    else:
        raw_chunks = raw_chunks[:top_k]

    return [attach_legal_status_flags(chunk) for chunk in raw_chunks]


def answer_with_rag(query: str, language: Optional[str] = None) -> str:
    from groq_client import generate_text

    _lazy_init_models()

    start_time = time.time()

    top_chunks = retrieve_chunks(query, top_k=3, language=language)

    context_parts = []
    for c in top_chunks:
        content = c["content"]
        if len(content) > 1000:
            content = content[:1000] + "..."
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
