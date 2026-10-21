from streamlit.testing.v1 import AppTest

from app.ui import download_filename, load_sample_text, summary_rows

TIMEOUT = 20


def app_script():
    import json
    from pathlib import Path

    from app.config import Settings
    from app.llm_client import LLMClient
    from app.ui import render_app

    class Fake(LLMClient):
        def generate_json(self, system_instruction, prompt):
            return Path("examples/expected_invoice_output.json").read_text()

    import os

    key = os.environ.get("TEST_KEY") or None
    def factory(settings):
        settings.require_api_key()  # same behaviour as the real create_client
        return Fake()

    render_app(Settings(api_key=key), factory)


def make_app(monkeypatch, key=None):
    if key:
        monkeypatch.setenv("TEST_KEY", key)
    else:
        monkeypatch.delenv("TEST_KEY", raising=False)
    return AppTest.from_function(app_script, default_timeout=TIMEOUT).run()


def test_helpers():
    assert "Northwind" in load_sample_text("invoice")
    assert "Anika" in load_sample_text("resume")
    assert download_filename("invoice") == "invoice_extraction.json"
    rows = dict(summary_rows({"vendor_name": None, "total_amount": 5.0, "skills": ["x"]}))
    assert rows == {"Vendor Name": "Not found", "Total Amount": "5.0"}


def test_header_and_missing_key_warning(monkeypatch):
    at = make_app(monkeypatch)
    assert at.title[0].value == "AI Document Extractor"
    assert any("API key is missing" in w.value for w in at.warning)


def test_empty_input_shows_error(monkeypatch):
    at = make_app(monkeypatch, key="dummy")
    at.button[-1].click().run()
    assert any("enter some document text" in e.value for e in at.error)
    assert not at.success


def test_missing_key_message_on_extract(monkeypatch):
    at = make_app(monkeypatch)
    at.text_area[0].set_value("Some invoice text").run()
    at.button[-1].click().run()
    assert any("API key is missing" in e.value for e in at.error)
    assert at.text_area[0].value == "Some invoice text"  # input preserved
    assert not at.success


def test_sample_button_loads_text_and_extraction_succeeds(monkeypatch):
    at = make_app(monkeypatch, key="dummy")
    at.button[0].click().run()
    assert "Northwind" in at.text_area[0].value
    at.button[-1].click().run()
    assert any("passed schema validation" in s.value for s in at.success)
    assert any("NW-2024-0457" in c.value for c in at.code)
    # go back, text is preserved
    back = [b for b in at.button if "Back" in b.label][0]
    back.click().run()
    assert "Northwind" in at.text_area[0].value


def test_switching_type_clears_old_results(monkeypatch):
    at = make_app(monkeypatch, key="dummy")
    at.text_area[0].set_value("An invoice").run()
    at.radio[0].set_value("resume").run()
    assert at.session_state["doc_type"] == "resume"
    assert at.session_state["result"] is None
