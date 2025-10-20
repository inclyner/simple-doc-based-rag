from app import config as cfg
from fastapi import FastAPI
from app.routes import files, ask


app = FastAPI(
    title="RAG Chatbot API",
    description="RAG with document upload and query endpoints.",
    version="0.1.0",
)

app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(ask.router, prefix="/ask", tags=["ask"])


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}