"""
backend/routers/health.py
--------------------------
GET /health — System health check for deployment monitoring.
"""

from fastapi import APIRouter
from backend.schemas import HealthResponse
from core.config import settings
from core.vector_store import vector_store_manager

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Returns operational status of the RAG system.
    Use this endpoint for load balancer / uptime monitoring.
    """
    return HealthResponse(
        status="ok",
        vector_store=settings.VECTOR_STORE,
        doc_count=vector_store_manager.doc_count,
        model=settings.MISTRAL_MODEL,
    )
