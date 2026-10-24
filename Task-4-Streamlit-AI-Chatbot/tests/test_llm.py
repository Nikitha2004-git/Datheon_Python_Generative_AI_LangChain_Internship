import sys
import types

import pytest

from chatbot import llm
from chatbot.config import ConfigError, load_config


def _install_fake_genai(monkeypatch):
    """Put a fake `langchain_google_genai` module in place (no real package/network)."""
    created = []

    class FakeChatGoogleGenerativeAI:
        def __init__(self, **kwargs):
            created.append(kwargs)

    module = types.ModuleType("langchain_google_genai")
    module.ChatGoogleGenerativeAI = FakeChatGoogleGenerativeAI
    monkeypatch.setitem(sys.modules, "langchain_google_genai", module)
    return created


def test_missing_api_key_raises_config_error_with_help():
    cfg = load_config(env={})
    with pytest.raises(ConfigError) as info:
        llm.create_chat_model(cfg)
    assert "GOOGLE_API_KEY" in str(info.value)


def test_model_is_created_with_key_and_model_name(monkeypatch):
    created = _install_fake_genai(monkeypatch)
    cfg = load_config(env={"GOOGLE_API_KEY": "k" * 12, "GEMINI_MODEL": "gemini-3.8-flash"})
    llm.create_chat_model(cfg)
    assert created == [{"model": "gemini-3.8-flash", "google_api_key": "k" * 12}]


def test_temperature_is_only_passed_when_configured(monkeypatch):
    created = _install_fake_genai(monkeypatch)
    cfg = load_config(env={"GOOGLE_API_KEY": "k" * 12, "GEMINI_TEMPERATURE": "0.3"})
    llm.create_chat_model(cfg)
    assert created[0]["temperature"] == 0.3


def test_missing_package_gives_helpful_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "langchain_google_genai", None)  # makes import fail
    cfg = load_config(env={"GOOGLE_API_KEY": "k" * 12})
    with pytest.raises(ConfigError) as info:
        llm.create_chat_model(cfg)
    assert "pip install -r requirements.txt" in str(info.value)


def test_stream_chunks_yields_from_model_stream(fakes):
    model = fakes.Model(["a", "b"])
    msgs = [{"role": "user", "content": "hi"}]
    assert [c.content for c in llm.stream_chunks(model, msgs)] == ["a", "b"]
    assert model.received == [msgs]
