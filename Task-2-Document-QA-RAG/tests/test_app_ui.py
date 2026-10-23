"""Smoke test: the Streamlit page starts without errors (no network needed)."""

from pathlib import Path

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")

APP = str(Path(__file__).resolve().parent.parent / "app" / "main.py")


def test_app_starts_and_shows_setup_help(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    at = streamlit_testing.AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("Document Q&A" in t.value for t in at.title)
    assert any("API key not set" in w.value for w in at.warning)
