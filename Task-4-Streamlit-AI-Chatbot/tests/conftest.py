"""Shared fakes so the tests never need a real API key or internet."""

from types import SimpleNamespace

import pytest

from chatbot.config import load_config

TEST_KEY = "test-key-1234567890"


class FakePlaceholder:
    """Stands in for st.empty(): records every call so tests can inspect it."""

    def __init__(self):
        self.calls = []

    def markdown(self, text):
        self.calls.append(("markdown", text))

    def empty(self):
        self.calls.append(("empty", None))

    @property
    def last_markdown(self):
        shown = [text for kind, text in self.calls if kind == "markdown"]
        return shown[-1] if shown else None


class FakeChunk:
    """Looks like a LangChain AIMessageChunk (has .content)."""

    def __init__(self, content):
        self.content = content


class FakeModel:
    """Looks like a chat model: .stream(messages) yields chunks.

    `error` is raised after all `chunks` were yielded (use it to test a
    failure in the middle of a stream).
    """

    def __init__(self, chunks=(), error=None):
        self.chunks = list(chunks)
        self.error = error
        self.received = []  # every messages list passed to .stream()

    def stream(self, messages):
        self.received.append(messages)
        for chunk in self.chunks:
            yield FakeChunk(chunk) if isinstance(chunk, (str, list)) else chunk
        if self.error is not None:
            raise self.error


@pytest.fixture
def fakes():
    return SimpleNamespace(Placeholder=FakePlaceholder, Chunk=FakeChunk, Model=FakeModel)


@pytest.fixture
def config():
    """A valid config with a fake key (never a real one)."""
    return load_config(env={"GOOGLE_API_KEY": TEST_KEY})
