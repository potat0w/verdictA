"""Embedding requests stay on one model and reject the wrong vector width."""

import pytest

from embedding_provider import (
    EmbeddingError,
    embed_texts,
    parse_embeddings,
    provider_name,
)


def test_tei_posts_one_batch(monkeypatch):
    calls = []

    def fake_post(url, body, headers):
        calls.append((url, body, headers))
        return [[0.1] * 384 for _ in body["inputs"]]

    monkeypatch.setattr("embedding_provider._post_json", fake_post)
    vectors = embed_texts(["arrest rights", "a second sentence"], provider="tei")
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert calls[0][0].endswith("/embed")
    assert calls[0][1]["inputs"] == ["arrest rights", "a second sentence"]
    assert "Authorization" not in calls[0][2]


def test_huggingface_uses_the_feature_extraction_route(monkeypatch):
    calls = []

    def fake_post(url, body, headers):
        calls.append((url, body, headers))
        return [[0.2] * 384]

    monkeypatch.setenv("HF_API_TOKEN", "hf-test-token")
    monkeypatch.setattr("embedding_provider._post_json", fake_post)
    vector = embed_texts(["arrest rights"], provider="huggingface")[0]
    assert len(vector) == 384
    assert calls[0][0].endswith(
        "/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
    )
    assert calls[0][1]["normalize"] is True
    assert calls[0][2]["Authorization"] == "Bearer hf-test-token"


def test_wrong_width_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "embedding_provider._post_json",
        lambda url, body, headers: [[0.0, 1.0]],
    )
    with pytest.raises(EmbeddingError, match="384"):
        embed_texts(["arrest rights"], provider="tei")


def test_a_different_model_is_refused(monkeypatch):
    monkeypatch.setenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )

    def fail(url, body, headers):
        raise AssertionError("mismatched model must not be requested")

    monkeypatch.setattr("embedding_provider._post_json", fail)
    with pytest.raises(EmbeddingError, match="Refusing to embed"):
        embed_texts(["arrest rights"], provider="tei")


def test_render_skips_a_localhost_tei_server(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "tei")
    monkeypatch.setenv("TEI_BASE_URL", "http://localhost:8080")
    assert provider_name() == "fastembed"


def test_render_keeps_a_reachable_tei_server(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "tei")
    monkeypatch.setenv("TEI_BASE_URL", "https://embeddings.example.com")
    assert provider_name() == "tei"


def test_fastembed_does_not_call_http(monkeypatch):
    class FakeModel:
        def embed(self, texts):
            for _text in texts:
                yield [0.3] * 384

    monkeypatch.setattr("embedding_provider._local_model", FakeModel())

    def fail(url, body, headers):
        raise AssertionError("fastembed must not call the embedding server")

    monkeypatch.setattr("embedding_provider._post_json", fail)
    vector = embed_texts(["arrest rights"], provider="fastembed")[0]
    assert len(vector) == 384


def test_parse_accepts_a_single_flat_vector():
    parsed = parse_embeddings([0.5] * 384, count=1, width=384)
    assert len(parsed) == 1
    assert len(parsed[0]) == 384
