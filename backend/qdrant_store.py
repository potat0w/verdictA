"""Semantic search against the serving Qdrant collection.

MiniLM indexing still writes to COLLECTION_NAME (verdictai, 384-d).
Live queries with EMBEDDING_PROVIDER=voyage read VOYAGE_COLLECTION
(verdictai-voyage-4, 1024-d). Point ids are the row numbers from the index build.
"""

from __future__ import annotations

import logging
import os
import threading

COLLECTION_NAME = "verdictai"
VECTOR_SIZE = 384
VOYAGE_DEFAULT_COLLECTION = "verdictai-voyage-4"
UPLOAD_BATCH = 128

_client = None
_client_lock = threading.Lock()
_payload_indexes_ready = False
_payload_indexes_collection: str | None = None
_query_ready = False
_query_ready_collection: str | None = None


def qdrant_configured() -> bool:
    from dotenv import load_dotenv

    load_dotenv()
    return bool(os.getenv("QDRANT_URL", "").strip())


def active_collection() -> str:
    """Qdrant collection used for live search and payload reads."""
    from dotenv import load_dotenv

    from embedding_provider import provider_name

    load_dotenv()
    if provider_name() == "voyage":
        name = os.getenv("VOYAGE_COLLECTION", VOYAGE_DEFAULT_COLLECTION).strip()
        if not name:
            raise RuntimeError("VOYAGE_COLLECTION is empty")
        if name == COLLECTION_NAME:
            raise RuntimeError(
                f"VOYAGE_COLLECTION must not be {COLLECTION_NAME}. "
                f"Use {VOYAGE_DEFAULT_COLLECTION}."
            )
        return name
    return COLLECTION_NAME


def active_vector_size() -> int:
    from embedding_provider import dimension, provider_name

    if provider_name() == "voyage":
        return dimension()
    return VECTOR_SIZE


def active_stored_model() -> str:
    from embedding_provider import STORED_MODEL, model_name, provider_name

    if provider_name() == "voyage":
        return model_name()
    return STORED_MODEL


def get_client():
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            from dotenv import load_dotenv
            from qdrant_client import QdrantClient

            load_dotenv()
            url = os.getenv("QDRANT_URL", "").strip()
            if not url:
                raise RuntimeError("QDRANT_URL is not set")
            api_key = os.getenv("QDRANT_API_KEY", "").strip()
            logging.getLogger("httpx").setLevel(logging.WARNING)
            _client = QdrantClient(url=url, api_key=api_key or None, timeout=120)
    return _client


def _vector_config(info) -> tuple[int, object]:
    vectors = info.config.params.vectors
    if hasattr(vectors, "size"):
        return int(vectors.size), vectors.distance
    first = next(iter(vectors.values()))
    return int(first.size), first.distance


def _distance_name(distance) -> str:
    value = getattr(distance, "value", None)
    if value is None:
        value = getattr(distance, "name", None)
    if value is None:
        value = distance
    return str(value).split(".")[-1].lower()


def _is_cosine(distance) -> bool:
    return _distance_name(distance) == "cosine"


def payload_from_chunk(chunk: dict) -> dict:
    """JSON payload for one metadata row. Passage text stays with the vector."""
    payload: dict = {}
    for key, value in chunk.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            payload[key] = value
        else:
            payload[key] = str(value)
    return payload


def ensure_payload_indexes() -> None:
    """Keyword indexes so a collection filter does not scan every point."""
    global _payload_indexes_ready, _payload_indexes_collection
    name = active_collection()
    if _payload_indexes_ready and _payload_indexes_collection == name:
        return
    client = get_client()
    for field in ("collection", "language"):
        try:
            client.create_payload_index(
                collection_name=name,
                field_name=field,
                field_schema="keyword",
            )
        except Exception as exc:
            message = str(exc).lower()
            if "already exists" not in message and "already_exists" not in message:
                raise
    _payload_indexes_ready = True
    _payload_indexes_collection = name


def _collection_filter(collection: str, language: str | None = None):
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    must = [FieldCondition(key="collection", match=MatchValue(value=collection))]
    if language:
        must.append(FieldCondition(key="language", match=MatchValue(value=language)))
    return Filter(must=must)


