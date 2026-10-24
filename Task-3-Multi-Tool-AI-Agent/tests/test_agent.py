import pytest
from langchain_core.messages import AIMessage

from agent.agent_runner import AgentRunner, message_text, truncate
from agent.config import ConfigError, Settings
from agent.llm import MissingAPIKeyError, get_llm
from agent.tools import build_tools
from tests.conftest import tool_call_msg


def run(settings, model, query="q", tools=None):
    events = []
    runner = AgentRunner(settings, llm=model, tools=tools, on_event=events.append)
    return runner.run(query), events


def test_tools_are_registered(settings):
    names = {t.name for t in build_tools(settings)}
    assert names == {"web_search", "calculator", "read_file"}


def test_single_tool_calculator(settings, make_model):
    model = make_model(
        tool_call_msg("calculator", {"expression": "(1250 * 3) + 450"}, "c1", "Need exact math"),
        AIMessage(content="The answer is 4200."),
    )
    result, events = run(settings, model, "Calculate (1250 * 3) + 450.")
    assert result.ok and result.final_answer == "The answer is 4200."
    kinds = [e.kind for e in events]
    assert kinds == ["user_query", "action", "observation", "final"]
    assert events[1].tool == "calculator" and "1250" in events[1].text
    assert "= 4200" in events[2].text


def test_multi_tool_sequence_uses_observations(settings, make_model):
    model = make_model(
        tool_call_msg("read_file", {"filename": "budget.txt"}, "c1"),
        tool_call_msg("calculator", {"expression": "1000 - 250"}, "c2"),
        AIMessage(content="Remaining budget is 750."),
    )
    result, events = run(settings, model, "Remaining budget?")
    assert [e.tool for e in events if e.kind == "action"] == ["read_file", "calculator"]
    assert result.tool_calls == 2 and result.final_answer == "Remaining budget is 750."
    # the model must have been shown the file contents before its next step
    assert "Total: 1000" in str(model.seen[1][-1].content)
    assert "= 750" in str(model.seen[2][-1].content)


def test_web_search_tool_is_called_with_mock(settings, make_model, monkeypatch):
    import agent.tools as tools_pkg
    monkeypatch.setattr(tools_pkg, "search_web", lambda q, n, t: f"MOCK RESULTS for {q}")
    model = make_model(tool_call_msg("web_search", {"query": "latest python"}, "c1"),
                       AIMessage(content="Done."))
    result, events = run(settings, model)
    assert "MOCK RESULTS for latest python" in events[2].text


def test_direct_answer_without_tools(settings, make_model):
    result, events = run(settings, make_model(AIMessage(content="Hello!")), "hi")
    assert result.tool_calls == 0 and result.final_answer == "Hello!"


def test_tool_failure_is_reported_not_fatal(settings, make_model):
    model = make_model(
        tool_call_msg("read_file", {"filename": "missing.txt"}, "c1"),
        AIMessage(content="I could not find that file, so I cannot answer."),
    )
    result, events = run(settings, model)
    assert result.ok
    assert "File reader error" in events[2].text
    assert "cannot answer" in result.final_answer


def test_sensitive_file_request_blocked_through_agent(settings, make_model):
    model = make_model(tool_call_msg("read_file", {"filename": ".env"}, "c1"),
                       AIMessage(content="Access was denied."))
    result, events = run(settings, model)
    assert "Access denied" in events[2].text and "SECRET123" not in events[2].text


def test_unknown_tool_does_not_crash(settings, make_model):
    model = make_model(tool_call_msg("delete_everything", {}, "c1"),
                       AIMessage(content="Sorry, that tool does not exist."))
    result, _ = run(settings, model)
    assert result.final_answer  # run completed with a final message


def test_tool_call_limit_stops_runaway_loops(settings, make_model):
    calls = [tool_call_msg("calculator", {"expression": "1+1"}, f"c{i}") for i in range(20)]
    model = make_model(*calls, AIMessage(content="stopped"))
    result, events = run(settings, model)
    # never more than the model-call limit worth of model turns
    assert model.cursor <= settings.max_model_calls + 1
    assert result.tool_calls <= settings.max_model_calls


def test_model_call_limit_prevents_infinite_loop(settings, make_model):
    model = make_model(*[tool_call_msg("calculator", {"expression": "2*2"}, f"c{i}")
                         for i in range(50)])
    result, _ = run(settings, model)
    assert model.cursor <= settings.max_model_calls
    assert result.ok is False  # stopped by limit, flagged as not a normal finish


def test_malformed_empty_model_response(settings, make_model):
    result, _ = run(settings, make_model(AIMessage(content="")))
    assert not result.ok and "did not return" in result.final_answer


def test_llm_exception_is_handled_and_key_scrubbed(settings, make_model):
    model = make_model(RuntimeError(f"API failure key={settings.google_api_key}"))
    result, events = run(settings, model)
    assert not result.ok
    assert settings.google_api_key not in result.final_answer
    assert events[-1].kind == "error"


def test_empty_query_rejected(settings, make_model):
    result, events = run(settings, make_model(AIMessage(content="x")), "   ")
    assert not result.ok and events == []


def test_missing_api_key_raises_friendly_error(settings):
    no_key = Settings(**{**settings.__dict__, "google_api_key": None})
    with pytest.raises(MissingAPIKeyError, match="GOOGLE_API_KEY"):
        get_llm(no_key)
    with pytest.raises(ConfigError):
        AgentRunner(no_key)


def test_settings_placeholder_key_treated_as_missing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GOOGLE_API_KEY=your_api_key_here\n", encoding="utf-8")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert Settings.load(env).google_api_key is None


def test_settings_reads_key_but_summary_hides_it(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GOOGLE_API_KEY=abc123realish\nMAX_TOOL_CALLS=3\n", encoding="utf-8")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("MAX_TOOL_CALLS", raising=False)
    s = Settings.load(env)
    assert s.google_api_key == "abc123realish" and s.max_tool_calls == 3
    assert "abc123realish" not in str(s.safe_summary())
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("MAX_TOOL_CALLS", raising=False)


def test_invalid_numeric_setting(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("MAX_FILE_BYTES=abc\n", encoding="utf-8")
    monkeypatch.delenv("MAX_FILE_BYTES", raising=False)
    with pytest.raises(ConfigError, match="MAX_FILE_BYTES"):
        Settings.load(env)


def test_message_text_handles_block_lists():
    assert message_text([{"type": "text", "text": "a"}, {"type": "thinking", "x": 1}, "b"]) == "a\nb"
    assert message_text(None) == ""


def test_truncate():
    assert truncate("x" * 10, 20) == "x" * 10
    assert "truncated" in truncate("x" * 50, 20)
