import pytest

from chatbot import history


# --- session-state initialisation -----------------------------------------

def test_init_creates_empty_history():
    state = {}
    history.init_session_state(state)
    assert state["messages"] == []
    assert state["pending_prompt"] is None


def test_init_does_not_overwrite_existing_messages():
    state = {"messages": [{"role": "user", "content": "hi"}]}
    history.init_session_state(state)
    assert state["messages"] == [{"role": "user", "content": "hi"}]


# --- adding messages -------------------------------------------------------

def test_add_user_and_assistant_messages_in_order():
    state = {}
    history.add_message(state, "user", "Hello")
    history.add_message(state, "assistant", "Hi there!")
    assert history.get_messages(state) == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]


def test_add_message_rejects_bad_role_and_empty_content():
    state = {}
    with pytest.raises(ValueError):
        history.add_message(state, "robot", "hi")
    with pytest.raises(ValueError):
        history.add_message(state, "user", "   ")
    assert history.get_messages(state) == []


def test_discard_last_user_message():
    state = {}
    history.add_message(state, "user", "q1")
    history.add_message(state, "assistant", "a1")
    history.add_message(state, "user", "q2")
    assert history.discard_last_user_message(state) is True
    assert [m["content"] for m in state["messages"]] == ["q1", "a1"]
    # Last message is now an assistant message, so nothing more is removed.
    assert history.discard_last_user_message(state) is False
    assert len(state["messages"]) == 2


# --- new chat / reset -------------------------------------------------------

def test_reset_clears_messages_and_pending_prompt():
    state = {}
    history.add_message(state, "user", "q")
    history.add_message(state, "assistant", "a")
    history.queue_prompt(state, "queued")
    old_list = state["messages"]
    history.reset_conversation(state)
    assert state["messages"] == []
    assert state["pending_prompt"] is None
    assert state["messages"] is not old_list  # a fresh list, not a shared one


def test_new_messages_work_after_reset():
    state = {}
    history.add_message(state, "user", "old")
    history.reset_conversation(state)
    history.add_message(state, "user", "new")
    assert [m["content"] for m in state["messages"]] == ["new"]


# --- queued sample prompts ---------------------------------------------------

def test_pending_prompt_is_returned_once():
    state = {}
    history.queue_prompt(state, "sample")
    assert history.pop_pending_prompt(state) == "sample"
    assert history.pop_pending_prompt(state) is None


# --- input validation --------------------------------------------------------

def test_empty_and_whitespace_inputs_are_rejected():
    for bad in (None, "", "   ", "\n\t"):
        cleaned, error = history.validate_user_input(bad)
        assert cleaned is None and "type a message" in error


def test_input_is_trimmed():
    assert history.validate_user_input("  hello  ") == ("hello", None)


def test_too_long_input_is_rejected():
    cleaned, error = history.validate_user_input("x" * 11, max_chars=10)
    assert cleaned is None and "too long" in error


# --- conversation history sent to the model ----------------------------------

def _chat(n_pairs):
    msgs = []
    for i in range(n_pairs):
        msgs.append({"role": "user", "content": f"q{i}"})
        msgs.append({"role": "assistant", "content": f"a{i}"})
    return msgs


def test_system_prompt_comes_first_and_history_follows():
    out = history.build_model_messages(_chat(1) + [{"role": "user", "content": "q1"}], "Be nice", 20)
    assert out[0] == {"role": "system", "content": "Be nice"}
    assert [m["content"] for m in out[1:]] == ["q0", "a0", "q1"]


def test_follow_up_questions_include_earlier_turns():
    out = history.build_model_messages(_chat(2), "", 20)
    assert [m["content"] for m in out] == ["q0", "a0", "q1", "a1"]
    assert all(m["role"] != "system" for m in out)


def test_only_recent_messages_are_sent():
    out = history.build_model_messages(_chat(5), "", 4)
    assert [m["content"] for m in out] == ["q3", "a3", "q4", "a4"]


def test_window_never_starts_with_an_assistant_message():
    out = history.build_model_messages(_chat(5), "", 5)  # would start with a(n)
    assert out[0]["role"] == "user"
    assert [m["content"] for m in out] == ["q3", "a3", "q4", "a4"]


def test_window_size_below_one_still_sends_latest_message():
    msgs = [{"role": "user", "content": "only"}]
    out = history.build_model_messages(msgs, "", 0)
    assert [m["content"] for m in out] == ["only"]


def test_building_messages_does_not_change_stored_history():
    stored = _chat(2)
    snapshot = [dict(m) for m in stored]
    history.build_model_messages(stored, "sys", 2)
    assert stored == snapshot