def iter_payloads(collection: str, language: str | None = None):
    """Yield one collection's passages. This never scrolls the whole vector set."""
    ensure_payload_indexes()
    client = get_client()
    name = active_collection()
    if not client.collection_exists(name):
        raise FileNotFoundError(
            f"Qdrant collection {name} was not found. "
            "Run build_voyage_index.py (voyage) or build_index.py (MiniLM)."
        )
    offset = None
    query_filter = _collection_filter(collection, language)
    while True:
        points, offset = client.scroll(
            collection_name=name,
            scroll_filter=query_filter,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            yield int(point.id), dict(point.payload or {})
        if offset is None:
            break


def fetch_payloads(row_ids: list[int]) -> dict[int, dict]:
    """Passage text for specific point ids. Missing local metadata uses this."""
    if not row_ids:
        return {}
    name = active_collection()
    points = get_client().retrieve(
        collection_name=name,
        ids=row_ids,
        with_payload=True,
        with_vectors=False,
    )
    found: dict[int, dict] = {}
    for point in points:
        payload = dict(point.payload or {})
        if "content" not in payload:
            raise FileNotFoundError(
                "Qdrant payloads have no passage text. Run build_index.py."
            )
        found[int(point.id)] = payload
    return found


def _reset_ready_flags() -> None:
    global _payload_indexes_ready, _payload_indexes_collection, _query_ready
    global _query_ready_collection
    _payload_indexes_ready = False
    _payload_indexes_collection = None
    _query_ready = False
    _query_ready_collection = None


def _create_serving_collection() -> None:
    from qdrant_client.models import Distance, VectorParams

    _reset_ready_flags()
    get_client().create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    ensure_payload_indexes()
    logging.info(
        "Created Qdrant collection %s size=%s distance=cosine",
        COLLECTION_NAME,
        VECTOR_SIZE,
    )


def _replace_serving_collection(reason: str) -> None:
    """Delete only the serving collection, then create an empty cosine collection."""
    client = get_client()
    names = [item.name for item in client.get_collections().collections]
    logging.info("Qdrant collections before replace: %s", names)
    if COLLECTION_NAME not in names:
        _create_serving_collection()
        return
    info = client.get_collection(COLLECTION_NAME)
    size, distance = _vector_config(info)
    logging.info(
        "Replacing collection %s size=%s distance=%s points=%s reason=%s",
        COLLECTION_NAME,
        size,
        _distance_name(distance),
        info.points_count,
        reason,
    )
    _reset_ready_flags()
    client.delete_collection(COLLECTION_NAME)
    _create_serving_collection()


def _scroll_index_stamp(expected_chunk_ids: list[str]) -> set[int] | None:
    """Ids already stored for this dataset. None means the points must be rebuilt."""
    from embedding_provider import STORED_MODEL

    client = get_client()
    found: dict[int, dict] = {}
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=256,
            offset=offset,
            with_payload=["chunk_id", "embedding_model"],
            with_vectors=False,
        )
        for point in points:
            found[int(point.id)] = dict(point.payload or {})
        if offset is None:
            break
    total = len(expected_chunk_ids)
    for point_id, payload in found.items():
        if payload.get("embedding_model") != STORED_MODEL:
            return None
        if point_id < 0 or point_id >= total:
            return None
        if payload.get("chunk_id") != expected_chunk_ids[point_id]:
            return None
    return set(found)


def ensure_serving_collection(chunk_ids: list[str]) -> set[int]:
    """Create the cosine collection. Return point ids that already match this build."""
    client = get_client()
    names = [item.name for item in client.get_collections().collections]
    logging.info("Qdrant collections: %s", names)
    if COLLECTION_NAME not in names:
        _create_serving_collection()
        return set()
    info = client.get_collection(COLLECTION_NAME)
    size, distance = _vector_config(info)
    if size != VECTOR_SIZE or not _is_cosine(distance):
        _replace_serving_collection(
            f"configuration was size={size} distance={_distance_name(distance)}"
        )
        return set()
    existing = _scroll_index_stamp(chunk_ids)
    if existing is None:
        _replace_serving_collection("points do not match the current dataset and model")
        return set()
    logging.info(
        "Resuming collection %s existing=%s expected=%s",
        COLLECTION_NAME,
        len(existing),
        len(chunk_ids),
    )
    ensure_payload_indexes()
    return existing


