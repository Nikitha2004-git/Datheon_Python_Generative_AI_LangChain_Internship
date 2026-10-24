"""Shared test helpers. No real API key or internet is ever needed."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import Settings  # noqa: E402


class ScriptedChatModel(BaseChatModel):
    """A fake LLM that returns pre-written AIMessages in order (supports tool calling)."""

    script: list = []
    cursor: int = 0
    seen: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        if self.cursor >= len(self.script):
            raise RuntimeError("ScriptedChatModel ran out of scripted responses")
        msg = self.script[self.cursor]
        self.cursor += 1
        if isinstance(msg, Exception):
            raise msg
        return ChatResult(generations=[ChatGeneration(message=msg)])


def tool_call_msg(name: str, args: dict, call_id: str, text: str = "") -> AIMessage:
    return AIMessage(content=text, tool_calls=[{"name": name, "args": args, "id": call_id}])


@pytest.fixture
def make_model():
    def _make(*messages):
        return ScriptedChatModel(script=list(messages), cursor=0, seen=[])
    return _make


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "notes.txt").write_text("hello notes", encoding="utf-8")
    (ws / "readme.md").write_text("# Title\nbody", encoding="utf-8")
    (ws / "data.json").write_text('{"a":1,"b":[1,2]}', encoding="utf-8")
    (ws / "budget.txt").write_text("Total: 1000\nSpent: 250", encoding="utf-8")
    (ws / "sub").mkdir()
    (ws / "sub" / "inner.txt").write_text("inner", encoding="utf-8")
    # sensitive / forbidden things that must never be readable
    (ws / ".env").write_text("GOOGLE_API_KEY=SECRET123", encoding="utf-8")
    (ws / "api_key.txt").write_text("SECRET123", encoding="utf-8")
    (ws / "script.py").write_text("print('x')", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("outside secret", encoding="utf-8")
    return ws


@pytest.fixture
def settings(workspace):
    return Settings(
        google_api_key="fake-test-key-123", gemini_model="gemini-test", workspace_dir=workspace,
        max_file_bytes=1000, max_model_calls=6, max_tool_calls=4, search_max_results=3,
        search_timeout=5, llm_timeout=5,
    )
