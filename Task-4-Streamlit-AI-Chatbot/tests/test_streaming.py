from chatbot.streaming import CURSOR, EMPTY_REPLY_MESSAGE, chunk_to_text, stream_to_placeholder


# --- chunk_to_text -----------------------------------------------------------

def test_chunk_to_text_handles_plain_string_content(fakes):
    assert chunk_to_text(fakes.Chunk("Hello")) == "Hello"


def test_chunk_to_text_handles_block_lists_and_skips_thinking(fakes):
    blocks = [
        {"type": "thinking", "thinking": "secret reasoning"},
        {"type": "text", "text": "Hel"},
        "lo",
    ]
    assert chunk_to_text(fakes.Chunk(blocks)) == "Hello"


def test_chunk_to_text_ignores_unknown_content(fakes):
    assert chunk_to_text(fakes.Chunk(None)) == ""
    assert chunk_to_text(fakes.Chunk(123)) == ""


# --- rendering ---------------------------------------------------------------

def test_text_grows_chunk_by_chunk_with_cursor(fakes):
    ph = fakes.Placeholder()
    result = stream_to_placeholder(fakes.Model(["Hel", "lo ", "world"]).stream([]), ph)
    shown = [text for kind, text in ph.calls if kind == "markdown"]
    assert shown == ["Hel" + CURSOR, "Hello " + CURSOR, "Hello world" + CURSOR, "Hello world"]
    assert result.ok and result.text == "Hello world"


def test_final_render_has_no_cursor(fakes):
    ph = fakes.Placeholder()
    stream_to_placeholder(iter([fakes.Chunk("Done")]), ph)
    assert ph.last_markdown == "Done"


def test_empty_chunks_are_skipped(fakes):
    ph = fakes.Placeholder()
    result = stream_to_placeholder(iter([fakes.Chunk(""), fakes.Chunk("A"), fakes.Chunk("")]), ph)
    assert result.text == "A"
    assert len([c for c in ph.calls if c[0] == "markdown"]) == 2  # "A▌" and "A"


def test_accepts_plain_string_chunks():
    class P:
        def __init__(self): self.last = None
        def markdown(self, t): self.last = t
        def empty(self): self.last = None
    ph = P()
    assert stream_to_placeholder(["a", "b"], ph).text == "ab"


# --- error handling ------------------------------------------------------------

def test_error_in_the_middle_clears_partial_text_and_reports_error(fakes):
    ph = fakes.Placeholder()
    model = fakes.Model(["partial ", "answer"], error=RuntimeError("503 service down"))
    result = stream_to_placeholder(model.stream([]), ph)
    assert not result.ok
    assert result.text == ""  # partial text is NOT kept, so nothing is duplicated
    assert ph.calls[-1] == ("empty", None)
    assert "RuntimeError" in result.error


def test_error_before_first_chunk(fakes):
    ph = fakes.Placeholder()
    result = stream_to_placeholder(fakes.Model(error=ConnectionError("connection refused")).stream([]), ph)
    assert not result.ok and "internet" in result.error
    assert ph.last_markdown is None


def test_empty_stream_is_reported_as_error(fakes):
    ph = fakes.Placeholder()
    result = stream_to_placeholder(fakes.Model([]).stream([]), ph)
    assert result.error == EMPTY_REPLY_MESSAGE
    assert ph.calls[-1] == ("empty", None)


def test_whitespace_only_stream_is_reported_as_error(fakes):
    result = stream_to_placeholder(fakes.Model(["  ", "\n"]).stream([]), fakes.Placeholder())
    assert result.error == EMPTY_REPLY_MESSAGE


def test_secret_is_hidden_in_error_text(fakes):
    secret = "my-very-secret-key-123"
    model = fakes.Model(error=ValueError(f"bad request for key {secret}"))
    result = stream_to_placeholder(model.stream([]), fakes.Placeholder(), secret=secret)
    assert secret not in result.error
