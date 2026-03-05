FROM python:3.11-slim

# ── System dependencies ────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ──────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ────────────────────────────────
# Copy only requirements first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Download the embedding model at build time ─────────────────
# This avoids the delay on first request in production.
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# ── Copy application source ────────────────────────────────────
COPY . .

# ── Runtime directories ────────────────────────────────────────
RUN mkdir -p faiss_index logs data

# ── Expose ports ───────────────────────────────────────────────
EXPOSE 8000   
# FastAPI (backend)
EXPOSE 8501   
# Streamlit (frontend)

# ── Default command: run FastAPI backend ───────────────────────
# Override in docker-compose for the frontend service.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
