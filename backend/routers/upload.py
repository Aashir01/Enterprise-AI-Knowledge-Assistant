"""
backend/routers/upload.py
--------------------------
Ingestion endpoints — process and index new knowledge sources.

Endpoints:
  POST /upload/pdf  — Upload a PDF file
  POST /upload/url  — Scrape and index a web URL
  POST /upload/sql  — Query and index a SQL database
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from backend.schemas import SQLIngestionRequest, UploadResponse
from core.ingestion import ingestion_service
from core.vector_store import vector_store_manager
from core.logger import get_logger

router = APIRouter(tags=["Ingestion"])
logger = get_logger(__name__)


# ─────────────────────────────────────────
# PDF Upload
# ─────────────────────────────────────────

@router.post("/upload/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF document, extract text, chunk it, and index it.
    Duplicate chunks are automatically skipped.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    try:
        raw_bytes = await file.read()
        chunks = ingestion_service.ingest_pdf(raw_bytes, file.filename)
        indexed = vector_store_manager.add_documents(chunks)

        return UploadResponse(
            status="success",
            chunks_indexed=indexed,
            message=f"'{file.filename}' processed: {indexed} new chunks indexed "
                    f"({len(chunks) - indexed} duplicates skipped).",
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("PDF ingestion error for '%s': %s", file.filename, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


# ─────────────────────────────────────────
# URL Ingestion
# ─────────────────────────────────────────

@router.post("/upload/url", response_model=UploadResponse)
async def upload_url(url: str = Form(...)):
    """
    Scrape a public web page by URL, chunk the content, and index it.
    """
    if not url.strip().startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400, detail="URL must begin with 'http://' or 'https://'."
        )

    try:
        chunks = ingestion_service.ingest_url(url.strip())
        indexed = vector_store_manager.add_documents(chunks)

        return UploadResponse(
            status="success",
            chunks_indexed=indexed,
            message=f"URL '{url}' indexed: {indexed} new chunks ({len(chunks) - indexed} duplicates skipped).",
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("URL ingestion error for '%s': %s", url, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


# ─────────────────────────────────────────
# SQL Ingestion
# ─────────────────────────────────────────

@router.post("/upload/sql", response_model=UploadResponse)
async def upload_sql(request: SQLIngestionRequest):
    """
    Connect to a SQL database, run a SELECT query, convert rows to
    text documents, and index them.

    Example request body:
    {
        "connection_string": "sqlite:///data/company.db",
        "query": "SELECT name, description, price FROM products",
        "table_name": "products"
    }
    """
    try:
        chunks = ingestion_service.ingest_sql(
            request.connection_string,
            request.query,
            request.table_name,
        )
        indexed = vector_store_manager.add_documents(chunks)

        return UploadResponse(
            status="success",
            chunks_indexed=indexed,
            message=f"SQL table '{request.table_name}' indexed: {indexed} new chunks.",
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("SQL ingestion error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
