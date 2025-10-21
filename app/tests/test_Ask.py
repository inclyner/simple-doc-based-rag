
import os
import io
import json
import pytest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from app.routes.ask import router as ask_router
from app.services import indexer as ask_module  # for _db()
from app.routes.files import router as files_router

STRICT_REFUSAL = "This information is not available in my current knowledge base."

# Load envs from .env automatically
load_dotenv()

# ---------------------------
# Environment setup
# ---------------------------

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL")

CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")).resolve()

# Fail early if missing (not skip)
if not OPENROUTER_API_KEY or not OPENROUTER_BASE_URL:
    raise RuntimeError(
        "Missing required environment variables: OPENROUTER_API_KEY or OPENROUTER_BASE_URL. "
        "Please configure them in your .env file."
    )


# ---------------------------
# App and helpers
# ---------------------------

def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ask_router, prefix="/ask")
    app.include_router(files_router, prefix="/files")
    return app


@pytest.fixture(scope="module")
def client():
    app = _build_app()
    return TestClient(app)


def _persist_dir() -> Path:
    return CHROMA_DIR


def _upload_text_file(client: TestClient, name: str, text: str):
    """Uploads a text file via /files and returns JSON with doc_id."""
    file_bytes = io.BytesIO(text.encode("utf-8"))
    r = client.post("/files", files={"file": (name, file_bytes, "text/plain")})
    assert r.status_code in (200, 201), f"Upload failed: {r.text}"
    data = r.json()
    assert "doc_id" in data, f"Upload response missing doc_id: {data}"
    return data


def _delete_doc(client: TestClient, doc_id: str):
    r = client.delete(f"/files/{doc_id}")
    assert r.status_code in (200, 204), f"Delete failed: {r.text}"
    return True


# ---------------------------
# Tests from Developer Log
# ---------------------------


def test_contradiction_context(client):
    """Ask against common knowledge once; context must override model bias."""
    _upload_text_file(client, "contradict.txt", "In our documents, the sky is green.")

    r = client.post("/ask/", json={"question": "What color is the sky?", "k": 4})
    assert r.status_code == 200, r.text

    ans = r.json().get("answer", "").lower()
    assert "green" in ans, f"Expected 'green' in answer, got: {ans}"


def test_out_of_scope_refuses_with_strict_message(client):
    """Ask out of scope -> must refuse with strict message."""
    r = client.post("/ask/", json={"question": "Describe Martian fiscal law."})
    assert r.status_code == 200
    ans = r.json()["answer"].lower()
    assert STRICT_REFUSAL.lower() in ans, f"Expected refusal, got: {ans}"


def test_bad_embeddings_synonyms_still_retrieve(client):
    """Synonyms should work: upload 'car', ask 'automobile'."""
    _upload_text_file(client, "vehicle.txt", "A car is a road vehicle with four wheels.")

    r = client.post("/ask/", json={"question": "Define automobile", "k": 4})
    print("answer:", r.text)
    assert r.status_code == 200, r.text
    ans = r.json()["answer"].lower()
    assert "car" in ans or "road vehicle" in ans


def test_deleted_doc_is_not_answered_after_removal(client):
    """Ask a question from deleted doc -> should not reply with that info after deletion."""
    up = _upload_text_file(client, "temp.txt", "Secret pattern: the sky is plaid.")
    doc_id = up["doc_id"]

    # Ensure it can answer before deletion
    r1 = client.post("/ask/", json={"question": "What pattern is the sky?"})
    assert r1.status_code == 200
    pre_ans = r1.json()["answer"].lower()
    assert "plaid" in pre_ans or "pattern" in pre_ans

    # Delete and ask again
    assert _delete_doc(client, doc_id)

    r2 = client.post("/ask/", json={"question": "What pattern is the sky?"})
    assert r2.status_code == 200
    print("answer:", r2.text)
    assert STRICT_REFUSAL.lower() in r2.json()["answer"].lower()