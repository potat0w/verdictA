import os
import logging
import time
from typing import List, Dict

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


def retrieve_chunks(query: str, top_k: int = 5) -> List[Dict]:
    import numpy as np

    _lazy_init_models()
    query_vec = np.array(list(_embed_model.embed([query])), dtype="float32")
    _, indices = _index.search(query_vec, top_k)
    return [_metadata[i] for i in indices[0]]


def answer_with_rag(query: str) -> str:
    from groq_client import generate_text

    _lazy_init_models()

    start_time = time.time()

    top_chunks = retrieve_chunks(query, top_k=3)

    context_parts = []
    for c in top_chunks:
        content = c["content"]
        if len(content) > 1000:
            content = content[:1000] + "..."
        context_parts.append(
            f"{c['chunk_type'].capitalize()} from {c['act_title']}:\n{content}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""Using these legal texts, answer concisely:

{context}

Question: {query}
Answer:"""

    answer = generate_text(prompt)

    total_time = time.time() - start_time
    logging.info(f"RAG query completed in {total_time:.2f}s")

    return answer
