"""
core/vector_store.py
--------------------
VectorStoreManager — handles FAISS (local/free) and Qdrant (cloud) vector stores.

Key features:
 - Deduplication via MD5 content hash (prevents re-indexing the same chunk)
 - Rich metadata attached to every chunk (source, page, URL, type)
 - Lazy FAISS initialization (index is created on first document ingest)
 - Transparent FAISS disk persistence after every add operation
 - Qdrant: auto-creates the collection if it doesn't exist

Usage:
    from core.vector_store import vector_store_manager
    vector_store_manager.initialize()
    vector_store_manager.add_documents(docs)
    retriever = vector_store_manager.get_retriever()
"""

import hashlib
from pathlib import Path
from typing import List, Optional

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class VectorStoreManager:
    """
    Manages the active vector store (FAISS or Qdrant).
    Always call `initialize()` once at application startup.
    """

    def __init__(self):
        self._store = None
        self._embeddings: Optional[HuggingFaceEmbeddings] = None
        self._indexed_hashes: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Load or create the vector store.
        Embeddings run locally (HuggingFace sentence-transformers) — no API key needed.
        """
        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        self._embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        if settings.VECTOR_STORE == "faiss":
            self._store = self._init_faiss()
        elif settings.VECTOR_STORE == "qdrant":
            self._store = self._init_qdrant()
        else:
            raise ValueError(f"Unsupported VECTOR_STORE value: '{settings.VECTOR_STORE}'")

        logger.info(
            "Vector store ready | type=%s | chunks≈%d",
            settings.VECTOR_STORE,
            self.doc_count,
        )

    def add_documents(self, docs: List[Document]) -> int:
        """
        Deduplicate by content hash and add new chunks to the vector store.
        Returns the count of newly indexed chunks (duplicates are skipped).
        """
        if not docs:
            return 0

        new_docs = []
        for doc in docs:
            h = _md5(doc.page_content)
            if h not in self._indexed_hashes:
                self._indexed_hashes.add(h)
                new_docs.append(doc)

        dupe_count = len(docs) - len(new_docs)
        if not new_docs:
            logger.info("All %d chunks already indexed — skipping.", dupe_count)
            return 0

        # First-time FAISS initialization requires an initial document set
        if self._store is None and settings.VECTOR_STORE == "faiss":
            logger.info("Creating new FAISS index with %d initial chunks.", len(new_docs))
            self._store = FAISS.from_documents(new_docs, self._embeddings)
        else:
            self._store.add_documents(new_docs)

        # Persist FAISS index to disk after every write
        if settings.VECTOR_STORE == "faiss":
            self._store.save_local(settings.FAISS_INDEX_PATH)

        logger.info(
            "Indexed %d new chunks | skipped %d duplicates | total≈%d",
            len(new_docs),
            dupe_count,
            self.doc_count,
        )
        return len(new_docs)

    def get_retriever(self):
        """
        Return a LangChain retriever for the current vector store.
        Raises RuntimeError if no documents have been indexed yet.
        """
        if self._store is None:
            raise RuntimeError(
                "No documents indexed yet. Upload a PDF, URL, or SQL data source first."
            )
        return self._store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.RETRIEVER_K},
        )

    @property
    def doc_count(self) -> int:
        """Approximate number of currently indexed chunks."""
        try:
            if settings.VECTOR_STORE == "faiss" and self._store is not None:
                return self._store.index.ntotal
        except Exception:
            pass
        return len(self._indexed_hashes)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _init_faiss(self) -> Optional[FAISS]:
        """Load an existing FAISS index from disk (or return None if none exists)."""
        index_path = Path(settings.FAISS_INDEX_PATH)
        if index_path.exists():
            logger.info("Loading existing FAISS index from '%s'.", index_path)
            store = FAISS.load_local(
                str(index_path),
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
            # Rebuild deduplication hash cache from stored documents
            for doc in store.docstore._dict.values():
                self._indexed_hashes.add(_md5(doc.page_content))
            logger.info("FAISS index loaded | chunks=%d", len(self._indexed_hashes))
            return store
        else:
            logger.info("No existing FAISS index — will create on first document ingest.")
            return None

    def _init_qdrant(self):
        """
        Connect to Qdrant and create the collection if it does not exist.
        Requires: QDRANT_URL and (for cloud) QDRANT_API_KEY in .env.

        For Qdrant Cloud: https://cloud.qdrant.io/
        For local Qdrant: docker run -p 6333:6333 qdrant/qdrant
        """
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        from langchain_qdrant import QdrantVectorStore

        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )

        existing = [c.name for c in client.get_collections().collections]
        if settings.QDRANT_COLLECTION not in existing:
            # all-MiniLM-L6-v2 produces 384-dimensional vectors
            client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection '%s'.", settings.QDRANT_COLLECTION)
        else:
            logger.info("Using existing Qdrant collection '%s'.", settings.QDRANT_COLLECTION)

        return QdrantVectorStore(
            client=client,
            collection_name=settings.QDRANT_COLLECTION,
            embedding=self._embeddings,
        )


def _md5(text: str) -> str:
    """Fast content hash for deduplication."""
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()


# ── Singleton — import this everywhere ──────────────────────────────────
vector_store_manager = VectorStoreManager()
