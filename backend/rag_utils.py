import os
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from groq_client import generate_text, get_groq_api_key, get_groq_model
from typing import List, Dict
import logging
import time

# Resolve embeddings directory relative to this file to avoid cwd issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBED_DIR = os.path.join(BASE_DIR, "embeddings")
INDEX_PATH = os.path.join(EMBED_DIR, "faiss.index")
META_PATH = os.path.join(EMBED_DIR, "chunk_metadata.pkl")

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
        if _embed_model is None:
            logging.info("Loading sentence transformer model...")
            _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            logging.info("Sentence transformer loaded")
            
        if _index is None:
            if not os.path.exists(INDEX_PATH):
                raise FileNotFoundError(f"FAISS index not found at {INDEX_PATH}")
            logging.info("Loading FAISS index...")
            _index = faiss.read_index(INDEX_PATH)
            logging.info("FAISS index loaded")
            
        if _metadata is None:
            if not os.path.exists(META_PATH):
                raise FileNotFoundError(f"Chunk metadata not found at {META_PATH}")
            logging.info("Loading metadata...")
            with open(META_PATH, "rb") as f:
                _metadata = pickle.load(f)
            logging.info("Metadata loaded")
            
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
    _lazy_init_models()
    query_vec = _embed_model.encode([query]).astype("float32")
    D, I = _index.search(query_vec, top_k)
    return [_metadata[i] for i in I[0]]


def answer_with_rag(query: str) -> str:
    _lazy_init_models()
    
    # Start timing for performance monitoring
    start_time = time.time()
    
    top_chunks = retrieve_chunks(query, top_k=3)  # Reduced from 5 to 3 for speed
    
    # Create more concise context
    context_parts = []
    for c in top_chunks:
        # Truncate very long content to speed up processing
        content = c['content']
        if len(content) > 1000:
            content = content[:1000] + "..."
        context_parts.append(f"{c['chunk_type'].capitalize()} from {c['act_title']}:\n{content}")
    
    context = "\n\n".join(context_parts)

    # More concise prompt
    prompt = f"""Using these legal texts, answer concisely:

{context}

Question: {query}
Answer:"""

    answer = generate_text(prompt)

    total_time = time.time() - start_time
    logging.info(f"RAG query completed in {total_time:.2f}s")

    return answer
