from fastapi import APIRouter, UploadFile, File, HTTPException, Request, status
import os
from app.models import UploadResponse, DeleteResponse
from app.services import indexer

router = APIRouter()

ALLOWED_EXTS = {".txt", ".md", ".pdf"}
MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  

@router.post("/", response_model=UploadResponse, status_code=status.HTTP_200_OK, summary="Upload a file")
async def upload_file(file: UploadFile = File(..., description="txt, md, or pdf")):
    """
    Uploads a file to the index.

    Parameters
    ----------
    file : UploadFile
        The file to upload.

    Returns
    -------
    UploadResponse
        A UploadResponse object indicating the success of the ingestion.

    Raises
    ------
    HTTPException
        If the file type is unsupported, a 400 error is raised.
    HTTPException
        If the file size exceeds the maximum allowed size, a 400 error is raised.
    HTTPException
        If the ingestion fails for any other reason, a 500 error is raised.
    """
    if not ext_supported(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {sorted(ALLOWED_EXTS)}",
        )
        
    #! checks file size only valid for small files (or it can take too much time)
    if await exceeds_size_limit(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size too large. Max: {MAX_UPLOAD_MB}MB",
        )

    
    try:
        result = await indexer.ingest_upload(file)
        return UploadResponse(**result)
    except indexer.UnsupportedTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except indexer.ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except indexer.EmbeddingError as e:
        raise HTTPException(status_code=500, detail="Embedding failed")
    except indexer.UpsertError as e:
        raise HTTPException(status_code=500, detail="Index upsert failed")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error during ingestion")
    
   
   
@router.delete("/{doc_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_file(doc_id: str):
    """
    Deletes a document from the index.

    Parameters
    ----------
    doc_id : str
        The document id to delete.

    Returns
    -------
    DeleteResponse
        A DeleteResponse object indicating the success of the deletion.

    Raises
    ------
    HTTPException
        If the document is not found, a 404 error is raised.
    HTTPException
        If the deletion fails for any other reason, a 500 error is raised.
    """
    try:
        deleted = await indexer.delete_document(doc_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        return DeleteResponse(deleted=True, doc_id=doc_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error during deletion")
   
   
   
#################* helpers 
def ext_supported(filename: str) -> bool:
    """Check if a file extension is supported.
    
    Parameters
    ----------
    filename : str
        The filename to check.
    
    Returns
    -------
    bool
        True if the extension is supported, False otherwise.
    """
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTS
    
async def exceeds_size_limit(file: UploadFile) -> bool:
    """
    Reads the file stream incrementally and stops if it exceeds MAX_UPLOAD_BYTES.
    Avoids loading the whole file in memory.
    """
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            await file.seek(0)  #
            return True

    await file.seek(0)  # reset pointer after check
    return False



@router.get("/debug/chroma")
async def debug_chroma():
    db = indexer._db()
    count = db._collection.count()
    sample = db._collection.get(limit=3)
    return {
        "count": count,
        "sample_ids": sample["ids"],
        "sample_meta": sample["metadatas"]
    }
