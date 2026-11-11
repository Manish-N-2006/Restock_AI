import os
import logging
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Load .env cleanly from repository root or backend directory without overriding platform env vars
_CURRENT_FILE = Path(__file__).resolve()
_BACKEND_DIR = _CURRENT_FILE.parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
load_dotenv(_REPO_ROOT / ".env", override=False)
load_dotenv(_BACKEND_DIR / ".env", override=False)

BASE_DIR = str(_BACKEND_DIR)
_DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "restock.db").replace("\\", "/")
_DEFAULT_SQLITE_URL = f"sqlite:///{_DEFAULT_SQLITE_PATH}"


def normalize_database_url(url: str) -> str:
    """Normalize Render/Heroku 'postgres://' URLs to SQLAlchemy 2.0-compatible 'postgresql://'."""
    cleaned = (url or "").strip()
    if not cleaned:
        return _DEFAULT_SQLITE_URL
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql://" + cleaned[len("postgres://"):]
    return cleaned


def resolve_database_url() -> str:
    """Resolve database connection string supporting Render DATABASE_URL and local SQLite."""
    raw_url = os.getenv("RESTOCKAI_DATABASE_URL") or os.getenv("DATABASE_URL") or _DEFAULT_SQLITE_URL
    return normalize_database_url(raw_url)


def is_sqlite_url(url: str) -> bool:
    """Return True if the SQLAlchemy URL targets SQLite."""
    return url.lower().startswith("sqlite")


def get_engine_kwargs(url: str) -> Dict[str, Any]:
    """Build dialect-appropriate SQLAlchemy engine keyword arguments."""
    if is_sqlite_url(url):
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    }


SQLALCHEMY_DATABASE_URL = resolve_database_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    **get_engine_kwargs(SQLALCHEMY_DATABASE_URL),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_database_dialect() -> str:
    """Return active SQLAlchemy dialect name (e.g. 'sqlite' or 'postgresql')."""
    return engine.dialect.name


def check_database_connection() -> bool:
    """Verify database connectivity cleanly using a lightweight SELECT 1 query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return False


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
