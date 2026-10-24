from chatbot.config import (
    DEFAULT_MAX_HISTORY_MESSAGES,
    DEFAULT_MODEL,
    MISSING_KEY_MESSAGE,
    load_config,
)


def test_missing_api_key_is_reported_not_raised():
    cfg = load_config(env={})
    assert not cfg.has_api_key
    assert cfg.errors == (MISSING_KEY_MESSAGE,)


def test_blank_api_key_counts_as_missing():
    assert load_config(env={"GOOGLE_API_KEY": "   "}).errors


def test_placeholder_api_key_is_rejected():
    cfg = load_config(env={"GOOGLE_API_KEY": "your_api_key_here"})
    assert not cfg.has_api_key
    assert "placeholder" in cfg.errors[0]


def test_valid_key_and_defaults():
    cfg = load_config(env={"GOOGLE_API_KEY": "abc-123-real-looking"})
    assert cfg.has_api_key and not cfg.errors and not cfg.warnings
    assert cfg.model_name == DEFAULT_MODEL
    assert cfg.temperature is None
    assert cfg.max_history_messages == DEFAULT_MAX_HISTORY_MESSAGES
    assert cfg.enable_task3_agent is False


def test_api_key_never_appears_in_repr():
    cfg = load_config(env={"GOOGLE_API_KEY": "super-secret-key-value"})
    assert "super-secret-key-value" not in repr(cfg)


def test_model_can_be_changed_with_env():
    cfg = load_config(env={"GOOGLE_API_KEY": "k" * 12, "GEMINI_MODEL": "gemini-3.8-flash"})
    assert cfg.model_name == "gemini-3.8-flash"


def test_valid_temperature_is_used():
    cfg = load_config(env={"GOOGLE_API_KEY": "k" * 12, "GEMINI_TEMPERATURE": "0.4"})
    assert cfg.temperature == 0.4


def test_bad_temperature_gives_warning_and_default():
    for bad in ("hot", "5", "-1"):
        cfg = load_config(env={"GOOGLE_API_KEY": "k" * 12, "GEMINI_TEMPERATURE": bad})
        assert cfg.temperature is None
        assert cfg.warnings


def test_bad_history_size_gives_warning_and_default():
    for bad in ("abc", "0", "-3"):
        cfg = load_config(env={"GOOGLE_API_KEY": "k" * 12, "MAX_HISTORY_MESSAGES": bad})
        assert cfg.max_history_messages == DEFAULT_MAX_HISTORY_MESSAGES
        assert cfg.warnings


def test_agent_flag_and_names():
    cfg = load_config(env={
        "GOOGLE_API_KEY": "k" * 12,
        "ENABLE_TASK3_AGENT": "true",
        "TASK3_AGENT_MODULE": "my_agent",
        "TASK3_AGENT_FUNCTION": "ask",
    })
    assert cfg.enable_task3_agent is True
    assert (cfg.task3_agent_module, cfg.task3_agent_function) == ("my_agent", "ask")


def test_dotenv_file_is_read(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GOOGLE_API_KEY=from-dotenv-file-123\n")
    # setenv + delenv makes pytest restore a clean environment afterwards.
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    monkeypatch.delenv("GOOGLE_API_KEY")
    cfg = load_config(dotenv_path=env_file)
    assert cfg.has_api_key and not cfg.errors
