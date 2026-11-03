"""Build the FAISS index and chunk metadata.

Writes temporary files and replaces the live index only after the embed finishes.
Footnotes are not vectorized. A language-tagged question searches the matching
constitution collection only.
"""

from __future__ import annotations

import json
import os
import pickle

import faiss
import numpy as np
from fastembed import TextEmbedding

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
EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
QUERY_PREFIX = ""
PASSAGE_PREFIX = ""
EMBED_BATCH = 64


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


def embed_texts(model: TextEmbedding, texts: list[str]) -> np.ndarray:
    batches = []
    total = len(texts)
    for start in range(0, total, EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        prefixed = [f"{PASSAGE_PREFIX}{text}" for text in batch]
        vectors = np.array(list(model.embed(prefixed)), dtype="float32")
        batches.append(vectors)
        print(f"embedded {min(start + EMBED_BATCH, total)}/{total}", flush=True)
    return np.vstack(batches)


def write_index(base_dir: str, chunks: list, vectors: np.ndarray) -> None:
    embed_dir = os.path.join(base_dir, "embeddings")
    os.makedirs(embed_dir, exist_ok=True)
    index_tmp = os.path.join(embed_dir, "faiss.index.tmp")
    meta_tmp = os.path.join(embed_dir, "chunk_metadata.pkl.tmp")
    info_tmp = os.path.join(embed_dir, "index_meta.json.tmp")

    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, index_tmp)
    with open(meta_tmp, "wb") as handle:
        pickle.dump(chunks, handle)
    with open(info_tmp, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "model_name": EMBED_MODEL_NAME,
                "query_prefix": QUERY_PREFIX,
                "passage_prefix": PASSAGE_PREFIX,
                "chunks": len(chunks),
            },
            handle,
        )

    os.replace(index_tmp, os.path.join(embed_dir, "faiss.index"))
    os.replace(meta_tmp, os.path.join(embed_dir, "chunk_metadata.pkl"))
    os.replace(info_tmp, os.path.join(embed_dir, "index_meta.json"))


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(base_dir, "processed_law.json")
    with open(source, encoding="utf-8") as handle:
        data = json.load(handle)

    chunks = build_chunks(data["acts"])
    print(f"chunked {len(chunks)} passages", flush=True)
    model = TextEmbedding(model_name=EMBED_MODEL_NAME)
    vectors = embed_texts(model, [chunk["content"] for chunk in chunks])
    write_index(base_dir, chunks, vectors)
    print(f"Rebuilt FAISS index with {EMBED_MODEL_NAME} ({len(chunks)} chunks).")


if __name__ == "__main__":
    main()
