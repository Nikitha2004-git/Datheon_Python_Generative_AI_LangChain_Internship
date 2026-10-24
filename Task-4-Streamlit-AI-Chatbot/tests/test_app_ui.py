"""UI smoke tests using Streamlit's built-in AppTest (runs app.py without a browser).

Skipped automatically if Streamlit is not installed. No API key or internet is
used: the model is replaced by a fake.
"""

from pathlib import Path

import pytest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def _isolate_env(monkeypatch, tmp_path, key=None):
    import chatbot.config as config_module

    monkeypatch.setattr(config_module, "PROJECT_ROOT", tmp_path)  # so no real .env is read
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    monkeypatch.delenv("GOOGLE_API_KEY")
    if key:
        monkeypatch.setenv("GOOGLE_API_KEY", key)


def test_app_shows_helpful_error_when_api_key_missing(monkeypatch, tmp_path):
    testing = pytest.importorskip("streamlit.testing.v1")
    _isolate_env(monkeypatch, tmp_path)
    at = testing.AppTest.from_file(APP_PATH, default_timeout=20).run()
    assert not at.exception
    assert any("GOOGLE_API_KEY" in e.value for e in at.error)


def test_app_chat_flow_and_new_chat_with_fake_model(monkeypatch, tmp_path, fakes):
    testing = pytest.importorskip("streamlit.testing.v1")
    _isolate_env(monkeypatch, tmp_path, key="test-key-1234567890")
    import chatbot.llm as llm_module

    monkeypatch.setattr(llm_module, "create_chat_model", lambda cfg: fakes.Model(["Hello ", "friend"]))

    at = testing.AppTest.from_file(APP_PATH, default_timeout=20).run()
    assert not at.exception and not at.error

    at.chat_input[0].set_value("Hi").run()
    assert not at.exception
    assert at.session_state["messages"] == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello friend"},
    ]

    at.button(key="new_chat").click().run()
    assert at.session_state["messages"] == []
