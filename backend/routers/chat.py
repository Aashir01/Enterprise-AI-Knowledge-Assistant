"""
backend/routers/chat.py
-----------------------
POST /chat — Conversational RAG query endpoint.

Accepts a question + session_id, runs it through the RAG chain,
and returns the answer with cited source documents.
"""

from fastapi import APIRouter, HTTPException
from backend.schemas import ChatRequest, ChatResponse, SourceDoc
from core.rag_chain import rag_chain
from core.logger import get_logger

router = APIRouter(tags=["Chat"])
logger = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question against the indexed knowledge base.

    - Maintains conversation history per session_id (follow-up questions work).
    - Returns a grounded answer from Mistral + cited source document excerpts.
    - If no docs are indexed, returns a friendly guidance message.
    """
    try:
        result = rag_chain.chat(
            question=request.question,
            session_id=request.session_id,
        )

        sources = [
            SourceDoc(
                source=doc.metadata.get("source", "unknown"),
                page=doc.metadata.get("page"),
                url=doc.metadata.get("url"),
                type=doc.metadata.get("type"),
                content=doc.page_content[:300].strip(),
            )
            for doc in result["sources"]
        ]

        return ChatResponse(
            answer=result["answer"],
            sources=sources,
            session_id=request.session_id,
        )

    except RuntimeError as e:
        # Not initialized / no documents — return 503 Service Unavailable
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(
            "Chat error | session=%s | question=%.80s | error=%s",
            request.session_id,
            request.question,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")
