import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_utils import answer_with_rag
import rag_utils
from embedding_provider import EmbeddingError
from document_parser import (
    parse_document,
    UnsupportedFileType,
    FileTooLarge,
    EmptyDocument,
    MAX_DOCUMENT_BYTES,
)
from clause_extractor import extract_clauses
from document_analyzer import analyze_document, is_rate_limit
from report_generator import build_report
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from models import User
from database import SessionLocal, engine, Base
import logging
from dotenv import load_dotenv
import os

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_dotenv()
    logger.info("Environment loaded. GROQ_API_KEY set: %s", bool(os.getenv("GROQ_API_KEY")))
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured.")
    except Exception as exc:
        logger.exception("Failed to initialize database: %s", exc)
    _preload_embeddings()
    yield


def _preload_embeddings() -> None:
    try:
        from embedding_provider import preload_local_model

        preload_local_model()
    except Exception as exc:
        logger.exception("Local embedding model did not load at startup: %s", exc)


def _configured_provider() -> str:
    try:
        from embedding_provider import provider_name

        return provider_name()
    except Exception:
        return os.getenv("EMBEDDING_PROVIDER", "tei").strip() or "tei"


def _configured_model() -> str:
    try:
        from embedding_provider import model_name

        return model_name()
    except Exception:
        return os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ).strip()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class ChatTurn(BaseModel):
    role: str
    content: str


class Question(BaseModel):
    query: str
    language: str | None = None
    history: list[ChatTurn] | None = None

class VoiceQuestion(BaseModel):
    query: str
    language: str


def _webhook_secret_matches(provided: str | None, expected: str) -> bool:
    if not provided:
        return False
    return secrets.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def _require_elevenlabs_webhook(
    authorization: str | None,
    webhook_secret_header: str | None,
) -> None:
    """Fail closed unless the configured webhook secret matches."""
    expected = os.getenv("ELEVENLABS_WEBHOOK_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Voice webhook is not configured.")
    bearer_token = ""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            bearer_token = token.strip()
    if _webhook_secret_matches(webhook_secret_header, expected) or _webhook_secret_matches(
        bearer_token, expected
    ):
        return
    raise HTTPException(status_code=401, detail="Unauthorized")

async def _run_legal_question(payload: Question, *, voice: bool = False):
    try:
        if payload.language is not None and payload.language not in ("en", "bn"):
            raise HTTPException(
                status_code=422,
                detail="language must be 'en', 'bn', or omitted",
            )
        history = (
            [{"role": turn.role, "content": turn.content} for turn in payload.history]
            if payload.history
            else None
        )
        answer = answer_with_rag(
            payload.query,
            language=payload.language,
            history=history,
            voice=voice,
        )
        return {"answer": answer}
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        logger.exception("/ask missing embeddings: %s", exc)
        raise HTTPException(status_code=503, detail="Embeddings not found. Please build the index.")
    except ValueError as exc:
        message = str(exc)
        if "GROQ_API_KEY" in message or "GROQ_MODEL_NAME" in message:
            logger.error("/ask missing Groq configuration: %s", exc)
            raise HTTPException(status_code=503, detail="Groq API is not configured on server.")
        logger.exception("/ask value error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate answer.")
    except EmbeddingError:
        logger.exception("/ask embedding failed")
        raise HTTPException(
            status_code=503,
            detail="The embedding service is unavailable.",
        )
    except RuntimeError as exc:
        message = str(exc)
        if "GROQ_API_KEY" in message or "GROQ_MODEL_NAME" in message:
            logger.error("/ask missing Groq configuration")
            raise HTTPException(status_code=503, detail="Groq API is not configured on server.")
        logger.exception("/ask runtime error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate answer.")
    except Exception as exc:
        logger.exception("/ask failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate answer. Check server logs.")


@app.post("/ask")
async def ask_legal_question(payload: Question):
    """Detailed text answer. The voice flag is not part of this request."""
    return await _run_legal_question(payload, voice=False)


@app.post("/voice/ask")
async def voice_ask(
    payload: VoiceQuestion,
    authorization: str | None = Header(default=None),
    x_verdictai_webhook_secret: str | None = Header(default=None),
):
    """ElevenLabs webhook tool. The JSON body is the tool's request body schema.

    Authentication is the shared secret in X-VerdictAI-Webhook-Secret, or
    Authorization: Bearer. Legal reasoning matches POST /ask. The spoken
    answer is a shorter summary, so the full text is not sent to speech.
    """
    _require_elevenlabs_webhook(authorization, x_verdictai_webhook_secret)
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="query must not be empty")
    if payload.language not in ("en", "bn"):
        raise HTTPException(status_code=422, detail="language must be 'en' or 'bn'")
    return await _run_legal_question(
        Question(query=query, language=payload.language),
        voice=True,
    )


