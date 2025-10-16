from pydantic import BaseModel

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks: int
    status: str
    
class DeleteResponse(BaseModel):
    doc_id: str
    deleted: bool
