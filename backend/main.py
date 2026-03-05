"""
backend/main.py
---------------
Enterprise AI Knowledge Assistant — FastAPI Application Entry Point.

Startup sequence (via `lifespan`):
  1. Initialize vector store (load existing FAISS index or connect to Qdrant).
  2. Initialize RAG chain (set up Mistral LLM client).

Middleware:
  - CORS: allows Streamlit frontend on any port.
  - Request timer: logs every request with method, path, status, and latency.

Run with:
    uvicorn backend.main:app --reload --port 8000
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routers import chat, health, upload
from core.logger import get_logger
from core.rag_chain import rag_chain
from core.vector_store import vector_store_manager

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────
# Lifespan — startup / shutdown
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize heavy components at startup."""
    logger.info("=" * 60)
    logger.info("  Enterprise AI Knowledge Assistant — STARTING UP")
    logger.info("=" * 60)

    # 1. Initialize vector store (load existing index if present)
    vector_store_manager.initialize()

    # 2. Initialize RAG chain (connects to Mistral API)
    rag_chain.initialize()

    logger.info("=" * 60)
    logger.info("  System ready | docs=%d | store=%s", vector_store_manager.doc_count, "FAISS/Qdrant")
    logger.info("=" * 60)

    yield  # ── Application runs here ──

    logger.info("Enterprise Knowledge Assistant shutting down.")


# ──────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    description=(
        "Production-grade RAG system: upload PDFs, web pages, or SQL data, "
        "then ask questions answered exclusively from your knowledge base."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────
# Allow Streamlit frontend (any port) and local dev tools.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with timing info."""
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%-6s %-40s → %d | %.1f ms",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    return response


# ── Global exception handler ─────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An internal server error occurred."})


# ── Register routers ─────────────────────────────────────────
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(chat.router)