def _elevenlabs_quota_exhausted(api_key: str) -> bool:
    """True when the ElevenLabs character quota is already spent."""
    request = urllib.request.Request(
        "https://api.elevenlabs.io/v1/user/subscription",
        headers={"xi-api-key": api_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    used = payload.get("character_count")
    limit = payload.get("character_limit")
    return isinstance(used, int) and isinstance(limit, int) and limit > 0 and used >= limit


def _elevenlabs_conversation_token(agent_id: str, api_key: str) -> str:
    """Mint a WebRTC token. The ElevenLabs API key stays on the server."""
    query = urllib.parse.urlencode({"agent_id": agent_id})
    url = f"https://api.elevenlabs.io/v1/convai/conversation/token?{query}"
    request = urllib.request.Request(url, headers={"xi-api-key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.error("ElevenLabs conversation token failed: %s", exc.code)
        elevenlabs_status = ""
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail_body = payload.get("detail") if isinstance(payload, dict) else None
            if isinstance(detail_body, dict):
                elevenlabs_status = str(detail_body.get("status") or "")
        except (json.JSONDecodeError, UnicodeError):
            elevenlabs_status = ""
        if elevenlabs_status == "missing_permissions":
            detail = "The ElevenLabs API key is missing the convai_write permission."
        elif exc.code == 401:
            detail = "ElevenLabs rejected the API key."
        else:
            detail = "Could not start a voice session."
        raise HTTPException(status_code=502, detail=detail) from exc
    except Exception as exc:
        logger.error("ElevenLabs conversation token failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Could not start a voice session.") from exc
    token = payload.get("token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        logger.error("ElevenLabs conversation token missing")
        raise HTTPException(status_code=502, detail="Could not start a voice session.")
    return token


@app.get("/voice/session")
async def voice_session():
    """Client session for the voice button. Never returns the API key or webhook secret."""
    agent_id = os.getenv("ELEVENLABS_AGENT_ID", "").strip()
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not agent_id:
        raise HTTPException(status_code=503, detail="Voice agent is not configured.")
    if not api_key:
        return {"agentId": agent_id}
    if _elevenlabs_quota_exhausted(api_key):
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs voice credits are used up. Add credits or wait for the quota to reset.",
        )
    return {"conversationToken": _elevenlabs_conversation_token(agent_id, api_key)}

def _analysis_auth_dependency():
    """Phase 1 does not check a token. Swap this dependency for verify_token later."""
    return None


@app.post("/analyze")
async def analyze_uploaded_document(
    file: UploadFile = File(...),
    _auth: dict | None = Depends(_analysis_auth_dependency),
):
    filename = file.filename or ""
    try:
        data = await file.read(MAX_DOCUMENT_BYTES + 1)
        logger.info(
            "/analyze accepted bytes=%s extension=%s",
            len(data),
            os.path.splitext(filename)[1].lower(),
        )
        text = parse_document(filename, data)
        extraction = extract_clauses(text)
        analyses = analyze_document(extraction.clauses)
        return build_report(
            extraction.clauses,
            analyses,
            truncated=extraction.truncated,
        )
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except FileTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except EmptyDocument as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError:
        logger.error("/analyze missing embeddings")
        raise HTTPException(
            status_code=503,
            detail="Embeddings not found. Please build the index.",
        )
    except ValueError as exc:
        message = str(exc)
        if "GROQ_API_KEY" in message or "GROQ_MODEL_NAME" in message:
            logger.error("/analyze missing Groq configuration")
            raise HTTPException(
                status_code=503,
                detail="Groq API is not configured on server.",
            )
        logger.error("/analyze failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to analyze document.")
    except EmbeddingError:
        logger.exception("/analyze embedding failed")
        raise HTTPException(
            status_code=503,
            detail="The embedding service is unavailable.",
        )
    except RuntimeError as exc:
        message = str(exc)
        if "GROQ_API_KEY" in message or "GROQ_MODEL_NAME" in message:
            logger.error("/analyze missing Groq configuration")
            raise HTTPException(
                status_code=503,
                detail="Groq API is not configured on server.",
            )
        logger.error("/analyze failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to analyze document.")
    except Exception as exc:
        if is_rate_limit(exc):
            logger.error("/analyze rate limited")
            raise HTTPException(
                status_code=503,
                detail="The analysis service is busy. Try again shortly.",
            )
        logger.error("/analyze failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to analyze document.")


@app.get("/")
async def root():
    return {"message": "VerdictAI Legal Assistant API"}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "embeddings_index_present": os.path.exists(getattr(rag_utils, "INDEX_PATH", "")),
        "embeddings_metadata_present": os.path.exists(getattr(rag_utils, "META_PATH", "")),
        "groq_key_configured": bool(os.getenv("GROQ_API_KEY")),
        "groq_model_configured": bool(os.getenv("GROQ_MODEL_NAME")),
        "qdrant_configured": bool(os.getenv("QDRANT_URL", "").strip()),
        "embedding_provider": _configured_provider(),
        "embedding_model": _configured_model(),
        "jina_key_configured": bool(os.getenv("JINA_API_KEY", "").strip()),
    }

@app.get("/warmup")
async def warmup():
    """Pre-initialize all models to improve first query performance"""
    try:
        rag_utils._lazy_init_models()
        return {"status": "warmed_up", "message": "All models initialized successfully"}
    except Exception as exc:
        logger.exception("Warmup failed: %s", exc)
        raise HTTPException(status_code=503, detail="Model warmup failed")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
_ephemeral_jwt_secret = ""


def _jwt_secret() -> str:
    """Signing key from JWT_SECRET. A process-only key is used when it is unset."""
    global _ephemeral_jwt_secret
    load_dotenv()
    configured = os.getenv("JWT_SECRET", "").strip()
    if configured:
        return configured
    if not _ephemeral_jwt_secret:
        _ephemeral_jwt_secret = secrets.token_hex(32)
        logger.warning("JWT_SECRET is unset. Login tokens will not survive a restart.")
    return _ephemeral_jwt_secret

class UserCreate(BaseModel):
    username: str
    password: str

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return create_user(db=db, user=user)

def authenticate_user(username: str, password: str, db: Session):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _jwt_secret(), algorithm=ALGORITHM)

@app.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")
        return payload
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.get("/verify-token/{token}")
async def verify_user_token(token: str):
    verify_token(token=token)
    return {"message": "Token is valid"}
