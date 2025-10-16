# app/services/indexer.py
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import List

from fastapi import UploadFile

from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface  import HuggingFaceEmbeddings


# simple config
DATA_DIR = "app/data/docs"
CHROMA_DIR = "app/data/chroma"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBED_MODEL = "intfloat/e5-base-v2"

_embeddings = None
_vectordb = None

def _emb():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    return _embeddings

def _db():
    global _vectordb
    if _vectordb is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _vectordb = Chroma(
            collection_name="docs",
            persist_directory=CHROMA_DIR,
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
    os.makedirs(DATA_DIR, exist_ok=True)

    # ids and paths
    doc_id = str(uuid.uuid4())
    folder = os.path.join(DATA_DIR, doc_id)
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
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
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
    folder = os.path.join(DATA_DIR, doc_id)
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



