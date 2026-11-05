# VerdictAI

VerdictAI answers questions about the Constitution and statutes of Bangladesh, in English or Bangla. Text chat returns a full answer. Voice chat speaks a shorter summary of that same answer. An uploaded PDF, DOCX, or TXT can be compared with the stored law.

This is legal information, not legal advice.

## Stack

- Frontend: Next.js 16, React 19, TypeScript
- Backend: FastAPI
- Answers: Groq
- Retrieval: Qdrant cosine search plus keyword search over the constitution and other stored Acts
- Voice: ElevenLabs. The API key stays on the server.

## Requirements

- Node.js 20+
- Python 3.12
- A Groq API key and model name

Voice also needs an ElevenLabs agent. Text chat works without it.

## Setup

```bash
git clone https://github.com/potat0w/verdictA.git
cd verdictA
```

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add these to `backend/.env`. Do not commit that file.

```
GROQ_API_KEY=
GROQ_MODEL_NAME=
```

`.env.example` lists the voice settings. `ELEVENLABS_WEBHOOK_SECRET` is the shared secret for `POST /voice/ask`. `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID` are used only to start a voice session. `VOICE_ANSWER_TOKEN_BUDGET` caps the spoken answer. The default is 180, about 720 characters. Text answers use a separate, larger budget.

The API reads vectors and passage text from Qdrant. It does not load `faiss.index` or `chunk_metadata.pkl`. Query embeddings come from the provider in `EMBEDDING_PROVIDER` (`tei` or `huggingface`) using `sentence-transformers/all-MiniLM-L6-v2` at 384 dimensions. The Qdrant collection `verdictai` stores cosine vectors from that same model. Rebuild only when the source law changes, with the local Text Embeddings Inference server running at `TEI_BASE_URL`:

```bash
python build_index.py
```

That reads `backend/processed_law.json`, embeds it through `TEI_BASE_URL/embed`, and uploads a fresh cosine collection. It does not reuse `faiss.index`. Production queries set `EMBEDDING_PROVIDER=huggingface` and `HF_API_TOKEN`. The model and dimension stay the same.

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

The browser calls this site, and the site forwards to that API. On Vercel, set `NEXT_PUBLIC_API_URL` to the public API before building. The browser never receives the ElevenLabs key or the webhook secret.

## Run

From `backend/`, with the virtualenv active:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

On Render, set the root directory to `backend` and the start command to:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

`127.0.0.1` and a fixed port `8000` are not reachable there. Render injects `PORT`. Set `GROQ_API_KEY`, `GROQ_MODEL_NAME`, `QDRANT_URL`, `QDRANT_API_KEY`, and `JWT_SECRET` in the Render environment. Voice also needs `ELEVENLABS_WEBHOOK_SECRET`, `ELEVENLABS_AGENT_ID`, and `ELEVENLABS_API_KEY`.

From `frontend/`:

```bash
npm run dev
```

- Site: http://localhost:3000
- API: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health

For voice, the ElevenLabs agent must be able to call `POST /voice/ask` on a public HTTPS URL, with the webhook secret. A local server is not reachable from ElevenLabs until that URL is in place. Start a new voice session after changing the agent prompt.

## What the app does

Text chat (`POST /ask`) retrieves matching passages and writes a detailed answer. The language follows the question: a Bangla question is answered in Bangla, an English question in English. Recent chat turns can be sent as `history` so a follow-up keeps the earlier facts. Chat history in the browser is kept locally for three days.

Voice uses the same retrieval and legal answer, then returns a short summary. That summary is what gets spoken. Lower `VOICE_ANSWER_TOKEN_BUDGET` to spend fewer voice credits.

Document analysis (`POST /analyze`) accepts one PDF, DOCX, or TXT file up to 5 MB. Scanned PDFs are not read.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service check |
| `GET` | `/health` | Index and Groq configuration |
| `GET` | `/warmup` | Load the search models |
| `POST` | `/ask` | Detailed answer. Body: `query`, optional `language` (`en` or `bn`), optional `history` |
| `POST` | `/voice/ask` | Spoken summary. Header `X-VerdictAI-Webhook-Secret` or `Authorization: Bearer`. Body: `query`, `language` |
| `GET` | `/voice/session` | Conversation token or public agent id. Does not return secrets |
| `POST` | `/analyze` | Multipart file upload |

`POST /ask` and `POST /voice/ask` both respond with `{ "answer": "..." }`.

## Tests

From `backend/`, with the virtualenv active:

```bash
pytest
```

## Project layout

```
frontend/src/app/            pages
frontend/src/components/chat chat and voice
frontend/src/lib/api.ts      API client
backend/app.py               HTTP API
backend/rag_utils.py         retrieval and answers
backend/answer_quality.py    citation checks and the voice summary
backend/embeddings/          search index
backend/tests/               API and answer tests
```
