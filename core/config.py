"""
core/config.py
--------------
Centralized settings management using pydantic-settings.
All values are loaded from environment variables / .env file.
"""

from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ----------------------------------------------------------------
    # LLM — Mistral API
    # ----------------------------------------------------------------
    MISTRAL_API_KEY: str
    MISTRAL_MODEL: str = "mistral-large-latest"

    # ----------------------------------------------------------------
    # Vector Store
    # "faiss"  → free, local, no account needed (default)
    # "qdrant" → cloud-scale upgrade (requires Qdrant account)
    # ----------------------------------------------------------------
    VECTOR_STORE: Literal["faiss", "qdrant"] = "faiss"
    FAISS_INDEX_PATH: str = "faiss_index"

    # Qdrant (only needed when VECTOR_STORE=qdrant)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "knowledge_base"

    # ----------------------------------------------------------------
    # Embeddings (free, local — HuggingFace sentence-transformers)
    # ----------------------------------------------------------------
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ----------------------------------------------------------------
    # Chunking & Retrieval
    # ----------------------------------------------------------------
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVER_K: int = 5  # Number of chunks to retrieve per query

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton — import this in all other modules
settings = Settings()
