"""
core/rag_chain.py
-----------------
RAGChain — LCEL-based conversational RAG powered by Mistral API.

Uses LangChain Expression Language (LCEL) — compatible with LangChain 0.2+ / 1.x.

Pipeline:
  1. If conversation history exists → condense question to standalone form
  2. Retrieve top-K relevant chunks from the vector store
  3. Inject context + history into a hallucination-safe Mistral prompt
  4. Return grounded answer + source documents
"""

from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_mistralai import ChatMistralAI

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# ── Hallucination-prevention system prompt ───────────────────────────────
_SYSTEM_TEMPLATE = """You are a precise and professional enterprise knowledge assistant.

Your ONLY job is to answer questions based on the CONTEXT DOCUMENTS provided below.

STRICT RULES you MUST follow:
1. Use ONLY information from the provided context. Do NOT use your training knowledge.
2. If the answer is NOT present or cannot be confidently inferred from the context, respond with exactly:
   "I don't know based on the provided documents. Please check the knowledge base or try a different question."
3. Never fabricate facts, statistics, dates, or names.
4. When citing information, briefly reference the source (e.g., "According to [filename]...").
5. Be concise, professional, and structured. Use bullet points for multi-step answers.

CONTEXT DOCUMENTS:
---
{context}
---"""

_CONDENSE_TEMPLATE = (
    "Given the following conversation history and a follow-up question, "
    "rewrite the follow-up question to be a self-contained standalone question. "
    "Return ONLY the reformulated question, nothing else."
)


class RAGChain:
    """
    Conversational RAG chain using LCEL (LangChain Expression Language).
    Maintains per-session message history for multi-turn conversations.
    """

    def __init__(self):
        self._llm: ChatMistralAI | None = None
        # session_id → list of HumanMessage / AIMessage
        self._session_histories: Dict[str, List[BaseMessage]] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Set up the Mistral LLM. Called once at app startup."""
        self._llm = ChatMistralAI(
            model=settings.MISTRAL_MODEL,
            mistral_api_key=settings.MISTRAL_API_KEY,
            temperature=0.1,
            max_retries=3,
        )
        logger.info("RAGChain initialized | model=%s", settings.MISTRAL_MODEL)

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def chat(self, question: str, session_id: str) -> Dict[str, Any]:
        """
        Run a conversational RAG query.

        Args:
            question:   The user's question.
            session_id: Unique identifier for the conversation session.

        Returns:
            {"answer": str, "sources": List[Document]}
        """
        if self._llm is None:
            raise RuntimeError("RAGChain not initialized. Call initialize() first.")

        # Lazy import to avoid circular dependency
        from core.vector_store import vector_store_manager

        if vector_store_manager.doc_count == 0:
            logger.warning("Chat requested but no documents are indexed.")
            return {
                "answer": (
                    "⚠️ No documents have been indexed yet.\n\n"
                    "Please upload a PDF, enter a URL, or connect a SQL database "
                    "using the sidebar before asking questions."
                ),
                "sources": [],
            }

        retriever = vector_store_manager.get_retriever()
        history = self._session_histories.get(session_id, [])

        # ── Step 1: Condense with history (if any) ───────────────────
        if history:
            condense_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", _CONDENSE_TEMPLATE),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{question}"),
                ]
            )
            condense_chain = condense_prompt | self._llm | StrOutputParser()
            standalone_question = condense_chain.invoke(
                {"question": question, "chat_history": history}
            )
            logger.debug("Condensed question: %s", standalone_question)
        else:
            standalone_question = question

        # ── Step 2: Retrieve relevant chunks ─────────────────────────
        docs = retriever.invoke(standalone_question)
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)

        # Log retrieval hits
        for idx, doc in enumerate(docs):
            logger.info(
                "Retrieval hit #%d | source=%-30s | page=%-4s | preview=%.80s",
                idx + 1,
                doc.metadata.get("source", "unknown"),
                doc.metadata.get("page", "N/A"),
                doc.page_content.replace("\n", " "),
            )

        # ── Step 3: Generate grounded answer ─────────────────────────
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _SYSTEM_TEMPLATE),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        qa_chain = qa_prompt | self._llm | StrOutputParser()
        answer = qa_chain.invoke(
            {"context": context, "question": question, "chat_history": history}
        )

        # ── Step 4: Update session history ───────────────────────────
        updated_history = history + [
            HumanMessage(content=question),
            AIMessage(content=answer),
        ]
        self._session_histories[session_id] = updated_history

        return {"answer": answer, "sources": docs}

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def clear_session(self, session_id: str) -> None:
        """Wipe conversation history for a given session."""
        self._session_histories.pop(session_id, None)
        logger.info("Session cleared: %s", session_id)

    def active_sessions(self) -> List[str]:
        """Return list of session IDs with active conversation history."""
        return list(self._session_histories.keys())


# ── Singleton ────────────────────────────────────────────────────────────
rag_chain = RAGChain()
