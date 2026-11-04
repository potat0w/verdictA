from fastapi.testclient import TestClient

from app import app

SECRET = "test-webhook-secret"


def _client(monkeypatch) -> TestClient:
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(
        "app.answer_with_rag",
        lambda query, language=None, history=None, voice=False: f"{language}:{query}",
    )
    return TestClient(app)


def test_voice_ask_returns_rag_answer(monkeypatch):
    client = _client(monkeypatch)
    response = client.post(
        "/voice/ask",
        headers={"X-VerdictAI-Webhook-Secret": SECRET},
        json={"query": "What does Article 27 say?", "language": "en"},
    )
    assert response.status_code == 200
    assert response.json() == {"answer": "en:What does Article 27 say?"}


def test_voice_ask_accepts_bearer_secret(monkeypatch):
    client = _client(monkeypatch)
    response = client.post(
        "/voice/ask",
        headers={"Authorization": f"Bearer {SECRET}"},
        json={"query": "অনুচ্ছেদ ২৭", "language": "bn"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "bn:অনুচ্ছেদ ২৭"


def test_voice_ask_rejects_missing_or_wrong_secret(monkeypatch):
    client = _client(monkeypatch)
    missing = client.post(
        "/voice/ask",
        json={"query": "Article 27", "language": "en"},
    )
    wrong = client.post(
        "/voice/ask",
        headers={"X-VerdictAI-Webhook-Secret": "nope"},
        json={"query": "Article 27", "language": "en"},
    )
    assert missing.status_code == 401
    assert wrong.status_code == 401


def test_voice_ask_fails_closed_when_secret_is_unset(monkeypatch):
    monkeypatch.setattr(
        "app.answer_with_rag",
        lambda query, language=None, history=None, voice=False: "should-not-run",
    )
    client = TestClient(app)
    monkeypatch.delenv("ELEVENLABS_WEBHOOK_SECRET", raising=False)
    response = client.post(
        "/voice/ask",
        headers={"X-VerdictAI-Webhook-Secret": SECRET},
        json={"query": "Article 27", "language": "en"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Voice webhook is not configured."


def test_voice_ask_rejects_bad_language_and_blank_query(monkeypatch):
    client = _client(monkeypatch)
    headers = {"X-VerdictAI-Webhook-Secret": SECRET}
    language = client.post(
        "/voice/ask",
        headers=headers,
        json={"query": "Article 27", "language": "fr"},
    )
    blank = client.post(
        "/voice/ask",
        headers=headers,
        json={"query": "  ", "language": "en"},
    )
    assert language.status_code == 422
    assert blank.status_code == 422


def test_voice_session_requires_an_agent_id(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_AGENT_ID", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    client = TestClient(app)
    monkeypatch.delenv("ELEVENLABS_AGENT_ID", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    response = client.get("/voice/session")
    assert response.status_code == 503
    assert response.json()["detail"] == "Voice agent is not configured."


def test_voice_session_returns_public_agent_id_without_secrets(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_public")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    client = TestClient(app)
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_public")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    response = client.get("/voice/session")
    assert response.status_code == 200
    assert response.json() == {"agentId": "agent_public"}
    assert SECRET not in response.text


def test_voice_session_returns_conversation_token_for_private_agent(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_private")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "server-only-key")

    def _fake_token(agent_id: str, api_key: str) -> str:
        assert agent_id == "agent_private"
        assert api_key == "server-only-key"
        return "webrtc-token"

    monkeypatch.setattr("app._elevenlabs_quota_exhausted", lambda api_key: False)
    monkeypatch.setattr("app._elevenlabs_conversation_token", _fake_token)
    client = TestClient(app)
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_private")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "server-only-key")
    response = client.get("/voice/session")
    assert response.status_code == 200
    body = response.json()
    assert body == {"conversationToken": "webrtc-token"}
    assert "server-only-key" not in response.text


def test_voice_session_reports_exhausted_credits(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_private")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "server-only-key")
    monkeypatch.setattr("app._elevenlabs_quota_exhausted", lambda api_key: True)
    client = TestClient(app)
    response = client.get("/voice/session")
    assert response.status_code == 503
    assert "credits" in response.json()["detail"]


def test_existing_ask_does_not_require_webhook_secret(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_WEBHOOK_SECRET", raising=False)
    monkeypatch.setattr(
        "app.answer_with_rag",
        lambda query, language=None, history=None, voice=False: "from-ask",
    )
    client = TestClient(app)
    response = client.post("/ask", json={"query": "Article 27", "language": "en"})
    assert response.status_code == 200
    assert response.json() == {"answer": "from-ask"}
