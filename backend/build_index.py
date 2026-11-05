"""Embed the statute dataset with the local TEI server and upload it to Qdrant.

Does not load the embedding model in-process, and does not read faiss.index.
Footnotes are not vectorized. A language-tagged question searches the matching
constitution collection only.
"""

from __future__ import annotations

import json
import logging
import os

from article_parser import classify_constitution_section
from chunking import (
    compose_section_text,
    detect_language,
    section_number_from_text,
    split_passage,
)

DOCUMENT_ID_CONSTITUTION = "bd-constitution"
EN_CONSTITUTION_TITLE_MARK = "Constitution of the People"
BN_CONSTITUTION_TITLE = "গণপ্রজাতন্ত্রী বাংলাদেশের সংবিধান"
QUERY_PREFIX = ""
PASSAGE_PREFIX = ""
EMBED_BATCH = 32
UPLOAD_BATCH = 128


def is_english_constitution(act: dict) -> bool:
    title = act.get("act_title") or ""
    return EN_CONSTITUTION_TITLE_MARK in title


def is_bangla_constitution(act: dict) -> bool:
    title = act.get("act_title") or ""
    return BN_CONSTITUTION_TITLE in title


def extract_constitution_chunks(act: dict, language: str) -> list:
    """Index constitution articles only. Footnotes are not separate vectors."""
    act_title = act.get("act_title", "")
    chunks = []

    for sec in act.get("sections", []):
        raw = (sec.get("section_content") or "").strip()
        if not raw:
            continue

        classified = classify_constitution_section(raw, language)
        if classified["kind"] != "article":
            continue

        title = (sec.get("section_title") or "").strip()
        article_key = classified["article_key"]
        chunks.append({
            "act_title": act_title,
            "chunk_type": "section",
            "chunk_id": f"{DOCUMENT_ID_CONSTITUTION}:{language}:{article_key}",
            "content": compose_section_text(title, raw),
            "section_title": title,
            "document_id": DOCUMENT_ID_CONSTITUTION,
            "language": language,
            "collection": f"constitution-{language}",
            "article_key": article_key,
            "display_number": classified["display_number"],
            "sibling_chunk_id": None,
        })

    return chunks


def extract_act_chunks(act: dict) -> list:
    act_title = act.get("act_title", "")
    chunks = []
    for index, sec in enumerate(act.get("sections", [])):
        raw = (sec.get("section_content") or "").strip()
        if not raw:
            continue
        title = (sec.get("section_title") or "").strip()
        text = compose_section_text(title, raw)
        language = detect_language(f"{act_title}\n{raw}")
        chunks.append({
            "act_title": act_title,
            "chunk_type": "section",
            "chunk_id": f"{act_title}-sec-{index + 1}",
            "content": text,
            "language": language,
            "collection": "other-acts",
            "section_number": section_number_from_text(raw),
            "section_title": title,
        })
    return chunks


def assert_constitution_pairs(en_chunks: list, bn_chunks: list) -> None:
    """Fail the build if EN/BN constitution article keys are not 1:1."""
    en_keys = [chunk["article_key"] for chunk in en_chunks]
    bn_keys = [chunk["article_key"] for chunk in bn_chunks]
    en_set = set(en_keys)
    bn_set = set(bn_keys)

    if len(en_keys) != len(en_set):
        raise RuntimeError(f"Duplicate EN constitution article_key values: {en_keys}")
    if len(bn_keys) != len(bn_set):
        raise RuntimeError(f"Duplicate BN constitution article_key values: {bn_keys}")

    only_en = sorted(en_set - bn_set)
    only_bn = sorted(bn_set - en_set)
    if only_en or only_bn:
        raise RuntimeError(
            "Constitution EN/BN article_key mismatch. "
            f"EN_only={only_en} BN_only={only_bn}"
        )


def link_constitution_siblings(en_chunks: list, bn_chunks: list) -> None:
    """Point each article piece at the other language's first piece."""
    def first_id(chunks: list) -> dict:
        grouped: dict = {}
        for chunk in chunks:
            grouped.setdefault(chunk["article_key"], chunk["chunk_id"])
        return grouped

    bn_first = first_id(bn_chunks)
    en_first = first_id(en_chunks)
    for chunk in en_chunks:
        chunk["sibling_chunk_id"] = bn_first[chunk["article_key"]]
    for chunk in bn_chunks:
        chunk["sibling_chunk_id"] = en_first[chunk["article_key"]]


def expand_pieces(chunks: list) -> list:
    expanded = []
    for chunk in chunks:
        pieces = split_passage(chunk["content"])
        if len(pieces) <= 1:
            expanded.append(chunk)
            continue
        for part_index, text in enumerate(pieces):
            piece = dict(chunk)
            piece["content"] = text
            piece["chunk_id"] = f"{chunk['chunk_id']}:{part_index}"
            piece["part_index"] = part_index
            expanded.append(piece)
    return expanded


def build_chunks(acts: list) -> list:
    all_chunks = []
    en_articles = []
    bn_articles = []

    for act in acts:
        if is_english_constitution(act):
            en_articles = extract_constitution_chunks(act, "en")
        elif is_bangla_constitution(act):
            bn_articles = extract_constitution_chunks(act, "bn")
        else:
            all_chunks.extend(extract_act_chunks(act))

    assert_constitution_pairs(en_articles, bn_articles)
    en_pieces = expand_pieces(en_articles)
    bn_pieces = expand_pieces(bn_articles)
    link_constitution_siblings(en_pieces, bn_pieces)
    return en_pieces + bn_pieces + expand_pieces(all_chunks)


