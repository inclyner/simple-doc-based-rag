# app/services/indexer.py
from __future__ import annotations

import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import List
from fastapi import UploadFile
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface  import HuggingFaceEmbeddings
from app import config as cfg



_embeddings = None
_vectordb = None

def _reset_db():
    """Reset the cached Chroma vectorstore so the next call re-initializes it.
    Useful after destructive operations like deleting a collection.
    """
    global _vectordb
    _vectordb = None

def _emb():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=cfg.EMBED_MODEL,encode_kwargs={"normalize_embeddings": True} # normalize embeddings added because synonym test was failing
)
    return _embeddings

def _db():
    global _vectordb
    if _vectordb is None:
        os.makedirs(cfg.CHROMA_DIR, exist_ok=True)
        _vectordb = Chroma(
            collection_name=cfg.CHROMA_COLLECTION,
            persist_directory=cfg.CHROMA_DIR,
            embedding_function=_emb(),
        )
    return _vectordb


async def ingest_upload(file: UploadFile) -> dict:

    """
    Ingests a file to the index.
    
    Save file -> extract text -> chunk -> embed -> upsert to Chroma.
    
    Parameters
    ----------
    file : UploadFile
        The file to ingest.

    Returns
    -------
    dict
        A dictionary indicating the success of the ingestion, containing
        the document id, original filename, the number of chunks produced,
        and the status of the ingestion.

    Raises
    ------
    ValueError
        If the file type is unsupported, a ValueError is raised.
        If the file size is empty, a ValueError is raised.
        If no chunks are produced, a ValueError is raised.
    """
    os.makedirs(cfg.DATA_DIR, exist_ok=True)

    # ids and paths
    doc_id = str(uuid.uuid4())
    folder = os.path.join(cfg.DATA_DIR, doc_id)
    os.makedirs(folder, exist_ok=True)
    original_path = os.path.join(folder, file.filename)

    # save original
    raw = await file.read()
    if not raw:
        raise ValueError("Empty file")
    with open(original_path, "wb") as f:
        f.write(raw)

    # extract text
    ext = os.path.splitext(file.filename.lower())[1]
    if ext in {".txt", ".md"}:
        text_path = os.path.join(folder, "text.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(raw.decode("utf-8", errors="replace"))
        docs = TextLoader(text_path, encoding="utf-8").load()
    elif ext == ".pdf":
        loader = PyPDFLoader(original_path)
        docs = loader.load()  # one Document per page with page metadata
    else:
        raise ValueError("Unsupported file type")

    # chunk
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.SPLIT_CHUNK_SIZE, chunk_overlap=cfg.SPLIT_CHUNK_OVERLAP
    )
    chunks: List[Document] = splitter.split_documents(docs)
    if not chunks:
        raise ValueError("No chunks produced")

    # minimal metadata
    for i, d in enumerate(chunks):
        d.metadata.update({
            "doc_id": doc_id,
            "filename": file.filename,
            "ord": i,
            "ingested_at": datetime.now().isoformat() + "Z",
        })

    # upsert
    db = _db()
    db.add_documents(chunks)

    
    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
        "status": "indexed",
    }


async def delete_document(doc_id: str) -> bool:
    """
    Deletes a document from the index.

    Parameters
    ----------
    doc_id : str
        The document id to delete.

    Returns
    -------
    bool
        True if the document existed and was deleted, False otherwise.
    """

    _db().delete(where={"doc_id": doc_id})

    # remove folder
    folder = os.path.join(cfg.DATA_DIR, doc_id)
    existed = os.path.isdir(folder)
    print("deleting", folder)
    print("full path", os.path.abspath(folder))
    if existed:
        # simple recursive delete
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except FileNotFoundError:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass
        try:
            os.rmdir(folder)
        except OSError:
            pass

    return existed

async def reset_docs() -> bool:
    """
    Clear all vectors without deleting sqlite files.
    Prefers delete_collection; falls back to batched ID deletes; final fallback is where={}.
    """
    vs = _db()

    client = getattr(vs, "_client", None)
    coll   = getattr(vs, "_collection", None)
    name = None
    if coll is not None:
        name = getattr(coll, "name", None) or getattr(coll, "_name", None)

    if client is not None and name:
        try:
            client.delete_collection(name)  
            _reset_db()
            _ = _db()  # re-initialize to a fresh, empty collection
            data_dir = Path(cfg.DATA_DIR.strip("/docs"))
            if data_dir.exists():
                shutil.rmtree(data_dir, ignore_errors=True)
            return True
        except Exception:
            pass


    return False
