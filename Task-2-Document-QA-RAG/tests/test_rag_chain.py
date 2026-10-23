import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import Settings, load_settings
from app.ingestion import ingest_file
from app.prompts import NO_DOCUMENTS_MESSAGE, NO_INFO_MESSAGE
from app.rag_chain import RAGPipeline, build_llm, translate_llm_error
from app.utils import AnswerGenerationError, ConfigurationError

MAX = 1024 * 1024


class RaisingLLM:
    """Stands in for Gemini and raises a chosen exception."""

    def __init__(self, exc):
        self.exc = exc

    def invoke(self, _messages):
        raise self.exc


class RecordingLLM:
    def __init__(self, reply):
        self.reply = reply
        self.messages = None

    def invoke(self, messages):
        from langchain_core.messages import AIMessage

        self.messages = messages
        return AIMessage(content=self.reply)


@pytest.fixture
def filled_store(store, pdf_bytes):
    ingest_file(store, "energy.pdf", pdf_bytes, MAX, 300, 30)
    return store


def _settings(**over):
    base = dict(
        gemini_api_key="real-looking-key",
        gemini_model="gemini-3.5-flash-lite",
        embedding_model="x",
        chunk_size=1000,
        chunk_overlap=150,
        top_k=4,
        max_file_size_mb=10,
        chroma_dir="x",
    )
    base.update(over)
    return Settings(**base)


def test_answer_with_mocked_model_includes_sources(filled_store):
    llm = FakeListChatModel(responses=["Solar panels turn sunlight into electricity [1]."])
    answer = RAGPipeline(filled_store, llm, top_k=2).ask("What do solar panels do?")
    assert answer.grounded is True
    assert "electricity" in answer.text
    assert answer.sources and answer.sources[0].source == "energy.pdf"
    assert answer.sources[0].page == 1
    assert answer.cited_numbers == [1]


def test_prompt_contains_context_question_and_grounding_rules(filled_store):
    llm = RecordingLLM("Answer [1]")
    RAGPipeline(filled_store, llm, top_k=2).ask("Tell me about wind turbines")
    system, human = llm.messages
    assert "ONLY" in system.content
    assert "Tell me about wind turbines" in human.content
    assert "Source: energy.pdf (page" in human.content
    assert "[1]" in human.content


def test_cited_numbers_ignore_invented_references(filled_store):
    llm = FakeListChatModel(responses=["Yes [1] and also [99]."])
    answer = RAGPipeline(filled_store, llm, top_k=2).ask("solar")
    assert answer.cited_numbers == [1]


def test_model_says_insufficient_context(filled_store):
    llm = FakeListChatModel(responses=["INSUFFICIENT_CONTEXT"])
    answer = RAGPipeline(filled_store, llm, top_k=2).ask("Who won the 1998 World Cup?")
    assert answer.grounded is False
    assert answer.text == NO_INFO_MESSAGE
    assert answer.sources  # closest passages are still shown, honestly labelled


def test_empty_model_reply_is_treated_as_no_answer(filled_store):
    llm = FakeListChatModel(responses=["   "])
    assert RAGPipeline(filled_store, llm, top_k=2).ask("solar").grounded is False


def test_no_documents_does_not_call_model(store):
    llm = RaisingLLM(AssertionError("model must not be called"))
    answer = RAGPipeline(store, llm, top_k=4).ask("anything")
    assert answer.text == NO_DOCUMENTS_MESSAGE
    assert answer.grounded is False


def test_empty_question_rejected(filled_store):
    with pytest.raises(ValueError):
        RAGPipeline(filled_store, FakeListChatModel(responses=["x"]), 2).ask("   ")


def test_list_style_model_content_is_joined(filled_store):
    from langchain_core.messages import AIMessage

    class ListLLM:
        def invoke(self, _m):
            return AIMessage(content=[{"type": "text", "text": "Part one. "}, {"type": "text", "text": "Part two [1]"}])

    answer = RAGPipeline(filled_store, ListLLM(), 2).ask("solar")
    assert answer.text == "Part one. Part two [1]"


# ---- error handling -------------------------------------------------
class FakeAPIError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message)
        self.code = code


@pytest.mark.parametrize(
    "exc,expected",
    [
        (FakeAPIError(429, "RESOURCE_EXHAUSTED"), "rate limit"),
        (FakeAPIError(403, "PERMISSION_DENIED"), "API key"),
        (FakeAPIError(401), "API key"),
        (FakeAPIError(404, "model not found"), "GEMINI_MODEL"),
        (FakeAPIError(503), "temporarily unavailable"),
        (ConnectionError("Connection refused"), "internet connection"),
        (TimeoutError("timed out"), "internet connection"),
        (RuntimeError("weird"), "returned an error"),
    ],
)
def test_translate_llm_error(exc, expected):
    friendly = translate_llm_error(exc)
    assert isinstance(friendly, AnswerGenerationError)
    assert expected.lower() in str(friendly).lower()


def test_pipeline_wraps_api_errors(filled_store):
    pipeline = RAGPipeline(filled_store, RaisingLLM(FakeAPIError(429, "quota")), 2)
    with pytest.raises(AnswerGenerationError, match="rate limit"):
        pipeline.ask("solar")


def test_error_message_never_contains_secrets(filled_store):
    secret = "FAKE-TEST-SECRET-VALUE-123"
    pipeline = RAGPipeline(filled_store, RaisingLLM(RuntimeError(f"key={secret}")), 2)
    with pytest.raises(AnswerGenerationError) as info:
        pipeline.ask("solar")
    assert secret not in str(info.value)


# ---- configuration / API key ----------------------------------------
@pytest.mark.parametrize("key", ["", "   ", "your_gemini_api_key_here"])
def test_missing_or_placeholder_api_key_detected(key):
    s = _settings(gemini_api_key=key)
    assert s.has_api_key is False
    with pytest.raises(ConfigurationError, match="API key"):
        build_llm(s)


def test_real_key_detected():
    assert _settings().has_api_key is True


def test_settings_defaults_and_bad_values(monkeypatch, tmp_path):
    for name in ["GEMINI_API_KEY", "GEMINI_MODEL", "CHUNK_SIZE", "CHUNK_OVERLAP", "TOP_K", "MAX_FILE_SIZE_MB"]:
        monkeypatch.delenv(name, raising=False)
    s = load_settings()
    assert (s.chunk_size, s.chunk_overlap, s.top_k, s.max_file_size_mb) == (1000, 150, 4, 10)
    monkeypatch.setenv("CHUNK_SIZE", "abc")
    monkeypatch.setenv("TOP_K", "0")
    monkeypatch.setenv("CHUNK_SIZE", "500")
    monkeypatch.setenv("CHUNK_OVERLAP", "900")  # overlap larger than chunk -> fixed
    s = load_settings()
    assert s.top_k == 4
    assert s.chunk_overlap < s.chunk_size


def test_max_file_size_bytes():
    assert _settings(max_file_size_mb=2).max_file_size_bytes == 2 * 1024 * 1024
