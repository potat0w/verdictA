#!/usr/bin/env python3
"""Build on-disk BM25 indexes for Other Acts (en + bn).

Scrolls Qdrant payloads once per language and writes finished BM25Index
pickles under bm25_indexes/. Does not change live retrieval yet.

Uses the same bm25_document() text as rag_utils statute search.
Respects EMBEDDING_PROVIDER / VOYAGE_COLLECTION (active serving collection).

From backend/ (venv on):
  python build_bm25_indexes.py
  python build_bm25_indexes.py --language bn
  python build_bm25_indexes.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from hybrid_search import BM25Index, bm25_document

log = logging.getLogger("build_bm25_indexes")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = BASE_DIR / "bm25_indexes"
LANGUAGES = ("en", "bn")
PROGRESS_EVERY = 2000


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build other-acts BM25 indexes (en and/or bn) onto disk."
    )
    parser.add_argument(
        "--language",
        choices=("en", "bn", "both"),
        default="both",
        help="Which language index to build (default: both).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output folder (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scroll and count only; do not write pickles.",
    )
    return parser.parse_args()


def _languages(choice: str) -> tuple[str, ...]:
    if choice == "both":
        return LANGUAGES
    return (choice,)


def _paths(out_dir: Path, language: str) -> tuple[Path, Path]:
    stem = f"other-acts-{language}"
    return out_dir / f"{stem}.pkl", out_dir / f"{stem}.meta.json"


def _build_one(language: str, out_dir: Path, dry_run: bool) -> dict:
    from qdrant_store import active_collection, iter_payloads

    collection = active_collection()
    index = BM25Index()
    count = 0
    skipped_footnote = 0
    skipped_empty = 0
    t0 = time.time()
    log.info(
        "Building other-acts BM25 language=%s qdrant=%s",
        language,
        collection,
    )

    for row_id, chunk in iter_payloads("other-acts", language=language):
        if chunk.get("chunk_type") == "footnote":
            skipped_footnote += 1
            continue
        if not (chunk.get("content") or "").strip():
            skipped_empty += 1
            continue
        index.add(row_id, bm25_document(chunk))
        count += 1
        if count % PROGRESS_EVERY == 0:
            log.info(
                "  language=%s progress=%s elapsed=%.1fs",
                language,
                count,
                time.time() - t0,
            )

    index.finish()
    elapsed = time.time() - t0
    meta = {
        "kind": "other-acts",
        "language": language,
        "qdrant_collection": collection,
        "rows": count,
        "skipped_footnote": skipped_footnote,
        "skipped_empty": skipped_empty,
        "n_docs": index.n_docs,
        "avgdl": round(index.avgdl, 4),
        "terms": len(index.postings),
        "built_seconds": round(elapsed, 2),
        "pickle": f"other-acts-{language}.pkl",
    }
    log.info(
        "Finished language=%s rows=%s terms=%s seconds=%.1f",
        language,
        count,
        meta["terms"],
        elapsed,
    )

    if dry_run:
        log.info("Dry run — not writing language=%s", language)
        return meta

    out_dir.mkdir(parents=True, exist_ok=True)
    pkl_path, meta_path = _paths(out_dir, language)
    with pkl_path.open("wb") as handle:
        pickle.dump(index, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with meta_path.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    log.info("Wrote %s (%s bytes)", pkl_path, pkl_path.stat().st_size)
    log.info("Wrote %s", meta_path)
    return meta


def main() -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    args = _parse_args()

    if not os.getenv("QDRANT_URL", "").strip():
        log.error("QDRANT_URL is not set in .env")
        return 1

    from qdrant_store import active_collection, serving_status

    status = serving_status()
    log.info(
        "Active Qdrant collection=%s size=%s points=%s",
        status["name"],
        status["size"],
        status["points"],
    )
    log.info("active_collection()=%s", active_collection())

    summaries = []
    for language in _languages(args.language):
        summaries.append(_build_one(language, args.out_dir, args.dry_run))

    log.info("Done. indexes=%s", [s["language"] for s in summaries])
    for item in summaries:
        log.info(
            "  %s rows=%s terms=%s dry_run=%s",
            item["language"],
            item["rows"],
            item["terms"],
            args.dry_run,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
