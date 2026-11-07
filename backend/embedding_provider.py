"""Query and document embeddings.

Live queries may use Voyage (voyage-4 → verdictai-voyage-4), a local TEI
server, in-process MiniLM, or Hugging Face. The active provider's model and
width must match the Qdrant collection being searched.
MiniLM indexing still uses STORED_* below. This module does not write to Qdrant.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any
from urllib.parse import urlparse

import httpx

STORED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
STORED_DIMENSION = 384
STORED_DISTANCE = "Cosine"
VOYAGE_DEFAULT_MODEL = "voyage-4"
VOYAGE_DEFAULT_DIMENSION = 1024
TEI_MAX_BATCH = 32
MAX_ATTEMPTS = 5
MAX_RETRY_WAIT_SECONDS = 8.0

_http: httpx.Client | None = None
_voyage_client: Any = None
_voyage_lock = threading.Lock()


class EmbeddingError(RuntimeError):
    """The selected embedding provider failed. Callers must not switch providers."""


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv()


def _pause(seconds: float) -> None:
    time.sleep(seconds)


def _tei_host_is_local() -> bool:
    base = os.getenv("TEI_BASE_URL", "http://localhost:8080").strip()
    host = (urlparse(base).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def provider_name() -> str:
    """The embedding host for this process.

    EMBEDDING_PROVIDER=voyage uses Voyage for live query vectors.
    A machine with Docker sets EMBEDDING_PROVIDER=tei. Render cannot reach a
    localhost TEI server, so it uses the same MiniLM model inside this process.
    A public TEI_BASE_URL on Render stays on tei.
    """
    _load_env()
    raw = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    if not raw:
        raw = "fastembed" if os.getenv("RENDER", "").strip() else "tei"
    if raw == "hf":
        return "huggingface"
    if raw == "local":
        return "fastembed"
    if (
        raw == "tei"
        and os.getenv("RENDER", "").strip()
        and _tei_host_is_local()
    ):
        logging.warning(
            "TEI_BASE_URL is local, so Render uses the in-process MiniLM model"
        )
        return "fastembed"
    if raw in ("tei", "fastembed", "huggingface", "voyage"):
        return raw
    raise EmbeddingError(
        "EMBEDDING_PROVIDER must be 'voyage', 'tei', 'fastembed', or 'huggingface'"
    )


def voyage_model() -> str:
    _load_env()
    model = os.getenv("VOYAGE_MODEL", VOYAGE_DEFAULT_MODEL).strip()
    if not model:
        raise EmbeddingError("VOYAGE_MODEL is empty")
    return model


def voyage_dimension() -> int:
    _load_env()
    raw = os.getenv("VOYAGE_DIMENSIONS", str(VOYAGE_DEFAULT_DIMENSION)).strip()
    try:
        width = int(raw)
    except ValueError as exc:
        raise EmbeddingError("VOYAGE_DIMENSIONS must be an integer") from exc
    if width <= 0:
        raise EmbeddingError("VOYAGE_DIMENSIONS must be greater than zero")
    return width


def _minilm_model() -> str:
    _load_env()
    model = os.getenv("EMBEDDING_MODEL", STORED_MODEL).strip()
    if not model:
        raise EmbeddingError("EMBEDDING_MODEL is empty")
    return model


def _minilm_dimension() -> int:
    _load_env()
    raw = os.getenv("EMBEDDING_DIMENSION", str(STORED_DIMENSION)).strip()
    try:
        width = int(raw)
    except ValueError as exc:
        raise EmbeddingError("EMBEDDING_DIMENSION must be an integer") from exc
    if width <= 0:
        raise EmbeddingError("EMBEDDING_DIMENSION must be greater than zero")
    return width


def model_name() -> str:
    """Model for the active live query provider."""
    if provider_name() == "voyage":
        return voyage_model()
    return _minilm_model()


def dimension() -> int:
    """Vector width for the active live query provider."""
    if provider_name() == "voyage":
        return voyage_dimension()
    return _minilm_dimension()


def require_stored_configuration(provider: str | None = None) -> tuple[str, int]:
    """Refuse a model or width that is not the one stored for this provider."""
    selected = provider or provider_name()
    if selected == "voyage":
        return voyage_model(), voyage_dimension()
    model = _minilm_model()
    width = _minilm_dimension()
    if model != STORED_MODEL or width != STORED_DIMENSION:
        raise EmbeddingError(
            f"Refusing to embed with {model} at {width} dimensions. "
            f"The collection stores {STORED_MODEL} at {STORED_DIMENSION} dimensions "
            f"with {STORED_DISTANCE} distance. Re-index into a new collection before "
            "changing the model or dimension."
        )
    return model, width


def tei_embed_url() -> str:
    _load_env()
    base = os.getenv("TEI_BASE_URL", "http://localhost:8080").strip().rstrip("/")
    if not base:
        raise EmbeddingError("TEI_BASE_URL is empty")
    if base.endswith("/embed"):
        return base
    return f"{base}/embed"


def _hf_token() -> str:
    _load_env()
    token = os.getenv("HF_API_TOKEN", "").strip() or os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise EmbeddingError("HF_API_TOKEN is not set")
    return token


def huggingface_embed_url(model: str | None = None) -> str:
    _load_env()
    base = os.getenv(
        "HF_INFERENCE_URL",
        "https://router.huggingface.co/hf-inference",
    ).strip().rstrip("/")
    if not base:
        raise EmbeddingError("HF_INFERENCE_URL is empty")
    return f"{base}/models/{model or _minilm_model()}/pipeline/feature-extraction"


def _redact(text: str) -> str:
    for name in ("HF_API_TOKEN", "HF_TOKEN"):
        token = os.getenv(name, "").strip()
        if token and token in text:
            text = text.replace(token, "[redacted]")
    return text[:300]


def _http_client() -> httpx.Client:
    global _http
    if _http is None:
        timeout = httpx.Timeout(120.0, connect=10.0)
        _http = httpx.Client(timeout=timeout)
    return _http


def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
    if response is not None:
        raw = response.headers.get("retry-after")
        if raw:
            try:
                delay = float(raw)
            except ValueError:
                delay = 0.0
            if 0 <= delay <= MAX_RETRY_WAIT_SECONDS:
                return delay
    return min(0.5 * (2**attempt), MAX_RETRY_WAIT_SECONDS)


def _post_json(url: str, body: dict, headers: dict) -> object:
    last_status = None
    for attempt in range(MAX_ATTEMPTS):
        response = None
        try:
            response = _http_client().post(url, json=body, headers=headers)
            last_status = response.status_code
            if response.status_code == 200:
                return response.json()
            retry = response.status_code in (429, 500, 502, 503, 504)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            retry = True
            logging.warning(
                "Embedding request failed attempt=%s error=%s",
                attempt + 1,
                type(exc).__name__,
            )
        if retry and attempt + 1 < MAX_ATTEMPTS:
            delay = _retry_delay(response, attempt)
            logging.warning(
                "Embedding retry attempt=%s status=%s wait=%.1fs texts=%s",
                attempt + 1,
                last_status,
                delay,
                len(body.get("inputs") or []),
            )
            _pause(delay)
            continue
        detail = ""
        if response is not None:
            detail = _redact(response.text)
        raise EmbeddingError(
            f"Embedding request failed status={last_status} detail={detail}"
        )
    raise EmbeddingError("Embedding request failed")


def _vector(raw: object, width: int) -> list[float]:
    if not isinstance(raw, list) or not raw or isinstance(raw[0], list):
        raise EmbeddingError(
            f"Expected a {width}-dimensional embedding, received a nested or empty value"
        )
    vector: list[float] = []
    for value in raw:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise EmbeddingError("Embedding contained a non-numeric value") from exc
        if number != number or number in (float("inf"), float("-inf")):
            raise EmbeddingError("Embedding contained a non-finite value")
        vector.append(number)
    if len(vector) != width:
        raise EmbeddingError(
            f"Expected {width} dimensions, received {len(vector)}"
        )
    return vector


def parse_embeddings(payload: object, count: int, width: int) -> list[list[float]]:
    """Accept the TEI list body and the Hugging Face feature-extraction body."""
    if isinstance(payload, dict):
        nested = payload.get("embeddings")
        if nested is None and isinstance(payload.get("data"), list):
            nested = [
                row.get("embedding") if isinstance(row, dict) else row
                for row in payload["data"]
            ]
        payload = nested
    if not isinstance(payload, list):
        raise EmbeddingError("Embedding service returned an unexpected response")
    if count == 1 and payload and not isinstance(payload[0], list):
        return [_vector(payload, width)]
    if len(payload) != count:
        raise EmbeddingError(
            f"Embedding service returned {len(payload)} vectors for {count} texts"
        )
    return [_vector(row, width) for row in payload]


_local_model: Any = None
_local_lock = threading.Lock()


def _local_vectors(texts: list[str]) -> list[list[float]]:
    """Same MiniLM weights as the TEI index, computed in this process."""
    global _local_model
    model, width = require_stored_configuration("fastembed")
    with _local_lock:
        if _local_model is None:
            from fastembed import TextEmbedding

            logging.info("Loading local embedding model %s", model)
            _local_model = TextEmbedding(model_name=model)
        rows = list(_local_model.embed(texts))
    if len(rows) != len(texts):
        raise EmbeddingError("Local embedding model returned the wrong number of vectors")
    return [_vector([float(value) for value in row], width) for row in rows]


def preload_local_model() -> None:
    """Download the local model at startup. Voyage, TEI, and Hugging Face skip this."""
    if provider_name() != "fastembed":
        return
    _local_vectors(["warmup"])


def _voyage_api_key() -> str:
    _load_env()
    key = os.getenv("VOYAGE_API_KEY", "").strip()
    if not key:
        raise EmbeddingError("VOYAGE_API_KEY is not set")
    return key


def _get_voyage_client() -> Any:
    global _voyage_client
    with _voyage_lock:
        if _voyage_client is None:
            try:
                import voyageai
            except ImportError as exc:
                raise EmbeddingError(
                    "voyageai is not installed. Run: pip install voyageai"
                ) from exc
            _voyage_client = voyageai.Client(api_key=_voyage_api_key())
        return _voyage_client


def _voyage_embed(texts: list[str], *, input_type: str) -> list[list[float]]:
    """Voyage vectors. Index used input_type=document; queries use input_type=query."""
    model, width = require_stored_configuration("voyage")
    logging.info(
        "Embedding batch provider=voyage model=%s input_type=%s texts=%s",
        model,
        input_type,
        len(texts),
    )
    last_error: Exception | None = None
    delay = 0.5
    for attempt in range(MAX_ATTEMPTS):
        try:
            result = _get_voyage_client().embed(
                texts=texts,
                model=model,
                input_type=input_type,
                output_dimension=width,
            )
            rows = list(result.embeddings)
            if len(rows) != len(texts):
                raise EmbeddingError(
                    f"Voyage returned {len(rows)} vectors for {len(texts)} texts"
                )
            return [_vector(row, width) for row in rows]
        except EmbeddingError:
            raise
        except Exception as exc:
            last_error = exc
            name = type(exc).__name__
            retry = name in {"RateLimitError", "ServiceUnavailableError", "Timeout"} or (
                "429" in str(exc) or "rate" in str(exc).lower()
            )
            if not retry or attempt + 1 >= MAX_ATTEMPTS:
                break
            logging.warning(
                "Voyage embed retry attempt=%s error=%s wait=%.1fs",
                attempt + 1,
                name,
                delay,
            )
            _pause(delay)
            delay = min(delay * 2, MAX_RETRY_WAIT_SECONDS)
    raise EmbeddingError(
        f"Voyage embed failed: {type(last_error).__name__ if last_error else 'unknown'}"
    ) from last_error


def _embed_batch(texts: list[str], provider: str) -> list[list[float]]:
    if provider == "voyage":
        return _voyage_embed(texts, input_type="document")
    model, width = require_stored_configuration(provider)
    if provider == "fastembed":
        logging.info(
            "Embedding batch provider=fastembed model=%s texts=%s",
            model,
            len(texts),
        )
        return _local_vectors(texts)
    if provider == "tei":
        url = tei_embed_url()
        headers = {"Content-Type": "application/json"}
        body = {"inputs": texts, "truncate": True}
    elif provider == "huggingface":
        url = huggingface_embed_url(model)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_hf_token()}",
        }
        body = {"inputs": texts, "truncate": True, "normalize": True}
    else:
        raise EmbeddingError(
            "EMBEDDING_PROVIDER must be 'voyage', 'tei', 'fastembed', or 'huggingface'"
        )
    logging.info(
        "Embedding batch provider=%s model=%s texts=%s",
        provider,
        model,
        len(texts),
    )
    try:
        payload = _post_json(url, body, headers)
    except EmbeddingError as exc:
        message = str(exc)
        rejected = any(token in message for token in ("status=400", "status=413", "status=422"))
        if rejected and len(texts) > 1:
            middle = len(texts) // 2
            logging.warning("Splitting embedding batch of %s after the server rejected it", len(texts))
            return _embed_batch(texts[:middle], provider) + _embed_batch(texts[middle:], provider)
        raise
    return parse_embeddings(payload, len(texts), width)


def embed_texts(texts: list[str], provider: str | None = None) -> list[list[float]]:
    """Embed a batch. provider overrides EMBEDDING_PROVIDER for this call only."""
    selected = provider or provider_name()
    if selected not in ("tei", "fastembed", "huggingface", "voyage"):
        raise EmbeddingError(
            "EMBEDDING_PROVIDER must be 'voyage', 'tei', 'fastembed', or 'huggingface'"
        )
    if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
        raise EmbeddingError("Embeddings require non-empty text")
    vectors: list[list[float]] = []
    step = TEI_MAX_BATCH if selected == "tei" else TEI_MAX_BATCH
    for start in range(0, len(texts), step):
        vectors.extend(_embed_batch(texts[start : start + step], selected))
    return vectors


def embed_query(text: str) -> list[float]:
    """One query vector from the configured provider. This does not query Qdrant."""
    if not isinstance(text, str) or not text.strip():
        raise EmbeddingError("Query text is empty")
    if provider_name() == "voyage":
        return _voyage_embed([text], input_type="query")[0]
    return embed_texts([text])[0]
