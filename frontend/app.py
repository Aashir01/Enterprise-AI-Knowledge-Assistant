"""
frontend/app.py
---------------
Enterprise AI Knowledge Assistant — Streamlit Frontend

Features:
 • Professional dark-mode UI with glassmorphism cards
 • Sidebar: Knowledge Source Management (PDF / URL / SQL ingestion)
 • Main area: Chat interface with persistent session history
 • Source citation expanders on every AI response
 • Live backend health status in sidebar
"""

import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ─────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────
# Premium CSS — Dark Mode with Glassmorphism
# ─────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Import Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global reset ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Dark gradient background ── */
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
        color: #e6edf3;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid rgba(48, 54, 61, 0.8);
    }

    /* ── Main header ── */
    .main-header {
        background: linear-gradient(135deg, rgba(88,166,255,0.15) 0%, rgba(163,113,247,0.15) 100%);
        border: 1px solid rgba(88,166,255,0.3);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        backdrop-filter: blur(10px);
    }

    .main-header h1 {
        background: linear-gradient(90deg, #58a6ff, #a371f7, #58a6ff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        animation: shimmer 3s linear infinite;
    }

    @keyframes shimmer {
        0% { background-position: 0% center; }
        100% { background-position: 200% center; }
    }

    .main-header p {
        color: #8b949e;
        margin: 6px 0 0 0;
        font-size: 0.95rem;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(48, 54, 61, 0.6);
        border-radius: 12px;
        padding: 4px 8px;
        margin-bottom: 8px;
        backdrop-filter: blur(6px);
        transition: border-color 0.2s ease;
    }

    [data-testid="stChatMessage"]:hover {
        border-color: rgba(88, 166, 255, 0.4);
    }

    /* ── Source expander ── */
    [data-testid="stExpander"] {
        background: rgba(13, 17, 23, 0.9);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 10px;
        margin-top: 8px;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #1f6feb, #7c3aed);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        padding: 0.4rem 1rem;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(88, 166, 255, 0.35);
        filter: brightness(1.1);
    }

    /* ── Text input ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(22, 27, 34, 0.9);
        border: 1px solid rgba(48, 54, 61, 0.8);
        color: #e6edf3;
        border-radius: 8px;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #58a6ff;
        box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2);
    }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        background: rgba(22, 27, 34, 0.6);
        border: 2px dashed rgba(88, 166, 255, 0.4);
        border-radius: 10px;
    }

    /* ── Select box ── */
    .stSelectbox > div > div {
        background: rgba(22, 27, 34, 0.9);
        border: 1px solid rgba(48, 54, 61, 0.8);
        color: #e6edf3;
        border-radius: 8px;
    }

    /* ── Status badges ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .status-online {
        background: rgba(35, 197, 94, 0.15);
        border: 1px solid rgba(35, 197, 94, 0.4);
        color: #23c55e;
    }

    .status-offline {
        background: rgba(248, 81, 73, 0.15);
        border: 1px solid rgba(248, 81, 73, 0.4);
        color: #f85149;
    }

    /* ── Source card ── */
    .source-card {
        background: rgba(22, 27, 34, 0.95);
        border: 1px solid rgba(88, 166, 255, 0.25);
        border-radius: 8px;
        padding: 10px 14px;
        margin: 6px 0;
        transition: border-color 0.2s;
    }

    .source-card:hover {
        border-color: rgba(88, 166, 255, 0.55);
    }

    /* ── Sidebar section headers ── */
    .sidebar-section {
        color: #8b949e;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 12px 0 4px 0;
    }

    /* ── Chat input ── */
    [data-testid="stChatInput"] > div {
        background: rgba(22, 27, 34, 0.9);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 12px;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0d1117; }
    ::-webkit-scrollbar-thumb { background: rgba(88, 166, 255, 0.4); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #58a6ff; }

    /* ── Divider ── */
    hr { border-color: rgba(48, 54, 61, 0.6) !important; }

    /* ── Success / Error messages ── */
    .stSuccess { border-radius: 8px; }
    .stError { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    # Each message: {"role": "user"|"assistant", "content": str, "sources": list}
    st.session_state.messages = []

if "doc_count" not in st.session_state:
    st.session_state.doc_count = 0


# ─────────────────────────────────────────────────
# Helper: call backend API
# ─────────────────────────────────────────────────
def get_health():
    try:
        r = requests.get(f"{API_URL}/health", timeout=4)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def post_pdf(file_bytes: bytes, filename: str):
    return requests.post(
        f"{API_URL}/upload/pdf",
        files={"file": (filename, file_bytes, "application/pdf")},
        timeout=120,
    )


def post_url(url: str):
    return requests.post(f"{API_URL}/upload/url", data={"url": url}, timeout=60)


def post_sql(connection_string: str, query: str, table_name: str):
    return requests.post(
        f"{API_URL}/upload/sql",
        json={"connection_string": connection_string, "query": query, "table_name": table_name},
        timeout=60,
    )


def post_chat(question: str, session_id: str):
    return requests.post(
        f"{API_URL}/chat",
        json={"question": question, "session_id": session_id},
        timeout=90,
    )


# ─────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h2 style='background: linear-gradient(90deg,#58a6ff,#a371f7);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        "font-size:1.5rem;margin-bottom:4px;'>🧠 Knowledge Assistant</h2>",
        unsafe_allow_html=True,
    )

    # ── Backend health status ────────────────────
    health = get_health()
    if health:
        st.markdown(
            f'<span class="status-badge status-online">● Backend Online</span>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Model: `{health.get('model', 'N/A')}`  |  "
            f"Chunks indexed: **{health.get('doc_count', 0)}**  |  "
            f"Store: `{health.get('vector_store', 'N/A')}`"
        )
        st.session_state.doc_count = health.get("doc_count", 0)
    else:
        st.markdown(
            '<span class="status-badge status-offline">● Backend Offline</span>',
            unsafe_allow_html=True,
        )
        st.caption("Start the API: `uvicorn backend.main:app --port 8000`")

    st.markdown("---")

    # ── Source type selector ─────────────────────
    st.markdown('<div class="sidebar-section">📁 Knowledge Sources</div>', unsafe_allow_html=True)

    source_type = st.selectbox(
        "Source Type",
        ["📄 PDF Document", "🌐 Web URL", "🗄️ SQL Database"],
        label_visibility="collapsed",
    )

    # ─────── PDF ───────
    if source_type == "📄 PDF Document":
        st.markdown("**Upload PDF**")
        uploaded_file = st.file_uploader(
            "Drop a PDF here",
            type=["pdf"],
            label_visibility="collapsed",
        )
        if uploaded_file:
            st.caption(f"📎 `{uploaded_file.name}` • {uploaded_file.size // 1024} KB")

        if st.button("📤 Index PDF", use_container_width=True, disabled=uploaded_file is None):
            with st.spinner("Extracting and indexing PDF…"):
                try:
                    resp = post_pdf(uploaded_file.read(), uploaded_file.name)
                    if resp.ok:
                        data = resp.json()
                        st.success(f"✅ {data['message']}")
                        st.rerun()
                    else:
                        st.error(f"❌ {resp.json().get('detail', 'Upload failed')}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot reach backend. Is it running?")

    # ─────── URL ───────
    elif source_type == "🌐 Web URL":
        st.markdown("**Scrape a Web Page**")
        url_input = st.text_input("URL", placeholder="https://docs.example.com/guide")

        if st.button("🌐 Index URL", use_container_width=True, disabled=not url_input.strip()):
            with st.spinner("Scraping and indexing…"):
                try:
                    resp = post_url(url_input.strip())
                    if resp.ok:
                        st.success(f"✅ {resp.json()['message']}")
                        st.rerun()
                    else:
                        st.error(f"❌ {resp.json().get('detail', 'Failed')}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot reach backend.")

    # ─────── SQL ───────
    elif source_type == "🗄️ SQL Database":
        st.markdown("**SQL Connector**")
        conn_str = st.text_input("Connection String", placeholder="sqlite:///data/company.db")
        query = st.text_area("SQL Query", placeholder="SELECT id, title, description FROM articles", height=90)
        table_name = st.text_input("Table / Source Name", value="database")

        if st.button("🗄️ Index SQL", use_container_width=True, disabled=not (conn_str and query)):
            with st.spinner("Querying database and indexing…"):
                try:
                    resp = post_sql(conn_str, query, table_name)
                    if resp.ok:
                        st.success(f"✅ {resp.json()['message']}")
                        st.rerun()
                    else:
                        st.error(f"❌ {resp.json().get('detail', 'Failed')}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot reach backend.")

    st.markdown("---")

    # ── Session management ───────────────────────
    st.markdown('<div class="sidebar-section">⚙️ Session</div>', unsafe_allow_html=True)
    st.caption(f"Session ID: `{st.session_state.session_id[:16]}…`")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='color:#8b949e;font-size:0.75rem;text-align:center;'>"
        "Enterprise AI Knowledge Assistant<br>Powered by Mistral + FAISS + LangChain"
        "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────

# ── Header ───────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
        <h1>🧠 Enterprise Knowledge Assistant</h1>
        <p>Ask questions about your indexed documents. Every answer is grounded in your knowledge base with full source citations.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Empty state ───────────────────────────────────
if st.session_state.doc_count == 0 and not st.session_state.messages:
    st.markdown(
        """
        <div style="
            text-align:center;
            padding:48px 24px;
            background:rgba(22,27,34,0.6);
            border:1px solid rgba(48,54,61,0.6);
            border-radius:16px;
            margin:24px 0;
        ">
            <div style="font-size:3rem;margin-bottom:16px;">📂</div>
            <h3 style="color:#e6edf3;margin:0 0 8px;">No documents indexed yet</h3>
            <p style="color:#8b949e;margin:0;">
                Use the sidebar to upload a <strong>PDF</strong>, enter a <strong>Web URL</strong>,
                or connect a <strong>SQL database</strong> — then start asking questions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Chat message history ──────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])

        # Source citations for assistant messages
        sources = msg.get("sources", [])
        if sources and msg["role"] == "assistant":
            with st.expander(f"📄 {len(sources)} Source{'s' if len(sources) != 1 else ''} cited"):
                for i, src in enumerate(sources, 1):
                    src_label = src.get("source", "unknown")
                    src_page = src.get("page")
                    src_url = src.get("url")
                    src_type = src.get("type", "")
                    src_content = src.get("content", "")

                    type_icon = {"pdf": "📄", "web": "🌐", "sql": "🗄️"}.get(src_type, "📎")

                    st.markdown(
                        f"""
                        <div class="source-card">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                                <span style="color:#58a6ff;font-weight:600;font-size:0.85rem;">
                                    {type_icon} Source {i}: <code style="color:#a371f7">{src_label}</code>
                                    {'— Page ' + str(src_page) if src_page else ''}
                                </span>
                                {'<a href="' + src_url + '" target="_blank" style="color:#58a6ff;font-size:0.75rem;">🔗 Open</a>' if src_url else ''}
                            </div>
                            <div style="color:#8b949e;font-size:0.82rem;line-height:1.5;border-left:2px solid rgba(88,166,255,0.3);padding-left:10px;">
                                {src_content}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


# ── Chat input ────────────────────────────────────
if prompt := st.chat_input("Ask a question about your knowledge base…"):
    # Display user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Searching knowledge base…"):
            try:
                resp = post_chat(prompt, st.session_state.session_id)

                if resp.ok:
                    data = resp.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])

                    st.markdown(answer)

                    if sources:
                        with st.expander(f"📄 {len(sources)} Source{'s' if len(sources) != 1 else ''} cited"):
                            for i, src in enumerate(sources, 1):
                                src_label = src.get("source", "unknown")
                                src_page = src.get("page")
                                src_url = src.get("url")
                                src_type = src.get("type", "")
                                src_content = src.get("content", "")
                                type_icon = {"pdf": "📄", "web": "🌐", "sql": "🗄️"}.get(src_type, "📎")

                                st.markdown(
                                    f"""
                                    <div class="source-card">
                                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                                            <span style="color:#58a6ff;font-weight:600;font-size:0.85rem;">
                                                {type_icon} Source {i}: <code style="color:#a371f7">{src_label}</code>
                                                {'— Page ' + str(src_page) if src_page else ''}
                                            </span>
                                            {'<a href="' + src_url + '" target="_blank" style="color:#58a6ff;font-size:0.75rem;">🔗 Open</a>' if src_url else ''}
                                        </div>
                                        <div style="color:#8b949e;font-size:0.82rem;line-height:1.5;border-left:2px solid rgba(88,166,255,0.3);padding-left:10px;">
                                            {src_content}
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                    # Persist to session state
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "sources": sources}
                    )

                else:
                    error_detail = resp.json().get("detail", "An error occurred.")
                    st.error(f"❌ {error_detail}")
                    st.session_state.messages.append(
                        {"role": "assistant", "content": f"⚠️ {error_detail}", "sources": []}
                    )

            except requests.exceptions.ConnectionError:
                err = "❌ Cannot connect to the backend. Make sure the API is running on port 8000."
                st.error(err)
                st.session_state.messages.append(
                    {"role": "assistant", "content": err, "sources": []}
                )
            except Exception as e:
                err = f"❌ Unexpected error: {e}"
                st.error(err)
                st.session_state.messages.append(
                    {"role": "assistant", "content": err, "sources": []}
                )
