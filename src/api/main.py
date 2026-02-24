"""Phase 3 – FastAPI application: REST interface for the Obsidian Cloud Brain."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.retrieval.rag import ask

app = FastAPI(
    title="Obsidian Cloud Brain API",
    description="Ask questions about your Obsidian notes via a RAG pipeline on Azure.",
    version="1.0.0",
)


# ── Request / Response models ──────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, example="What are my notes on Docker?")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of sources to retrieve")


class Source(BaseModel):
    title: str
    path: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", summary="Health check")
async def root() -> dict:
    return {"status": "ok", "service": "Obsidian Cloud Brain"}


@app.get("/health", summary="Detailed health check")
async def health() -> dict:
    return {"status": "healthy", "version": app.version}


@app.post("/ask", response_model=AskResponse, summary="Ask a question about your notes")
async def ask_endpoint(request: AskRequest) -> AskResponse:
    """
    Send a question to the RAG pipeline.

    - Retrieves relevant chunks from **Azure AI Search** (hybrid vector + keyword).
    - Sends the context + question to **GPT-4o** on Azure OpenAI.
    - Returns the answer and the sources.
    """
    try:
        result = ask(request.question, top_k=request.top_k)
        return AskResponse(
            answer=result["answer"],
            sources=[Source(**s) for s in result["sources"]],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