def write_meta(base_dir: str, count: int) -> None:
    from embedding_provider import STORED_DIMENSION, STORED_DISTANCE, STORED_MODEL

    embed_dir = os.path.join(base_dir, "embeddings")
    os.makedirs(embed_dir, exist_ok=True)
    info_tmp = os.path.join(embed_dir, "index_meta.json.tmp")
    with open(info_tmp, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "model_name": STORED_MODEL,
                "query_prefix": QUERY_PREFIX,
                "passage_prefix": PASSAGE_PREFIX,
                "dimension": STORED_DIMENSION,
                "distance": STORED_DISTANCE,
                "chunks": count,
                "index_provider": "tei",
            },
            handle,
        )
    os.replace(info_tmp, os.path.join(embed_dir, "index_meta.json"))


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _stored_vector(point) -> list[float]:
    vector = point.vector
    if isinstance(vector, dict):
        vector = next(iter(vector.values()))
    return [float(value) for value in vector]


def validate_index(chunks: list) -> None:
    """Check collection shape, a stored vector, and one English similarity search."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    from embedding_provider import STORED_DIMENSION, embed_query, embed_texts
    from qdrant_store import (
        COLLECTION_NAME,
        assert_collection_ready,
        get_client,
        serving_status,
    )

    assert_collection_ready(len(chunks))
    status = serving_status()
    query = "What rights does a person have after being arrested?"
    query_vector = embed_query(query)
    document_vector = embed_texts([chunks[0]["content"]], provider="tei")[0]
    if len(query_vector) != STORED_DIMENSION or len(document_vector) != STORED_DIMENSION:
        raise RuntimeError(
            f"Query width {len(query_vector)} and document width {len(document_vector)} "
            f"must both be {STORED_DIMENSION}"
        )
    stored = get_client().retrieve(
        collection_name=COLLECTION_NAME,
        ids=[0],
        with_payload=True,
        with_vectors=True,
    )
    if not stored:
        raise RuntimeError("Point 0 is missing after upload")
    agreement = _cosine(document_vector, _stored_vector(stored[0]))
    if agreement < 0.999:
        raise RuntimeError(f"Stored vector does not match a fresh TEI embedding ({agreement:.4f})")
    found = get_client().query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="collection", match=MatchValue(value="constitution-en"))]
        ),
        limit=5,
        with_payload=True,
    )
    print(
        f"collection={status['name']} size={status['size']} "
        f"distance={status['distance']} points={status['points']}",
        flush=True,
    )
    print(
        f"query_dimensions={len(query_vector)} document_dimensions={len(document_vector)} "
        f"stored_agreement={agreement:.4f}",
        flush=True,
    )
    relevant = False
    for point in found.points:
        payload = point.payload or {}
        text = payload.get("content") or ""
        print(
            f"hit id={point.id} score={point.score:.4f} "
            f"article={payload.get('article_key')} title={payload.get('section_title')}",
            flush=True,
        )
        print(text[:180].replace("\n", " "), flush=True)
        folded = text.lower()
        if "arrest" in folded or "detention" in folded:
            relevant = True
    if not relevant:
        raise RuntimeError("English arrest query did not return an arrest or detention passage")
    bangla = "গ্রেপ্তারের পর একজন ব্যক্তির কী অধিকার থাকে?"
    bangla_vector = embed_texts([bangla], provider="tei")[0]
    if len(bangla_vector) != len(query_vector):
        raise RuntimeError("Bangla query embedding width does not match the English query")
    bangla_hits = get_client().query_points(
        collection_name=COLLECTION_NAME,
        query=bangla_vector,
        query_filter=Filter(
            must=[FieldCondition(key="collection", match=MatchValue(value="constitution-bn"))]
        ),
        limit=3,
        with_payload=True,
    )
    for point in bangla_hits.points:
        payload = point.payload or {}
        text = (payload.get("content") or "")[:180].replace("\n", " ")
        print(
            f"bn hit id={point.id} score={point.score:.4f} "
            f"article={payload.get('article_key')} {text}",
            flush=True,
        )


def main() -> None:
    from dotenv import load_dotenv

    from embedding_provider import STORED_MODEL, embed_texts
    from qdrant_store import ensure_serving_collection, upsert_chunk_batch

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_dotenv()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(base_dir, "processed_law.json")
    with open(source, encoding="utf-8") as handle:
        data = json.load(handle)

    chunks = build_chunks(data["acts"])
    total = len(chunks)
    print(f"chunked {total} passages", flush=True)
    existing = ensure_serving_collection([chunk["chunk_id"] for chunk in chunks])
    missing = [index for index in range(total) if index not in existing]
    print(
        f"uploading {len(missing)} passages, {len(existing)} already stored",
        flush=True,
    )

    pending: list[tuple[int, dict, list[float]]] = []
    done = len(existing)
    for start in range(0, len(missing), EMBED_BATCH):
        ids = missing[start : start + EMBED_BATCH]
        texts = [f"{PASSAGE_PREFIX}{chunks[index]['content']}" for index in ids]
        try:
            vectors = embed_texts(texts, provider="tei")
        except Exception:
            logging.exception("Embedding failed for rows %s-%s", ids[0], ids[-1])
            raise
        if len(vectors) != len(ids):
            raise RuntimeError(
                f"TEI returned {len(vectors)} vectors for {len(ids)} passages"
            )
        for point_id, vector in zip(ids, vectors):
            pending.append((point_id, chunks[point_id], vector))
        if len(pending) >= UPLOAD_BATCH:
            upsert_chunk_batch(pending)
            pending = []
        done = len(existing) + start + len(ids)
        print(f"indexed {done}/{total}", flush=True)
    if pending:
        upsert_chunk_batch(pending)
        print(f"indexed {total}/{total}", flush=True)

    write_meta(base_dir, total)
    validate_index(chunks)
    print(f"Indexed {total} passages with {STORED_MODEL}.")


if __name__ == "__main__":
    main()
