from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_utils import answer_with_rag
import rag_utils
import uvicorn
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

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://verdict-ai-psi.vercel.app",
        "https://verdict-ai.vercel.app", 
        "http://localhost:3000",
        "http://localhost:3001",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Ensure DB tables exist on startup
@app.on_event("startup")
def on_startup() -> None:
    # Load .env if present
    load_dotenv()
    logger.info("Environment loaded. GEMINI_API_KEY set: %s", bool(os.getenv("GEMINI_API_KEY")))
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured.")
    except Exception as exc:
        logger.exception("Failed to initialize database: %s", exc)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Question(BaseModel):
    query: str

@app.post("/ask")
async def ask_legal_question(payload: Question):
    try:
        answer = answer_with_rag(payload.query)
        return {"answer": answer}
    except FileNotFoundError as exc:
        logger.exception("/ask missing embeddings: %s", exc)
        raise HTTPException(status_code=503, detail="Embeddings not found. Please build the index.")
    except RuntimeError as exc:
        message = str(exc)
        if "GEMINI_API_KEY" in message:
            logger.error("/ask missing GEMINI_API_KEY")
            raise HTTPException(status_code=503, detail="Model API key not configured on server.")
        logger.exception("/ask runtime error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate answer.")
    except Exception as exc:
        logger.exception("/ask failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate answer. Check server logs.")

@app.get("/")
async def root():
    return {"message": "VerdictAI Legal Assistant API"}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "embeddings_index_present": os.path.exists(getattr(rag_utils, "INDEX_PATH", "")),
        "embeddings_metadata_present": os.path.exists(getattr(rag_utils, "META_PATH", "")),
        "gemini_key_configured": bool(os.getenv("GEMINI_API_KEY")),
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

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
