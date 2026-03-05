# 🧠 Enterprise AI Knowledge Assistant (RAG System)

![Enterprise Knowledge Assistant](docs/assets/app_screenshot.png)

A production-grade **Retrieval-Augmented Generation (RAG)** system built to securely index and query your private data. Upload PDFs, scrape web pages, and connect SQL databases — then ask questions answered strictly from your knowledge base with full source citations.

**Stack**: FastAPI · LangChain · Mistral API · FAISS (local) / Qdrant (cloud) · Streamlit · Docker

---

## 📁 Project Structure

```
├── backend/                  # FastAPI application
│   ├── main.py               # App entry point, middleware, lifespan
│   ├── schemas.py            # Pydantic request/response models
│   └── routers/
│       ├── chat.py           # POST /chat
│       ├── upload.py         # POST /upload/pdf, /url, /sql
│       └── health.py         # GET /health
│
├── core/                     # Business logic
│   ├── config.py             # Settings from .env
│   ├── logger.py             # Structured logging
│   ├── vector_store.py       # FAISS / Qdrant manager
│   ├── ingestion.py          # PDF, URL, SQL ingestion pipelines
│   └── rag_chain.py          # ConversationalRetrievalChain (Mistral)
│
├── frontend/
│   └── app.py                # Streamlit UI
│
├── data/                     # Drop sample documents here
├── logs/                     # Auto-created on first run
├── faiss_index/              # Auto-created on first document ingest
│
├── requirements.txt
├── .env.template             # Copy to .env and fill in your keys
├── Dockerfile
└── docker-compose.yaml
```

---

## ⚡ Quick Start (Local)

### 1. Clone & enter the project

```bash
cd "Enterprise AI Knowledge Assistant (RAG System)"
```

### 2. Set up environment

```bash
copy .env.template .env
```

Open `.env` and paste your **Mistral API key** (get one at [console.mistral.ai](https://console.mistral.ai/)):

```
MISTRAL_API_KEY=your_key_here
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note**: First run will download the `all-MiniLM-L6-v2` embedding model (~90 MB). This is a one-time download.

### 4. Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### 5. Start the frontend (new terminal)

```bash
streamlit run frontend/app.py
```

Open **http://localhost:8501** in your browser.

---

## 🔑 Getting Your Mistral API Key

1. Go to [console.mistral.ai](https://console.mistral.ai/)
2. Sign up / log in
3. Navigate to **API Keys** → **Create new key**
4. Paste the key into your `.env` file as `MISTRAL_API_KEY=...`

---

## 🐳 Docker Deployment

```bash
# Build and start both services
docker compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System status, doc count, model |
| `POST` | `/upload/pdf` | Upload & index a PDF file |
| `POST` | `/upload/url` | Scrape & index a web page |
| `POST` | `/upload/sql` | Query & index a SQL database |
| `POST` | `/chat` | Ask a question (RAG pipeline) |

### Chat example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?", "session_id": "user-1"}'
```

### PDF upload example

```bash
curl -X POST http://localhost:8000/upload/pdf \
  -F "file=@data/company_policy.pdf"
```

---

## 🔄 Switching to Qdrant (Cloud Scale)

When you need multi-user scale or cloud persistence, switch from FAISS to Qdrant:

### Option A — Qdrant Cloud (recommended for production)

1. Create a free cluster at [cloud.qdrant.io](https://cloud.qdrant.io/)
2. Copy your **Cluster URL** and **API Key**
3. Update `.env`:
   ```
   VECTOR_STORE=qdrant
   QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
   QDRANT_API_KEY=your_qdrant_api_key
   QDRANT_COLLECTION=knowledge_base
   ```
4. Restart the backend — the collection is auto-created.

### Option B — Local Qdrant via Docker

```bash
docker run -d -p 6333:6333 qdrant/qdrant:latest
```

Then set `.env`:
```
VECTOR_STORE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=     # (leave blank for local)
```

For Docker Compose, uncomment the `qdrant` service block in `docker-compose.yaml`.

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MISTRAL_API_KEY` | *(required)* | Your Mistral API key |
| `MISTRAL_MODEL` | `mistral-large-latest` | Mistral model name |
| `VECTOR_STORE` | `faiss` | `faiss` or `qdrant` |
| `FAISS_INDEX_PATH` | `faiss_index` | Local FAISS index directory |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `QDRANT_API_KEY` | *(blank)* | Qdrant API key (cloud only) |
| `QDRANT_COLLECTION` | `knowledge_base` | Qdrant collection name |
| `CHUNK_SIZE` | `1000` | Text chunk size (characters) |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `RETRIEVER_K` | `5` | Top-K chunks to retrieve per query |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace embedding model |

---

## 🏛️ Architecture

```
User Question
     │
     ▼
[Streamlit UI]
     │ POST /chat
     ▼
[FastAPI Backend]
     │
     ├── ConversationBufferMemory (per session)
     │
     ├── Retriever → [FAISS / Qdrant]
     │       ↑
     │   HuggingFace Embeddings (local, free)
     │
     └── Mistral API (mistral-large-latest)
             │
             ▼
         Answer + Source Citations
```

**Deduplication**: Every chunk is MD5-hashed before indexing — re-uploading the same document does not create duplicate entries.

**Hallucination prevention**: The system prompt strictly instructs Mistral to answer *only* from retrieved context and say "I don't know" if the answer isn't found.

---

## 📝 License

MIT — free to use and modify.
