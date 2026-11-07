"""Retrieval stays on one collection, and a missing metadata file does not scroll every vector."""

import pytest
from dotenv import load_dotenv

from hybrid_search import BM25Index
from answer_quality import question_script


def test_streamed_bm25_matches_the_batch_index():
    documents = [
        (4, "dismissal without notice after a finding of misconduct"),
        (9, "wages are paid within the working days stated in the section"),
        (12, "a person who is arrested is told the grounds"),
    ]
    batch = BM25Index(documents)
    streamed = BM25Index()
    for row_id, text in documents:
        streamed.add(row_id, text)
    streamed.finish()
    query = "arrested and told the grounds"
    assert streamed.rank(query, 3) == batch.rank(query, 3)


def test_remote_retrieve_reads_only_the_constitution_collection(monkeypatch):
    import rag_utils

    calls = []

    def fake_iter(collection, language=None):
        calls.append((collection, language))
        return iter(
            [
                (
                    7,
                    {
                        "collection": collection,
                        "content": "A person who is arrested shall be informed of the grounds.",
                        "article_key": "A",
                        "chunk_id": "c-a",
                        "chunk_type": "section",
                    },
                ),
                (
                    8,
                    {
                        "collection": collection,
                        "content": "Property may be acquired only as the law provides.",
                        "article_key": "B",
                        "chunk_id": "c-b",
                        "chunk_type": "section",
                    },
                ),
            ]
        )

    monkeypatch.setattr("qdrant_store.iter_payloads", fake_iter)
    monkeypatch.setattr(
        "qdrant_store.search_collection_scored",
        lambda vector, collection, k: [(7, 0.2)],
    )
    previous = (
        rag_utils._remote_chunks,
        rag_utils._models_initialized,
        rag_utils._embed_model,
    )
    rag_utils._remote_chunks = True
    rag_utils._models_initialized = True
    rag_utils._partition_cache.clear()
    rag_utils._bm25_cache.clear()
    monkeypatch.setattr("embedding_provider.embed_query", lambda text: [0.0] * 384)
    try:
        hits = rag_utils.retrieve_chunks(
            "A person was arrested and was not told the grounds.",
            top_k=2,
            language="en",
        )
    finally:
        rag_utils._remote_chunks, rag_utils._models_initialized, rag_utils._embed_model = previous
        rag_utils._partition_cache.clear()
        rag_utils._bm25_cache.clear()

    assert calls == [("constitution-en", None)]
    assert hits
    assert {hit["collection"] for hit in hits} == {"constitution-en"}
    assert all(hit.get("content") for hit in hits)


def test_remote_statutes_fetch_only_ranked_passages(monkeypatch, tmp_path):
    import rag_utils

    stored = {
        3: {
            "collection": "other-acts",
            "language": "en",
            "content": "Whoever threatens injury to a person commits an offence.",
            "section_number": "1",
            "chunk_type": "section",
        },
        4: {
            "collection": "other-acts",
            "language": "en",
            "content": "The company may register its name.",
            "section_number": "2",
            "chunk_type": "section",
        },
    }
    fetched = []

    monkeypatch.setattr(rag_utils, "BM25_INDEX_DIR", str(tmp_path))
    monkeypatch.setattr(
        "qdrant_store.iter_payloads",
        lambda collection, language=None: iter(stored.items()),
    )
    monkeypatch.setattr(
        "qdrant_store.fetch_payloads",
        lambda row_ids: fetched.append(list(row_ids))
        or {row_id: stored[row_id] for row_id in row_ids if row_id in stored},
    )
    monkeypatch.setattr(
        "qdrant_store.search_collection_scored",
        lambda vector, collection, k, language=None: [(3, 0.55)],
    )
    monkeypatch.setattr(
        "embedding_provider.embed_query",
        lambda text: [0.0] * 384,
    )
    rag_utils._bm25_cache.pop("other-acts-en", None)
    chunks = rag_utils._remote_statute_chunks("threatens injury to a person", "en")
    rag_utils._bm25_cache.pop("other-acts-en", None)

    assert fetched
    assert set(fetched[0]).issubset(stored)
    assert len(fetched[0]) <= 80
    assert chunks
    assert all(chunk["collection"] == "other-acts" for chunk in chunks)