def upsert_chunk_batch(rows: list[tuple[int, dict, list[float]]]) -> None:
    """Upsert one batch. The point id is the chunk row, so a retry replaces it."""
    import time

    from embedding_provider import STORED_MODEL
    from qdrant_client.models import PointStruct

    if not rows:
        return
    points = []
    for point_id, chunk, vector in rows:
        if len(vector) != VECTOR_SIZE:
            raise RuntimeError(
                f"Refusing to store a {len(vector)}-dimensional vector in {COLLECTION_NAME}"
            )
        payload = payload_from_chunk(chunk)
        payload["embedding_model"] = STORED_MODEL
        points.append(PointStruct(id=point_id, vector=vector, payload=payload))
    client = get_client()
    delay = 0.5
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
            return
        except Exception as exc:
            last_error = exc
            logging.warning(
                "Qdrant upsert retry attempt=%s error=%s points=%s",
                attempt + 1,
                type(exc).__name__,
                len(points),
            )
            if attempt == 4:
                break
            time.sleep(delay)
            delay = min(delay * 2, 8.0)
    raise RuntimeError("Qdrant upsert failed") from last_error


def point_count() -> int:
    counted = get_client().count(collection_name=active_collection(), exact=True)
    return int(counted.count)


def serving_status() -> dict:
    """Collection geometry and exact point count for the active query collection."""
    client = get_client()
    name = active_collection()
    if not client.collection_exists(name):
        raise FileNotFoundError(
            f"Qdrant collection {name} was not found. "
            "Run build_voyage_index.py (voyage) or build_index.py (MiniLM)."
        )
    info = client.get_collection(name)
    size, distance = _vector_config(info)
    return {
        "name": name,
        "size": size,
        "distance": _distance_name(distance),
        "points": point_count(),
    }


def assert_collection_ready(expected_points: int) -> None:
    """Fail when the collection is missing, the wrong shape, or short of rows."""
    status = serving_status()
    expected_size = active_vector_size()
    name = status["name"]
    if status["size"] != expected_size or status["distance"] != "cosine":
        raise RuntimeError(
            f"Qdrant collection {name} is size={status['size']} "
            f"distance={status['distance']}. Expected {expected_size} cosine."
        )
    if status["points"] != expected_points:
        raise FileNotFoundError(
            f"Qdrant collection {name} has {status['points']} vectors, "
            f"expected {expected_points}. Run the matching index build."
        )


def assert_query_ready(vector: list[float]) -> None:
    """Refuse a query vector that does not match the stored collection."""
    global _query_ready, _query_ready_collection

    name = active_collection()
    expected_size = active_vector_size()
    expected_model = active_stored_model()
    if len(vector) != expected_size:
        raise RuntimeError(
            f"Query embedding has {len(vector)} dimensions; "
            f"{name} stores {expected_size}."
        )
    if _query_ready and _query_ready_collection == name:
        return
    status = serving_status()
    if status["size"] != expected_size or status["distance"] != "cosine":
        raise RuntimeError(
            f"Refusing to search {name}: size={status['size']} "
            f"distance={status['distance']}. Expected {expected_size} cosine vectors "
            f"from {expected_model}."
        )
    sample = get_client().retrieve(
        collection_name=name,
        ids=[0],
        with_payload=True,
        with_vectors=False,
    )
    model = (sample[0].payload or {}).get("embedding_model") if sample else None
    if model != expected_model:
        raise RuntimeError(
            f"Refusing to search {name}: stored model is {model!r}, "
            f"expected {expected_model}."
        )
    _query_ready = True
    _query_ready_collection = name


def search_collection_scored(
    vector: list[float],
    collection: str,
    k: int,
    language: str | None = None,
) -> list[tuple[int, float]]:
    """Nearest point ids and cosine scores. Same filter and limit as search_collection.

    language narrows other-acts (and any multi-language collection). Constitution
    partitions are already language-split by collection name.
    """
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    if k <= 0:
        return []
    assert_query_ready(vector)
    ensure_payload_indexes()
    name = active_collection()
    must = [FieldCondition(key="collection", match=MatchValue(value=collection))]
    if language:
        must.append(FieldCondition(key="language", match=MatchValue(value=language)))
    found = get_client().query_points(
        collection_name=name,
        query=vector,
        query_filter=Filter(must=must),
        limit=k,
        with_payload=False,
    )
    return [(int(point.id), float(point.score)) for point in found.points]


def search_collection(
    vector: list[float],
    collection: str,
    k: int,
    language: str | None = None,
) -> list[int]:
    """Nearest point ids inside one constitution or statute collection."""
    return [
        row_id
        for row_id, _score in search_collection_scored(
            vector, collection, k, language=language
        )
    ]


def upload_index(index_path: str, meta_path: str) -> int:
    """The FAISS copy path is retired. It would write the previous model's vectors."""
    del index_path, meta_path
    raise RuntimeError(
        "Refusing to copy faiss.index into Qdrant. "
        "Run build_index.py to embed with the local TEI server."
    )
