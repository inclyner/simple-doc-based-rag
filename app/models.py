from pydantic import BaseModel, Field

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks: int
    status: str
    
class DeleteResponse(BaseModel):
    doc_id: str
    deleted: bool

class AskRequest(BaseModel):
    question: str = Field(...,json_schema_extra={"title": "Question", "description": "The question to ask", "type": "string", "default": "", "examples": ["How many moon does earth have?"]})

class AskResponse(BaseModel):
    answer: str
    k: int
    chunks: int