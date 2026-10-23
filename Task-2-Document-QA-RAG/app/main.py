"""Streamlit user interface for the Document Q&A Assistant.

Run from the project folder with:
    python -m streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make "from app...." imports work no matter how Streamlit starts this file.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.embeddings import get_embeddings  # noqa: E402
from app.ingestion import ingest_file  # noqa: E402
from app.rag_chain import RAGPipeline, build_llm  # noqa: E402
from app.utils import (  # noqa: E402
    AnswerGenerationError,
    ConfigurationError,
    format_size,
    new_session_id,
)
from app.vector_store import SessionVectorStore  # noqa: E402

st.set_page_config(
    page_title="Document Q&A Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 980px;}
h1 {font-weight: 700; letter-spacing: -0.5px; margin-bottom: 0.2rem;}
.subtitle {color: #6b7280; font-size: 1.05rem; margin-bottom: 1.2rem;}
.pill {display: inline-block; padding: 2px 10px; border-radius: 999px;
       background: rgba(99,102,241,0.12); color: #4f46e5; font-size: 0.8rem;
       margin-right: 6px;}
.source-meta {color: #6b7280; font-size: 0.85rem;}
.file-row {padding: 6px 0; border-bottom: 1px solid rgba(128,128,128,0.2);}
</style>
"""


