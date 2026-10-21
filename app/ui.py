"""Streamlit user interface.

Session-state keys (mirrors survive widgets being hidden between views):
  doc_type, document_text, view ("input" | "results"), result, error,
  processing_status, validation_status, notice, uploader_n
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import streamlit as st

from app.config import Settings
from app.errors import AppError
from app.extractor import ExtractionResult, extract_document, get_spec, validate_input_text
from app.llm_client import LLMClient, create_client
from app.prompt_templates import DOCUMENT_SPECS
from app.validators import decode_uploaded_file

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
SAMPLE_FILES = {"invoice": "sample_invoice.txt", "resume": "sample_resume.txt"}

CSS = """
<style>
h1, h2, h3 { color: #0B2545; }
.block-container { max-width: 980px; padding-top: 2rem; }
div.stButton > button, div.stDownloadButton > button { width: 100%; border-radius: 8px; min-height: 2.6rem; }
div.stButton > button[kind="primary"] { background: #0B2545; border-color: #0B2545; color: #fff; }
.app-subtitle { color: #1F4E79; font-size: 1.1rem; margin-top: -0.6rem; }
.app-description { color: #3B5573; font-size: 0.95rem; }
</style>
"""

ClientFactory = Callable[[Settings], LLMClient]


# ----------------------------------------------------------------- helpers
def load_sample_text(document_type: str) -> str:
    """Read the bundled sample file for a document type."""
    get_spec(document_type)
    return (EXAMPLES_DIR / SAMPLE_FILES[document_type]).read_text(encoding="utf-8")


def summary_rows(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Scalar fields as (label, text) pairs. Missing values show as 'Not found'."""
    rows = []
    for key, value in data.items():
        if isinstance(value, (list, dict)):
            continue
        label = key.replace("_", " ").title()
        rows.append((label, "Not found" if value is None else str(value)))
    return rows


def download_filename(document_type: str) -> str:
    return f"{document_type}_extraction.json"


# ------------------------------------------------------------------- state
def init_state() -> None:
    defaults = {
        "doc_type": "invoice",
        "document_text": "",
        "view": "input",
        "result": None,
        "error": None,
        "notice": None,
        "processing_status": "Idle",
        "validation_status": "Not run",
        "uploader_n": 0,
        "processing": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_outcome() -> None:
    """Forget any previous result/error so stale output is never shown."""
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.processing_status = "Idle"
    st.session_state.validation_status = "Not run"


def _on_doc_type_change() -> None:
    st.session_state.doc_type = st.session_state.doc_type_widget
    reset_outcome()


def _set_text(text: str) -> None:
    st.session_state.document_text = text
    st.session_state.input_widget = text


def _on_text_change() -> None:
    st.session_state.document_text = st.session_state.input_widget


def _on_sample(document_type: str) -> None:
    st.session_state.doc_type = document_type
    st.session_state.doc_type_widget = document_type
    _set_text(load_sample_text(document_type))
    st.session_state.notice = ("info", f"Sample {document_type} loaded.")
    reset_outcome()


def _on_clear() -> None:
    _set_text("")
    st.session_state.uploader_n += 1  # a new key gives an empty file uploader
    st.session_state.notice = None
    reset_outcome()


def _on_upload(settings: Settings) -> None:
    uploaded = st.session_state.get(f"uploader_{st.session_state.uploader_n}")
    if uploaded is None:
        return
    reset_outcome()
    try:
        text = decode_uploaded_file(uploaded.name, uploaded.getvalue(), settings.max_file_bytes)
    except AppError as exc:
        st.session_state.notice = ("error", exc.user_message)
        return
    _set_text(text)
    st.session_state.notice = ("success", f"Loaded {uploaded.name}.")


def _on_back() -> None:
    st.session_state.view = "input"
    st.session_state.result = None
    st.session_state.validation_status = "Not run"
    st.session_state.processing_status = "Idle"


# ---------------------------------------------------------------- workflow
def run_extraction(settings: Settings, client_factory: ClientFactory) -> None:
    """Validate input, check config, call the AI, validate, store the outcome."""
    if st.session_state.processing:  # guard against duplicate requests
        return
    st.session_state.processing = True
    reset_outcome()
    st.session_state.document_text = st.session_state.get(
        "input_widget", st.session_state.document_text
    )
    doc_type = st.session_state.doc_type
    try:
        validate_input_text(st.session_state.document_text, settings.max_input_chars)
        client = client_factory(settings)  # raises a friendly error if no API key
        st.session_state.processing_status = "Processing"
        with st.spinner("Extracting and validating... this can take a few seconds."):
            result = extract_document(
                doc_type, st.session_state.document_text, client, settings.max_input_chars
            )
    except AppError as exc:
        st.session_state.error = (exc.user_message, exc.details)
        st.session_state.processing_status = "Failed"
        st.session_state.validation_status = "Failed" if exc.details else "Not run"
    else:
        st.session_state.result = result
        st.session_state.processing_status = "Done"
        st.session_state.validation_status = "Valid"
        st.session_state.view = "results"
    finally:
        st.session_state.processing = False


# ------------------------------------------------------------------ render
def _render_header() -> None:
    st.title("AI Document Extractor")
    st.markdown(
        '<p class="app-subtitle">Convert unstructured documents into validated JSON using AI.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="app-description">Paste or upload an invoice or resume. The text is sent '
        "to the AI model, the reply is checked against a strict schema, and only "
        "valid JSON is shown as a success.</p>",
        unsafe_allow_html=True,
    )


def _render_notice() -> None:
    notice = st.session_state.notice
    if notice:
        kind, message = notice
        {"error": st.error, "success": st.success}.get(kind, st.info)(message)


def _render_input_view(settings: Settings, client_factory: ClientFactory) -> None:
    if "doc_type_widget" not in st.session_state:
        st.session_state.doc_type_widget = st.session_state.doc_type
    if "input_widget" not in st.session_state:
        st.session_state.input_widget = st.session_state.document_text

    st.subheader("1. Choose a document type")
    st.radio(
        "Document type",
        list(DOCUMENT_SPECS),
        format_func=lambda key: DOCUMENT_SPECS[key].label,
        horizontal=True,
        key="doc_type_widget",
        on_change=_on_doc_type_change,
        label_visibility="collapsed",
    )
    spec = get_spec(st.session_state.doc_type)

    with st.container(border=True):
        st.subheader("2. Provide the document")
        st.caption(spec.input_help)
        st.caption(f"Fields extracted: {spec.required_fields}")
        st.file_uploader(
            "Upload a .txt file",
            type=["txt"],
            key=f"uploader_{st.session_state.uploader_n}",
            on_change=_on_upload,
            args=(settings,),
        )
        _render_notice()
        left, right = st.columns(2)
        left.button("Load sample invoice", on_click=_on_sample, args=("invoice",))
        right.button("Load sample resume", on_click=_on_sample, args=("resume",))
        st.text_area(
            "Document text",
            height=280,
            placeholder=spec.placeholder,
            key="input_widget",
            on_change=_on_text_change,
        )
        clear_col, extract_col = st.columns(2)
        clear_col.button("Clear input", on_click=_on_clear)
        extract_clicked = extract_col.button("Extract Information", type="primary")

    if extract_clicked:
        run_extraction(settings, client_factory)
        if st.session_state.view == "results":
            st.rerun()

    error = st.session_state.error
    if error:
        message, details = error
        st.error(message)
        if details:
            with st.expander("Validation details"):
                for line in details:
                    st.write(f"- {line}")


def _render_results_view() -> None:
    result: ExtractionResult | None = st.session_state.result
    if result is None:  # should not happen, but never show a fake success
        st.session_state.view = "input"
        st.rerun()
        return
    st.subheader("Results")
    st.success("Extraction succeeded and the data passed schema validation.")
    with st.container(border=True):
        st.markdown("**Extracted fields**")
        for label, value in summary_rows(result.data):
            st.markdown(f"- **{label}:** {value}")
        for key, value in result.data.items():
            if isinstance(value, list):
                st.markdown(f"**{key.replace('_', ' ').title()}**")
                if value and isinstance(value[0], dict):
                    st.dataframe(value, hide_index=True)
                else:
                    st.write(", ".join(value) if value else "Not found")
    st.markdown("**Validated JSON**")
    st.code(result.json_text, language="json")
    st.download_button(
        "Download JSON",
        data=result.json_text,
        file_name=download_filename(result.document_type),
        mime="application/json",
    )
    st.button("Back to input (edit text)", on_click=_on_back)


def _render_status(settings: Settings) -> None:
    with st.expander("Technical status"):
        spec = get_spec(st.session_state.doc_type)
        st.caption(f"Document type: {spec.label}")
        st.caption(f"AI provider: {settings.provider_name} ({settings.model})")
        st.caption(f"Processing status: {st.session_state.processing_status}")
        st.caption(f"Validation status: {st.session_state.validation_status}")
        st.caption(f"API key: {'configured' if settings.is_configured else 'missing'}")


def render_app(settings: Settings, client_factory: ClientFactory = create_client) -> None:
    """Draw the whole page."""
    st.set_page_config(page_title="AI Document Extractor", page_icon="📄", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    _render_header()
    if not settings.is_configured:
        st.warning(
            'Gemini API key is missing. Add your key to the local ".env" file and '
            "restart the application. (You can still explore the interface.)"
        )
    if st.session_state.view == "results":
        _render_results_view()
    else:
        _render_input_view(settings, client_factory)
    _render_status(settings)
