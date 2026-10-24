from chatbot.errors import describe_error, redact


def test_redact_hides_secret():
    assert redact("key=abcdefgh1234 failed", "abcdefgh1234") == "key=*** failed"


def test_redact_ignores_missing_or_tiny_secret():
    assert redact("hello", None) == "hello"
    assert redact("a b c", "a") == "a b c"  # too short to be a real key


def test_invalid_key_message():
    assert "API key" in describe_error(Exception("API_KEY_INVALID: API key not valid"))
    assert "API key" in describe_error(Exception("403 PERMISSION_DENIED"))


def test_rate_limit_message():
    assert "rate limit" in describe_error(Exception("429 RESOURCE_EXHAUSTED quota exceeded"))


def test_model_not_found_message():
    assert "GEMINI_MODEL" in describe_error(Exception("404 models/gemini-xyz is not found"))


def test_network_message():
    assert "internet" in describe_error(TimeoutError("request timed out"))


def test_safety_message():
    assert "safety" in describe_error(Exception("response was blocked"))


def test_unknown_error_shows_type_and_hides_secret():
    key = "super-secret-key-9999"
    msg = describe_error(KeyError(f"weird {key}"), secret=key)
    assert "KeyError" in msg and key not in msg
