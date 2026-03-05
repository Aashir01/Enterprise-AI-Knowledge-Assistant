"""
core/ingestion.py
-----------------
IngestionService — converts raw sources into LangChain Document chunks.

Supported sources:
  • PDF        — PyMuPDF (fitz), page-by-page extraction
  • Web URL    — BeautifulSoup HTML scraper
  • SQL DB     — SQLAlchemy query → row documents

Every chunk receives rich metadata:
  • source  — filename / URL / table name
  • page    — PDF page number (1-indexed)
  • url     — full URL for web sources
  • type    — "pdf" | "web" | "sql"
"""

from typing import List

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class IngestionService:
    """Unified service for ingesting and chunking documents from multiple sources."""

    def __init__(self):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            # Prefer splitting on double newlines → single newlines → sentences → words
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        )

    # ------------------------------------------------------------------
    # PDF Ingestion
    # ------------------------------------------------------------------

    def ingest_pdf(self, file_bytes: bytes, filename: str) -> List[Document]:
        """
        Load a PDF from raw bytes, extract text page-by-page, and chunk it.

        Args:
            file_bytes: Raw bytes of the PDF file.
            filename:   Original filename (used as 'source' metadata).

        Returns:
            List of Document chunks, each tagged with source + page metadata.
        """
        logger.info("Ingesting PDF: '%s'", filename)
        page_docs: List[Document] = []

        with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
            total_pages = len(pdf)
            for page_num in range(total_pages):
                page = pdf[page_num]
                text = page.get_text("text").strip()

                if not text:
                    logger.debug("Page %d of '%s' is empty — skipping.", page_num + 1, filename)
                    continue

                page_docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": filename,
                            "page": page_num + 1,
                            "total_pages": total_pages,
                            "type": "pdf",
                        },
                    )
                )

        if not page_docs:
            raise ValueError(f"No extractable text found in '{filename}'. It may be a scanned image PDF.")

        chunks = self._splitter.split_documents(page_docs)
        logger.info(
            "PDF '%s' — %d pages → %d chunks.", filename, len(page_docs), len(chunks)
        )
        return chunks

    # ------------------------------------------------------------------
    # Web URL Ingestion
    # ------------------------------------------------------------------

    def ingest_url(self, url: str) -> List[Document]:
        """
        Scrape a web page, strip navigation/boilerplate, and chunk the content.

        Args:
            url: Full URL including scheme (https://...).

        Returns:
            List of Document chunks tagged with source + url metadata.
        """
        logger.info("Ingesting URL: '%s'", url)

        try:
            response = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; EnterpriseKnowledgeBot/1.0; "
                        "+https://github.com/enterprise-rag)"
                    )
                },
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch URL '%s': %s", url, e)
            raise ValueError(f"Could not fetch '{url}': {e}") from e

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove layout noise — scripts, styles, navbars, footers, ads
        for noisy_tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            noisy_tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        if not text.strip():
            raise ValueError(f"No readable text found at URL: {url}")

        page_title = soup.title.string.strip() if soup.title else url

        doc = Document(
            page_content=text,
            metadata={
                "source": url,
                "url": url,
                "title": page_title,
                "type": "web",
            },
        )

        chunks = self._splitter.split_documents([doc])
        logger.info("URL '%s' ('%s') → %d chunks.", url, page_title, len(chunks))
        return chunks

    # ------------------------------------------------------------------
    # SQL Ingestion
    # ------------------------------------------------------------------

    def ingest_sql(
        self,
        connection_string: str,
        query: str,
        table_name: str = "database",
    ) -> List[Document]:
        """
        Execute a SQL query and convert each row into a searchable text Document.

        Args:
            connection_string: SQLAlchemy URL e.g. "sqlite:///mydb.db"
            query:             SQL SELECT statement to run.
            table_name:        Logical name for metadata (e.g. "products", "employees").

        Returns:
            List of Document chunks, each representing one or more rows.

        Example connection strings:
            SQLite:     sqlite:///path/to/db.sqlite
            PostgreSQL: postgresql://user:pass@localhost:5432/mydb
            MySQL:      mysql+pymysql://user:pass@localhost:3306/mydb
        """
        logger.info("Ingesting SQL | table='%s' | query=%.80s", table_name, query)

        try:
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                columns = list(result.keys())
        except Exception as e:
            logger.error("SQL ingestion failed: %s", e)
            raise ValueError(f"SQL query failed: {e}") from e

        if not rows:
            raise ValueError("SQL query returned no rows.")

        row_docs: List[Document] = []
        for i, row in enumerate(rows):
            # Convert each row to human-readable key: value pairs
            row_dict = dict(zip(columns, row))
            row_text = "\n".join(
                f"{col}: {val}" for col, val in row_dict.items() if val is not None
            )
            row_docs.append(
                Document(
                    page_content=row_text,
                    metadata={
                        "source": table_name,
                        "row": i + 1,
                        "table": table_name,
                        "type": "sql",
                    },
                )
            )

        chunks = self._splitter.split_documents(row_docs)
        logger.info(
            "SQL '%s' — %d rows → %d chunks.", table_name, len(rows), len(chunks)
        )
        return chunks


# ── Singleton ────────────────────────────────────────────────────────────
ingestion_service = IngestionService()
