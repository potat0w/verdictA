#!/usr/bin/env python3
"""Embed law chunks with Voyage and upsert into the NEW Qdrant collection only.

Does NOT touch the old MiniLM collection `verdictai`.
Target collection: `verdictai-voyage-4` (1024-d cosine), created separately.

Official limits (Voyage / MongoDB docs):
  Free trial (no payment method):  3 RPM, 10K TPM
  Tier 1 (card added, free tokens still apply): voyage-4 = 2000 RPM, 8M TPM
  Free tokens for voyage-4: first 200M per account
  Request caps for voyage-4: max 1000 texts / request, max ~320K tokens / request

Defaults assume Tier 1 (card on file): large batches, no artificial sleep.
429 responses still get exponential backoff.

Env (put in backend/.env — do not commit secrets):
  VOYAGE_API_KEY=...
  QDRANT_URL=...
  QDRANT_API_KEY=...
  VOYAGE_MODEL=voyage-4              # optional
  VOYAGE_DIMENSIONS=1024             # optional
  VOYAGE_COLLECTION=verdictai-voyage-4
  VOYAGE_BATCH_SIZE=128              # optional; max texts/request is 1000
  VOYAGE_SLEEP_SECONDS=0             # optional; only if you want pacing

Install once:
  pip install voyageai qdrant-client python-dotenv

Run from backend/ (venv on):
  python build_voyage_index.py --dry-run
  python build_voyage_index.py --limit 64
  python build_voyage_index.py
  # resume is automatic: already-stored matching points are skipped
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Any

from dotenv import load_dotenv

from build_index import build_chunks

log = logging.getLogger("build_voyage_index")

DEFAULT_MODEL = "voyage-4"
DEFAULT_DIMENSIONS = 1024
DEFAULT_COLLECTION = "verdictai-voyage-4"
OLD_COLLECTION = "verdictai"
UPLOAD_BATCH = 64
MAX_RETRIES = 8

# Tier 1 defaults (voyage-4: 2000 RPM / 8M TPM). No artificial pacing.
DEFAULT_BATCH = 128
DEFAULT_SLEEP = 0.0


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _rate_settings() -> tuple[int, float]:
    batch = DEFAULT_BATCH
    sleep = DEFAULT_SLEEP
    if _env("VOYAGE_BATCH_SIZE").isdigit():
        batch = max(1, min(1000, int(_env("VOYAGE_BATCH_SIZE"))))
    if _env("VOYAGE_SLEEP_SECONDS"):
        sleep = max(0.0, float(_env("VOYAGE_SLEEP_SECONDS")))
    return batch, sleep


def _require_env() -> dict[str, Any]:
    load_dotenv()
    key = _env("VOYAGE_API_KEY")
    url = _env("QDRANT_URL")
    if not key:
        raise SystemExit("Missing VOYAGE_API_KEY in .env")
    if not url:
        raise SystemExit("Missing QDRANT_URL in .env")
    model = _env("VOYAGE_MODEL", DEFAULT_MODEL)
    dimensions = int(_env("VOYAGE_DIMENSIONS", str(DEFAULT_DIMENSIONS)))
    collection = _env("VOYAGE_COLLECTION", DEFAULT_COLLECTION)
    if collection == OLD_COLLECTION:
        raise SystemExit(
            f"Refusing to write to {OLD_COLLECTION}. "
            f"Use {DEFAULT_COLLECTION} (or another new name)."
        )
    if dimensions != 1024 and model.startswith("voyage-4"):
        log.warning("voyage-4 default dim is 1024; you set %s", dimensions)
    return {
        "voyage_key": key,
        "qdrant_url": url,
        "qdrant_key": _env("QDRANT_API_KEY") or None,
        "model": model,
        "dimensions": dimensions,
        "collection": collection,
    }


def _qdrant(cfg: dict[str, Any]):
    from qdrant_client import QdrantClient

    return QdrantClient(
        url=cfg["qdrant_url"],
        api_key=cfg["qdrant_key"],
        timeout=120,
    )


def _assert_collection(client, name: str, dimensions: int) -> None:
    names = [c.name for c in client.get_collections().collections]
    if name not in names:
        raise SystemExit(
            f"Qdrant collection {name!r} not found. Create it first "
            f"(1024-d Cosine). Existing: {sorted(names)}"
        )
    if OLD_COLLECTION in names:
        old = client.get_collection(OLD_COLLECTION)
        log.info(
            "Leaving old collection alone: %s points=%s",
            OLD_COLLECTION,
            old.points_count,
        )
    info = client.get_collection(name)
    vectors = info.config.params.vectors
    size = int(vectors.size) if hasattr(vectors, "size") else None
    if size != dimensions:
        raise SystemExit(
            f"Collection {name} has size={size}, expected {dimensions}"
        )
    log.info(
        "Target collection %s points=%s size=%s",
        name,
        info.points_count,
        size,
    )


def _existing_matching_ids(
    client, collection: str, chunk_ids: list[str], model: str, dimensions: int
) -> set[int]:
    """Point ids already stored for this exact chunk list + model."""
    found: dict[int, dict] = {}
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=256,
            offset=offset,
            with_payload=["chunk_id", "embedding_model", "embedding_dimensions"],
            with_vectors=False,
        )
        for point in points:
            found[int(point.id)] = dict(point.payload or {})
        if offset is None:
            break

    total = len(chunk_ids)
    kept: set[int] = set()
    for point_id, payload in found.items():
        if point_id < 0 or point_id >= total:
            continue
        if payload.get("embedding_model") != model:
            continue
        if int(payload.get("embedding_dimensions") or 0) != dimensions:
            continue
        if payload.get("chunk_id") != chunk_ids[point_id]:
            continue
        kept.add(point_id)
    return kept


def _payload(chunk: dict, model: str, dimensions: int) -> dict:
    payload: dict = {}
    for key, value in chunk.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            payload[key] = value
        else:
            payload[key] = str(value)
    payload["embedding_model"] = model
    payload["embedding_dimensions"] = dimensions
    return payload


def _embed_batch(
    client,
    texts: list[str],
    model: str,
    dimensions: int,
) -> tuple[list[list[float]], int]:
    last_error: Exception | None = None
    delay = 2.0
    for attempt in range(MAX_RETRIES):
        try:
            result = client.embed(
                texts=texts,
                model=model,
                input_type="document",
                output_dimension=dimensions,
            )
            vectors = list(result.embeddings)
            if len(vectors) != len(texts):
                raise RuntimeError(
                    f"Voyage returned {len(vectors)} vectors for {len(texts)} texts"
                )
            for vector in vectors:
                if len(vector) != dimensions:
                    raise RuntimeError(
                        f"Expected {dimensions}-d vector, got {len(vector)}"
                    )
            usage = getattr(result, "total_tokens", None)
            if usage is None and getattr(result, "usage", None):
                usage = result.usage.total_tokens
            return vectors, int(usage or 0)
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            rate_limited = "429" in message or "rate" in message
            if attempt + 1 >= MAX_RETRIES or not rate_limited:
                raise
            wait = min(delay, 90.0)
            log.warning(
                "Voyage rate limit / busy attempt=%s wait=%.1fs error=%s",
                attempt + 1,
                wait,
                type(exc).__name__,
            )
            time.sleep(wait)
            delay *= 2
    raise RuntimeError("Voyage embed failed") from last_error


def _upsert(
    client,
    collection: str,
    rows: list[tuple[int, dict, list[float]]],
    model: str,
    dimensions: int,
) -> None:
    from qdrant_client.models import PointStruct

    if not rows:
        return
    points = [
        PointStruct(
            id=point_id,
            vector=vector,
            payload=_payload(chunk, model, dimensions),
        )
        for point_id, chunk, vector in rows
    ]
    delay = 0.5
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            client.upsert(collection_name=collection, points=points, wait=True)
            return
        except Exception as exc:
            last_error = exc
            if attempt == 4:
                break
            log.warning(
                "Qdrant upsert retry attempt=%s points=%s error=%s",
                attempt + 1,
                len(points),
                type(exc).__name__,
            )
            time.sleep(delay)
            delay = min(delay * 2, 8.0)
    raise RuntimeError("Qdrant upsert failed") from last_error


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build chunk plan only; no Voyage calls, no Qdrant writes",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N missing point ids (smoke test)",
    )
    return p.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    args = _parse_args()
    cfg = _require_env()
    batch_size, sleep_s = _rate_settings()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(base_dir, "processed_law.json")
    with open(source, encoding="utf-8") as handle:
        import json

        data = json.load(handle)

    chunks = build_chunks(data["acts"])
    total = len(chunks)
    chunk_ids = [c["chunk_id"] for c in chunks]
    log.info(
        "chunked=%s model=%s dim=%s collection=%s batch=%s sleep=%.2fs",
        total,
        cfg["model"],
        cfg["dimensions"],
        cfg["collection"],
        batch_size,
        sleep_s,
    )

    if args.dry_run:
        chars = sum(len(c.get("content") or "") for c in chunks)
        log.info("dry-run total_chars=%s approx_tokens~%s", chars, chars // 4)
        log.info("dry-run OK — no API calls")
        return

    try:
        import voyageai
    except ImportError:
        raise SystemExit("Install voyageai: pip install voyageai") from None

    qdrant = _qdrant(cfg)
    _assert_collection(qdrant, cfg["collection"], cfg["dimensions"])
    existing = _existing_matching_ids(
        qdrant,
        cfg["collection"],
        chunk_ids,
        cfg["model"],
        cfg["dimensions"],
    )
    missing = [i for i in range(total) if i not in existing]
    if args.limit is not None:
        missing = missing[: max(0, args.limit)]
    log.info(
        "already_stored=%s to_embed=%s",
        len(existing),
        len(missing),
    )
    if not missing:
        log.info("Nothing to do.")
        return

    voyage = voyageai.Client(api_key=cfg["voyage_key"])
    pending: list[tuple[int, dict, list[float]]] = []
    tokens_used = 0
    started = time.time()

    for start in range(0, len(missing), batch_size):
        ids = missing[start : start + batch_size]
        texts = [chunks[i]["content"] for i in ids]
        vectors, batch_tokens = _embed_batch(
            voyage, texts, cfg["model"], cfg["dimensions"]
        )
        tokens_used += batch_tokens
        for point_id, vector in zip(ids, vectors):
            pending.append((point_id, chunks[point_id], vector))
        if len(pending) >= UPLOAD_BATCH:
            _upsert(
                qdrant,
                cfg["collection"],
                pending,
                cfg["model"],
                cfg["dimensions"],
            )
            pending = []
        done = start + len(ids)
        elapsed = max(time.time() - started, 1e-6)
        log.info(
            "embedded %s/%s batch_tokens=%s total_tokens=%s rate=%.1f chunks/min",
            done,
            len(missing),
            batch_tokens,
            tokens_used,
            done / elapsed * 60.0,
        )
        # Pace after every Voyage request (except possibly the last).
        if start + batch_size < len(missing) and sleep_s > 0:
            time.sleep(sleep_s)

    if pending:
        _upsert(
            qdrant,
            cfg["collection"],
            pending,
            cfg["model"],
            cfg["dimensions"],
        )

    info = qdrant.get_collection(cfg["collection"])
    log.info(
        "Done. collection=%s points=%s voyage_tokens_this_run=%s",
        cfg["collection"],
        info.points_count,
        tokens_used,
    )
    log.info("Old collection %s was not modified.", OLD_COLLECTION)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted — rerun to resume.", file=sys.stderr)
        sys.exit(130)
