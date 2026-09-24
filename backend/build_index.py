# build_index.py
import os
import json
import pickle
import numpy as np
import faiss
from fastembed import TextEmbedding
from article_parser import classify_constitution_section

DOCUMENT_ID_CONSTITUTION = "bd-constitution"
EN_CONSTITUTION_TITLE_MARK = "Constitution of the People"
BN_CONSTITUTION_TITLE = "গণপ্রজাতন্ত্রী বাংলাদেশের সংবিধান"

# Load the JSON file
with open("processed_law.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def extract_chunks(data):
    act_title = data.get("act_title", "")
    chunks = []

    for i, sec in enumerate(data.get("sections", [])):
        text = sec.get("section_content", "").strip()
        if text:
            chunks.append({
                "act_title": act_title,
                "chunk_type": "section",
                "chunk_id": f"{act_title}-sec-{i+1}",
                "content": text
            })

    for i, foot in enumerate(data.get("footnotes", [])):
        text = foot.get("footnote_text", "").strip()
        if text:
            chunks.append({
                "act_title": act_title,
                "chunk_type": "footnote",
                "chunk_id": f"{act_title}-footnote-{i+1}",
                "content": text
            })

    return chunks


def is_english_constitution(act: dict) -> bool:
    title = act.get("act_title") or ""
    return EN_CONSTITUTION_TITLE_MARK in title


def is_bangla_constitution(act: dict) -> bool:
    title = act.get("act_title") or ""
    return BN_CONSTITUTION_TITLE in title


def extract_constitution_chunks(act: dict, language: str) -> list:
    """Index constitution articles only; skip omitted placeholders."""
    act_title = act.get("act_title", "")
    chunks = []

    for sec in act.get("sections", []):
        text = (sec.get("section_content") or "").strip()
        if not text:
            continue

        classified = classify_constitution_section(text, language)
        if classified["kind"] != "article":
            continue

        article_key = classified["article_key"]
        chunks.append({
            "act_title": act_title,
            "chunk_type": "section",
            "chunk_id": f"{DOCUMENT_ID_CONSTITUTION}:{language}:{article_key}",
            "content": text,
            "document_id": DOCUMENT_ID_CONSTITUTION,
            "language": language,
            "article_key": article_key,
            "display_number": classified["display_number"],
            "sibling_chunk_id": None,
        })

    for footnote_index, foot in enumerate(act.get("footnotes", [])):
        text = (foot.get("footnote_text") or "").strip()
        if text:
            chunks.append({
                "act_title": act_title,
                "chunk_type": "footnote",
                "chunk_id": (
                    f"{DOCUMENT_ID_CONSTITUTION}:{language}:footnote-{footnote_index + 1}"
                ),
                "content": text,
            })

    return chunks


def assert_constitution_pairs(en_chunks: list, bn_chunks: list) -> None:
    """Fail the build if EN/BN constitution article keys are not 1:1."""
    en_keys = [c["article_key"] for c in en_chunks]
    bn_keys = [c["article_key"] for c in bn_chunks]

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
    """Set sibling_chunk_id on each paired constitution article chunk."""
    bn_by_key = {c["article_key"]: c for c in bn_chunks}
    en_by_key = {c["article_key"]: c for c in en_chunks}

    for en_chunk in en_chunks:
        bn_chunk = bn_by_key[en_chunk["article_key"]]
        en_chunk["sibling_chunk_id"] = bn_chunk["chunk_id"]
        bn_chunk["sibling_chunk_id"] = en_chunk["chunk_id"]


# Combine all chunks
all_chunks = []
en_constitution_articles = []
bn_constitution_articles = []

for act in data["acts"]:
    if is_english_constitution(act):
        chunks = extract_constitution_chunks(act, "en")
        en_constitution_articles = [c for c in chunks if c.get("article_key")]
        all_chunks.extend(chunks)
    elif is_bangla_constitution(act):
        chunks = extract_constitution_chunks(act, "bn")
        bn_constitution_articles = [c for c in chunks if c.get("article_key")]
        all_chunks.extend(chunks)
    else:
        all_chunks.extend(extract_chunks(act))

assert_constitution_pairs(en_constitution_articles, bn_constitution_articles)
link_constitution_siblings(en_constitution_articles, bn_constitution_articles)

# Embeddings
model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
texts = [chunk["content"] for chunk in all_chunks]
metadata = all_chunks

embeddings = np.array(list(model.embed(texts)), dtype="float32")

# FAISS
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

# Save
os.makedirs("embeddings", exist_ok=True)
faiss.write_index(index, "embeddings/faiss.index")
with open("embeddings/chunk_metadata.pkl", "wb") as f:
    pickle.dump(metadata, f)

print("✅ Rebuilt FAISS index and saved.")
