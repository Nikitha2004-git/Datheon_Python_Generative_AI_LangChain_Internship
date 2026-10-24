"""Builds the tool-calling agent and runs it, producing a transparent action trace.

Uses ``langchain.agents.create_agent`` (LangChain 1.x). The LLM itself decides which tool to
call (native function/tool calling). We only: set limits, stream the steps, and record them.
Only actions, tool inputs, observations and the final answer are shown - never hidden reasoning.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_core.messages import AIMessage, ToolMessage

from .config import Settings
from .llm import get_llm
from .prompts import SYSTEM_PROMPT
from .tools import build_tools

MAX_INPUT_CHARS = 200
MAX_OBSERVATION_CHARS = 600


@dataclass
class TraceEvent:
    kind: str  # user_query | action | observation | final | error
    text: str
    tool: str | None = None
    step: int = 0


@dataclass
class RunResult:
    final_answer: str
    events: list[TraceEvent] = field(default_factory=list)
    ok: bool = True
    tool_calls: int = 0


def truncate(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + f"... [truncated, {len(text)} chars]"


def message_text(content) -> str:
    """Extract plain text from a message (Gemini may return a list of content blocks)."""
    if isinstance(content, str):
        return content.strip()
    parts = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
    return "\n".join(p for p in parts if p).strip()


class AgentRunner:
    def __init__(self, settings: Settings, llm=None, tools=None,
                 on_event: Callable[[TraceEvent], None] | None = None):
        self.settings = settings
        self.on_event = on_event or (lambda event: None)
        self.llm = llm if llm is not None else get_llm(settings)  # may raise MissingAPIKeyError
        self.tools = tools if tools is not None else build_tools(settings)
        self.graph = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
            middleware=[
                ModelCallLimitMiddleware(run_limit=settings.max_model_calls, exit_behavior="end"),
                ToolCallLimitMiddleware(run_limit=settings.max_tool_calls, exit_behavior="continue"),
            ],
        )

    # -- helpers -------------------------------------------------------------------------
    def _emit(self, result: RunResult, event: TraceEvent) -> None:
        result.events.append(event)
        self.on_event(event)

    def _scrub(self, text: str) -> str:
        key = self.settings.google_api_key
        return text.replace(key, "***") if key and key in text else text

    # -- main entry ----------------------------------------------------------------------
    def run(self, query: str) -> RunResult:
        result = RunResult(final_answer="")
        query = (query or "").strip()
        if not query:
            result.ok = False
            result.final_answer = "Please type a question."
            return result
        self._emit(result, TraceEvent("user_query", query))
        step = 0
        last_text = ""
        try:
            stream = self.graph.stream(
                {"messages": [{"role": "user", "content": query}]},
                stream_mode="updates",
                config={"recursion_limit": 2 * (self.settings.max_model_calls + 2) + 5},
            )
            for chunk in stream:
                for _node, update in chunk.items():
                    messages = update.get("messages") if isinstance(update, dict) else None
                    if not isinstance(messages, list):
                        continue
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            text = message_text(msg.content)
                            if msg.tool_calls:
                                for call in msg.tool_calls:
                                    step += 1
                                    result.tool_calls += 1
                                    args = truncate(
                                        json.dumps(call.get("args", {}), ensure_ascii=False),
                                        MAX_INPUT_CHARS)
                                    note = f" (why: {truncate(text, 150)})" if text else ""
                                    self._emit(result, TraceEvent(
                                        "action", f"{args}{note}", call.get("name"), step))
                            else:
                                last_text = text
                        elif isinstance(msg, ToolMessage):
                            self._emit(result, TraceEvent(
                                "observation",
                                truncate(message_text(msg.content), MAX_OBSERVATION_CHARS),
                                msg.name, step))
        except Exception as exc:  # noqa: BLE001 - show a friendly message, never a raw traceback
            result.ok = False
            msg = self._scrub(f"{type(exc).__name__}: {exc}")
            result.final_answer = (
                "Sorry, the agent stopped because of an error. "
                f"Details: {truncate(msg, 300)}"
            )
            self._emit(result, TraceEvent("error", result.final_answer))
            return result

        if not last_text:
            result.ok = False
            last_text = "The model did not return a usable answer. Please try rephrasing."
        elif last_text.lower().startswith("model call limit"):
            result.ok = False
        result.final_answer = last_text
        self._emit(result, TraceEvent("final", last_text))
        return result
