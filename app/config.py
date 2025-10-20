from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Base dir and .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def _as_int(name: str, default: int) -> int:
    val = os.getenv(name)
    try:
        return int(val) if val is not None else default
    except ValueError:
        return default

def _as_float(name: str, default: float) -> float:
    val = os.getenv(name)
    try:
        return float(val) if val is not None else default
    except ValueError:
        return default

def _as_list(name: str, default_list: list[str]) -> list[str]:
    val = os.getenv(name)
    if not val:
        return default_list
    # comma or space separated
    parts = [p.strip() for p in val.replace(",", " ").split() if p.strip()]
    return parts or default_list

def _path_from_env(*names: str, default: str) -> str:
    # First non-empty wins (use CHROMA_PERSIST_DIR for test compat)
    for n in names:
        v = os.getenv(n)
        if v and v.strip():
            return str(Path(v).resolve())
    return str((BASE_DIR.parent / default).resolve())

# OpenRouter
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")

# Retrieval
RETRIEVAL_K: int = _as_int("RETRIEVAL_K", 4)

# Data + Vector store
DATA_DIR: str = _path_from_env("DATA_DIR", default="app/data/docs")
CHROMA_DIR: str = _path_from_env("CHROMA_DIR", "CHROMA_PERSIST_DIR", default="app/data/chroma")
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "docs")

# Embeddings and splitting
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "intfloat/e5-base-v2")
SPLIT_CHUNK_SIZE: int = _as_int("SPLIT_CHUNK_SIZE", 1000)
SPLIT_CHUNK_OVERLAP: int = _as_int("SPLIT_CHUNK_OVERLAP", 150)

# Upload constraints
ALLOWED_EXTS: list[str] = _as_list("ALLOWED_EXTS", [".txt", ".md", ".pdf"])
MAX_UPLOAD_MB: int = _as_int("MAX_UPLOAD_MB", 25)

# HTTP client
HTTP_TIMEOUT_SECONDS: float = _as_float("HTTP_TIMEOUT_SECONDS", 60.0)
HTTP_REFERER: str = os.getenv("HTTP_REFERER", "http://localhost")
HTTP_TITLE: str = os.getenv("HTTP_TITLE", "Simple-RAG-Ask")

# Convenience: bytes from MB
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024
