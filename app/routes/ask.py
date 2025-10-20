import os
import httpx
from fastapi import APIRouter, HTTPException
from app.services.indexer import _db
from app.models import AskRequest, AskResponse
from app import config as cfg

router = APIRouter()

@router.post("/", response_model=AskResponse)
async def ask(body: AskRequest):
    """
    Ask the RAG to answer a question based on the provided context.

    Parameters
    ----------
    body : AskRequest
        The question to ask and the context to use.

    Returns
    -------
    AskResponse
        The answer to the question, along with some metadata.

    Raises
    ------
    HTTPException
        If no OPENROUTER_API_KEY is provided, a 500 error is raised.
        If no OPENROUTER_BASE_URL is provided, a 500 error is raised.
        If the question is empty, a 400 error is raised.
        If the OpenRouter API returns an error, a 502 error is raised.
    """
    if not cfg.OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENROUTER_API_KEY")
    if not cfg.OPENROUTER_MODEL:
        raise HTTPException(status_code=500, detail="Missing OPENROUTER_BASE_URL")

    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing 'question'")


    docs = await get_context(question, cfg.RETRIEVAL_K)
    if not docs:
        return AskResponse(
            answer="This information is not available in my current knowledge base.",
            k=cfg.RETRIEVAL_K,
            chunks=0,
            model=None,
            usage=None,
        )

    headers = {
        "Authorization": f"Bearer {cfg.OPENROUTER_API_KEY}", 
        "Content-Type": "application/json",
        "HTTP-Referer": cfg.HTTP_REFERER,
        "X-Title": cfg.HTTP_TITLE,
    }
    payload = {
        "model": cfg.OPENROUTER_MODEL,
        "messages": build_messages(question, docs),
        "temperature": 0,
        "top_p": 1,
        "stream": False, 
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(cfg.HTTP_TIMEOUT_SECONDS)) as client:
        r = await client.post(f"{cfg.OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=payload)
        if r.status_code >= 400:
            
            raise HTTPException(status_code=502, detail=f"OpenRouter error {r.status_code}: {r.text}")
        resp = r.json()

    msg = resp.get("choices", [{}])[0].get("message", {})
    content = (msg.get("content") or "").strip() or "this information is not available in my current knowledge base." 

    return AskResponse(
        answer=content,
        k=cfg.RETRIEVAL_K,
        chunks=len(docs),
        model=resp.get("model"),
        usage=resp.get("usage"),
    )

    
    
#########* helpers

async def get_context(question: str, k: int) -> list[str]:
    """
    Retrieves context documents from the database based on the question.

    Parameters
    ----------
    question : str
        The question to find context for.
    k : int, optional
        The number of context documents to retrieve. Defaults to K.

    Returns
    -------
    list[str]
        A list of context documents as strings.
    """
    db = _db()
    results = db.similarity_search(question, k)
    return [d.page_content.strip() for d in results if getattr(d, "page_content", "").strip()]

def build_messages(question: str, docs: list[str]) -> list[dict]:
    """
    Builds a list of messages in the format required by OpenRouter.

    The system message is a strict instruction to the AI to only use the provided context.
    The user message is the question with the context appended to it.

    Parameters
    ----------
    question : str
        The question to build the messages for.
    docs : list[str]
        A list of context documents as strings.

    Returns
    -------
    list[dict]
        A list of messages in the format required by OpenRouter.
    """
    context_blob = "\n\n".join(docs) if docs else ""
    system = (
        "You are a strict RAG assistant. Use only the provided context to answer. "
        "If the answer is not present in the context, reply exactly: This information is not available in my current knowledge base."
    )
    user = f"Question:\n{question}\n\nContext:\n{context_blob}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