def test_blank_query_does_not_initialize_models(monkeypatch):
    import rag_utils

    def fail():
        raise AssertionError("blank query should not load models")

    monkeypatch.setattr(rag_utils, "_lazy_init_models", fail)
    assert rag_utils.retrieve_chunks("   ", top_k=5, language="en") == []


def test_strings_without_words_are_not_treated_as_questions():
    assert question_script("fdfhy5") is None
    assert question_script("123456") is None
    assert question_script("What rights follow an arrest?") == "en"
    assert question_script("গ্রেপ্তারের পর কী অধিকার থাকে?") == "bn"


def test_live_collections_are_filtered_and_have_passage_text():
    load_dotenv()
    from qdrant_store import iter_payloads, qdrant_configured

    if not qdrant_configured():
        pytest.skip("QDRANT_URL is not set")

    def take(collection, language=None, limit=3000):
        rows = []
        for _row_id, chunk in iter_payloads(collection, language):
            rows.append(chunk)
            if len(rows) > limit:
                break
        return rows

    english = take("constitution-en")
    bangla = take("constitution-bn")
    statute = next(iter_payloads("other-acts", language="en"))[1]
    assert 0 < len(english) < 3000
    assert 0 < len(bangla) < 3000
    assert all(chunk.get("collection") == "constitution-en" and chunk.get("content") for chunk in english)
    assert all(chunk.get("collection") == "constitution-bn" and chunk.get("content") for chunk in bangla)
    assert statute.get("collection") == "other-acts"
    assert statute.get("language") == "en"
    assert statute.get("content")


def test_serving_does_not_load_faiss_or_the_metadata_file(monkeypatch, tmp_path):
    import json
    import pickle

    import rag_utils

    marker = tmp_path / "chunk_metadata.pkl"
    with marker.open("wb") as handle:
        pickle.dump([{"content": "should not be loaded"}], handle)
    meta = tmp_path / "index_meta.json"
    meta.write_text(
        json.dumps(
            {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "query_prefix": "",
                "passage_prefix": "",
                "dimension": 384,
                "distance": "Cosine",
                "chunks": 1,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(rag_utils, "META_PATH", str(marker))
    monkeypatch.setattr(rag_utils, "INDEX_PATH", str(tmp_path / "faiss.index"))
    monkeypatch.setattr(rag_utils, "INDEX_META_PATH", str(meta))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "tei")
    monkeypatch.setenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "384")
    previous = (
        rag_utils._models_initialized,
        rag_utils._embed_model,
        rag_utils._remote_chunks,
        rag_utils._init_start_time,
        rag_utils.EMBED_MODEL_NAME,
    )
    rag_utils._models_initialized = False
    rag_utils._embed_model = None
    rag_utils._init_start_time = None
    try:
        rag_utils._lazy_init_models()
        assert rag_utils._remote_chunks is True
        assert rag_utils.EMBED_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"
        assert not hasattr(rag_utils, "_index")
        assert marker.stat().st_size > 0
    finally:
        (
            rag_utils._models_initialized,
            rag_utils._embed_model,
            rag_utils._remote_chunks,
            rag_utils._init_start_time,
            rag_utils.EMBED_MODEL_NAME,
        ) = previous


def test_qdrant_answers_english_and_bangla_without_local_metadata():
    from qdrant_store import qdrant_configured
    from rag_utils import retrieve_chunks

    if not qdrant_configured():
        pytest.skip("QDRANT_URL is not set")
    english = retrieve_chunks(
        "What rights does a person have after being arrested?",
        top_k=3,
        language="en",
    )
    bangla = retrieve_chunks(
        "গ্রেপ্তারের পর একজন ব্যক্তির কী অধিকার থাকে?",
        top_k=3,
        language="bn",
    )
    assert english
    assert bangla
    assert all(chunk.get("collection") == "constitution-en" and chunk.get("content") for chunk in english)
    assert all(chunk.get("collection") == "constitution-bn" and chunk.get("content") for chunk in bangla)
