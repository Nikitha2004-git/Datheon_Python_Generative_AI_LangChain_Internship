"""End-to-end turn logic with a fake model: no API key, no internet."""

from chatbot import history, service
from chatbot.config import ConfigError, load_config


def _turn(state, config, fakes, text, model, agent_runner=None):
    """Run one full turn the same way app.py does."""
    cleaned, problem = service.submit_user_message(state, text)
    if problem:
        return None, problem, None
    ph = fakes.Placeholder()
    result = service.generate_assistant_reply(
        state, config, ph, model_factory=lambda cfg: model, agent_runner=agent_runner
    )
    service.finish_turn(state, result)
    return result, None, ph


def test_successful_turn_stores_user_and_assistant_messages(config, fakes):
    state = {}
    result, problem, ph = _turn(state, config, fakes, "  Hello  ", fakes.Model(["Hi ", "there"]))
    assert problem is None and result.ok
    assert state["messages"] == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    assert ph.last_markdown == "Hi there"


def test_follow_up_question_sends_earlier_conversation_to_model(config, fakes):
    state = {}
    model = fakes.Model(["Paris"])
    _turn(state, config, fakes, "What is the capital of France?", model)
    model.chunks = ["About 2 million people"]
    _turn(state, config, fakes, "How many people live there?", model)

    second_call = model.received[1]
    assert second_call[0]["role"] == "system"
    assert [(m["role"], m["content"]) for m in second_call[1:]] == [
        ("user", "What is the capital of France?"),
        ("assistant", "Paris"),
        ("user", "How many people live there?"),
    ]


def test_old_messages_fall_out_of_the_memory_window(fakes):
    cfg = load_config(env={"GOOGLE_API_KEY": "k" * 12, "MAX_HISTORY_MESSAGES": "2", "SYSTEM_PROMPT": "sys"})
    state = {}
    model = fakes.Model(["ok"])
    _turn(state, cfg, fakes, "first", model)
    _turn(state, cfg, fakes, "second", model)
    sent = [m["content"] for m in model.received[1] if m["role"] != "system"]
    assert sent == ["second"]  # window of 2 -> starts at a user message, so "ok" is dropped too
    assert len(state["messages"]) == 4  # but the full chat is still stored for display


def test_empty_input_changes_nothing_and_never_calls_model(config, fakes):
    state = {}
    model = fakes.Model(["should not run"])
    result, problem, _ = _turn(state, config, fakes, "   ", model)
    assert result is None and "type a message" in problem
    assert history.get_messages(state) == []
    assert model.received == []


def test_api_error_removes_the_unanswered_question_and_shows_no_reply(config, fakes):
    state = {}
    _turn(state, config, fakes, "q1", fakes.Model(["a1"]))
    result, _, ph = _turn(state, config, fakes, "q2", fakes.Model(error=Exception("429 quota exceeded")))
    assert not result.ok and "rate limit" in result.error
    assert [m["content"] for m in state["messages"]] == ["q1", "a1"]  # q2 removed, no stray reply
    assert ph.last_markdown is None


def test_mid_stream_failure_leaves_no_partial_or_duplicate_reply(config, fakes):
    state = {}
    model = fakes.Model(["half an ans"], error=ConnectionError("connection reset"))
    result, _, ph = _turn(state, config, fakes, "q", model)
    assert not result.ok
    assert state["messages"] == []
    assert ph.calls[-1] == ("empty", None)


def test_retry_after_failure_keeps_user_assistant_order(config, fakes):
    state = {}
    _turn(state, config, fakes, "q", fakes.Model(error=Exception("boom")))
    _turn(state, config, fakes, "q", fakes.Model(["fine"]))
    assert [m["role"] for m in state["messages"]] == ["user", "assistant"]


def test_missing_api_key_gives_clear_error_from_real_factory(fakes):
    cfg = load_config(env={})
    state = {}
    service.submit_user_message(state, "hello")
    result = service.generate_assistant_reply(state, cfg, fakes.Placeholder())  # real factory
    assert not result.ok and "GOOGLE_API_KEY" in result.error


def test_factory_config_error_and_unexpected_error_are_handled(config, fakes):
    def bad_config(cfg):
        raise ConfigError("package missing")

    def bad_other(cfg):
        raise RuntimeError("kaboom")

    for factory, expected in ((bad_config, "package missing"), (bad_other, "RuntimeError")):
        state = {}
        service.submit_user_message(state, "hi")
        result = service.generate_assistant_reply(state, config, fakes.Placeholder(), model_factory=factory)
        assert not result.ok and expected in result.error


def test_new_chat_clears_conversation_and_next_turn_starts_fresh(config, fakes):
    state = {}
    model = fakes.Model(["a"])
    _turn(state, config, fakes, "q1", model)
    history.reset_conversation(state)
    assert state["messages"] == []
    _turn(state, config, fakes, "q2", model)
    sent = [m["content"] for m in model.received[-1] if m["role"] != "system"]
    assert sent == ["q2"]  # nothing from before the reset leaks into the new chat


# --- optional Task 3 agent path ------------------------------------------------

def test_agent_runner_answer_is_stored_and_model_is_not_used(config, fakes):
    state = {}
    model = fakes.Model(["should not run"])
    result, _, ph = _turn(state, config, fakes, "2+2?", model, agent_runner=lambda q: f"agent says 4 for {q}")
    assert result.ok and ph.last_markdown == "agent says 4 for 2+2?"
    assert state["messages"][-1] == {"role": "assistant", "content": "agent says 4 for 2+2?"}
    assert model.received == []


def test_agent_failure_is_reported_and_question_removed(config, fakes):
    def broken(question):
        raise RuntimeError("tool crashed")

    state = {}
    result, _, _ = _turn(state, config, fakes, "hi", fakes.Model(["x"]), agent_runner=broken)
    assert not result.ok and "Task 3 agent failed" in result.error
    assert state["messages"] == []


def test_agent_empty_answer_is_an_error(config, fakes):
    state = {}
    result, _, _ = _turn(state, config, fakes, "hi", fakes.Model(["x"]), agent_runner=lambda q: "  ")
    assert not result.ok