# ---------------------------------------------------------------- state
def init_state() -> None:
    defaults = {
        "session_id": new_session_id(),
        "files": {},  # file_hash -> info dict
        "chat": [],  # list of {"role", "content", "answer"?}
        "last_results": [],  # IngestResult list from the last processing run
        "uploader_key": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


@st.cache_resource(show_spinner=False)
def cached_embeddings(model_name: str):
    return get_embeddings(model_name)


def get_store(settings) -> SessionVectorStore:
    if "store" not in st.session_state:
        embeddings = cached_embeddings(settings.embedding_model)
        st.session_state["store"] = SessionVectorStore(
            st.session_state["session_id"], embeddings, settings.chroma_dir
        )
    return st.session_state["store"]


# ---------------------------------------------------------------- actions
def process_uploads(settings, uploads) -> None:
    results = []
    with st.status("Processing documents...", expanded=True) as status:
        try:
            with st.spinner("Loading the embedding model (first run downloads ~90 MB)..."):
                store = get_store(settings)
        except ConfigurationError as exc:
            status.update(label="Setup problem", state="error")
            st.error(str(exc))
            return

        for upload in uploads:
            st.write(f"Reading **{upload.name}** ...")
            result = ingest_file(
                store,
                upload.name,
                upload.getvalue(),
                settings.max_file_size_bytes,
                settings.chunk_size,
                settings.chunk_overlap,
            )
            results.append(result)
            if result.status in ("added", "skipped") and result.file_hash:
                info = st.session_state["files"].setdefault(
                    result.file_hash,
                    {
                        "name": result.filename,
                        "size": result.size_bytes,
                        "pages": result.pages,
                        "chunks": result.chunks,
                    },
                )
                if result.status == "added":
                    info["chunks"] = result.chunks
        errors = sum(r.status == "error" for r in results)
        status.update(
            label="Done" if not errors else f"Done with {errors} problem(s)",
            state="complete" if not errors else "error",
        )
    st.session_state["last_results"] = results


def reset_documents(settings) -> None:
    store = st.session_state.get("store")
    if store is not None:
        store.clear()
    st.session_state["files"] = {}
    st.session_state["last_results"] = []
    st.session_state["chat"] = []
    st.session_state["uploader_key"] += 1  # empties the upload widget


def remove_file(file_hash: str) -> None:
    store = st.session_state.get("store")
    if store is not None:
        store.remove_file(file_hash)
    st.session_state["files"].pop(file_hash, None)


# ---------------------------------------------------------------- UI parts
def render_sidebar(settings) -> None:
    with st.sidebar:
        st.header("1. Add documents")
        uploads = st.file_uploader(
            "Upload PDF or TXT files",
            type=["pdf", "txt"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state['uploader_key']}",
            help=f"Maximum {settings.max_file_size_mb} MB per file.",
        )
        if st.button(
            "Process documents",
            type="primary",
            disabled=not uploads,
            width="stretch",
        ):
            process_uploads(settings, uploads)

        for result in st.session_state["last_results"]:
            if result.status == "added":
                st.success(f"{result.filename}: {result.message}")
            elif result.status == "skipped":
                st.info(f"{result.filename}: {result.message}")
            else:
                st.error(result.message)

        st.header("2. Your documents")
        files = st.session_state["files"]
        if not files:
            st.caption("No documents processed yet.")
        for file_hash, info in list(files.items()):
            col_name, col_btn = st.columns([5, 1])
            col_name.markdown(
                f"**{info['name']}**  \n"
                f"<span class='source-meta'>{format_size(info['size'])} · "
                f"{info['pages']} page(s) · {info['chunks']} chunks</span>",
                unsafe_allow_html=True,
            )
            if col_btn.button("✕", key=f"rm_{file_hash}", help="Remove this document"):
                remove_file(file_hash)
                st.rerun()

        st.header("3. Manage")
        c1, c2 = st.columns(2)
        if c1.button("Clear chat", width="stretch", disabled=not st.session_state["chat"]):
            st.session_state["chat"] = []
            st.rerun()
        if c2.button("Reset all", width="stretch", help="Delete all documents and chat"):
            reset_documents(settings)
            st.rerun()

        with st.expander("Settings in use"):
            st.write(
                {
                    "Gemini model": settings.gemini_model,
                    "Embedding model": settings.embedding_model,
                    "Chunk size / overlap": f"{settings.chunk_size} / {settings.chunk_overlap}",
                    "Chunks retrieved (TOP_K)": settings.top_k,
                    "Max file size": f"{settings.max_file_size_mb} MB",
                }
            )
            st.caption("Change these in your .env file, then restart the app.")


def render_sources(answer) -> None:
    if not answer.sources:
        return
    label = (
        f"Sources ({len(answer.sources)} passages retrieved)"
        if answer.grounded
        else f"Closest passages found ({len(answer.sources)}) - they did not contain the answer"
    )
    with st.expander(label):
        for number, chunk in enumerate(answer.sources, start=1):
            cited = " · cited in answer" if number in answer.cited_numbers else ""
            st.markdown(
                f"**[{number}] {chunk.label}**  \n"
                f"<span class='source-meta'>distance {chunk.distance:.3f}{cited}</span>",
                unsafe_allow_html=True,
            )
            st.text(chunk.text)
            if number < len(answer.sources):
                st.divider()


def render_welcome(settings) -> None:
    st.markdown("### Getting started")
    st.markdown(
        "1. **Upload** one or more PDF or TXT files in the sidebar.\n"
        "2. Click **Process documents** and wait for the green check.\n"
        "3. **Ask a question** in the box at the bottom of the page.\n"
        "4. Open **Sources** under each answer to see the exact text it used."
    )
    st.caption(
        "Tip: no files handy? Try the files in the `sample_documents/` folder of this project."
    )


def render_privacy_note() -> None:
    with st.expander("Privacy note"):
        st.markdown(
            "- Embeddings (turning text into numbers) run **locally** on your computer.\n"
            "- When you ask a question, the question **and the retrieved document passages** "
            "are sent over the internet to Google's Gemini API to write the answer. "
            "Do not upload confidential documents unless you are comfortable with that.\n"
            "- Free-tier Gemini usage may be used by Google to improve its products; "
            "check Google's current terms.\n"
            "- Your API key stays in your local `.env` file and is never shown here."
        )


# ---------------------------------------------------------------- main
def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    settings = load_settings()

    st.title("📄 Document Q&A Assistant")
    st.markdown(
        "<div class='subtitle'>Ask questions about your own PDF and TXT files. "
        "Answers come only from your documents, with sources.</div>"
        "<span class='pill'>RAG</span><span class='pill'>ChromaDB</span>"
        "<span class='pill'>LangChain</span><span class='pill'>Gemini</span>",
        unsafe_allow_html=True,
    )

    if not settings.has_api_key:
        st.warning(
            "**Gemini API key not set.** You can still upload and process documents, "
            "but answers need a key.\n\n"
            "1. Get a free key at https://aistudio.google.com/apikey\n"
            "2. Copy `.env.example` to `.env`\n"
            "3. Put your key after `GEMINI_API_KEY=`\n"
            "4. Stop and restart the app."
        )

    render_sidebar(settings)
    render_privacy_note()

    if not st.session_state["files"] and not st.session_state["chat"]:
        render_welcome(settings)

    for message in st.session_state["chat"]:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and message.get("error"):
                st.error(message["content"])
            else:
                st.markdown(message["content"])
            if message.get("answer") is not None:
                render_sources(message["answer"])

    question = st.chat_input(
        "Ask a question about your documents...",
        disabled=not st.session_state["files"],
    )
    if not st.session_state["files"]:
        st.caption("Process at least one document to enable the question box.")

    if question:
        st.session_state["chat"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Searching your documents and writing an answer..."):
                    store = get_store(settings)
                    pipeline = RAGPipeline(store, build_llm(settings), settings.top_k)
                    answer = pipeline.ask(question)
                st.markdown(answer.text)
                render_sources(answer)
                st.session_state["chat"].append(
                    {"role": "assistant", "content": answer.text, "answer": answer}
                )
            except (ConfigurationError, AnswerGenerationError) as exc:
                st.error(str(exc))
                st.session_state["chat"].append(
                    {"role": "assistant", "content": str(exc), "error": True}
                )
            except Exception as exc:  # last line of defence - never show a traceback
                msg = f"Something unexpected went wrong ({type(exc).__name__}). Please try again."
                st.error(msg)
                st.session_state["chat"].append(
                    {"role": "assistant", "content": msg, "error": True}
                )


main()
