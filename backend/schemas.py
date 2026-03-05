"""
backend/schemas.py
------------------
Pydantic v2 request/response models for all API endpoints.
These schemas enforce input validation and shape API responses consistently.
"""

from typing import List, Optional
from pydantic import BaseModel, field_validator


# ──────────────────────────────────────────────────────────────
# Chat schemas
# ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"

    @field_validator("question")
    @classmethod
    def question_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty.")
        return v.strip()


class SourceDoc(BaseModel):
    source: str
    page: Optional[int] = None
    url: Optional[str] = None
    type: Optional[str] = None   # "pdf" | "web" | "sql"
    content: str                  # First 300 chars of the chunk (for display)


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDoc]
    session_id: str


# ──────────────────────────────────────────────────────────────
# Upload / Ingestion schemas
# ──────────────────────────────────────────────────────────────

class UploadURLRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def url_must_have_scheme(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must begin with 'http://' or 'https://'.")
        return v.strip()


class SQLIngestionRequest(BaseModel):
    connection_string: str
    query: str
    table_name: str = "database"

    @field_validator("query")
    @classmethod
    def query_must_be_select(cls, v: str) -> str:
        if not v.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed for safety.")
        return v.strip()


class UploadResponse(BaseModel):
    status: str           # "success" | "error"
    chunks_indexed: int
    message: str


# ──────────────────────────────────────────────────────────────
# Health schema
# ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    vector_store: str
    doc_count: int
    model: str
