"""Conversation history helpers.

Every function takes a `state` argument instead of importing Streamlit. In the
app we pass `st.session_state`; in tests we pass a plain dict. This keeps the
logic easy to test and free of UI code.

Memory model: the conversation lives in `state["messages"]`, a list of
`{"role": "user" | "assistant", "content": "..."}` dicts. It lasts only as long
as the Streamlit browser session. A page refresh or a new tab starts fresh.
"""

from __future__ import annotations

from typing import MutableMapping, Optional

from chatbot.config import MAX_USER_INPUT_CHARS

MESSAGES_KEY = "messages"
PENDING_PROMPT_KEY = "pending_prompt"
VALID_ROLES = ("user", "assistant")


def init_session_state(state: MutableMapping) -> None:
    """Create the keys we need, without overwriting existing values."""
    if MESSAGES_KEY not in state:
        state[MESSAGES_KEY] = []
    if PENDING_PROMPT_KEY not in state:
        state[PENDING_PROMPT_KEY] = None


def get_messages(state: MutableMapping) -> list:
    init_session_state(state)
    return state[MESSAGES_KEY]


def add_message(state: MutableMapping, role: str, content: str) -> None:
    """Append one message. Rejects unknown roles and empty content."""
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {VALID_ROLES}, got {role!r}")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("content must be a non-empty string")
    get_messages(state).append({"role": role, "content": content})


def discard_last_user_message(state: MutableMapping) -> bool:
    """Remove the newest message if it is a user message.

    Used when the model fails: the question never got an answer, so we drop it
    to keep the history in clean user/assistant order. Returns True if removed.
    """
    messages = get_messages(state)
    if messages and messages[-1]["role"] == "user":
        messages.pop()
        return True
    return False


def reset_conversation(state: MutableMapping) -> None:
    """Start a new chat: clear all messages and any queued sample prompt."""
    state[MESSAGES_KEY] = []
    state[PENDING_PROMPT_KEY] = None


def queue_prompt(state: MutableMapping, prompt: str) -> None:
    """Remember a sample prompt so the next script run can send it."""
    state[PENDING_PROMPT_KEY] = prompt


def pop_pending_prompt(state: MutableMapping) -> Optional[str]:
    """Return the queued sample prompt (if any) and clear it."""
    init_session_state(state)
    prompt = state[PENDING_PROMPT_KEY]
    state[PENDING_PROMPT_KEY] = None
    return prompt


def validate_user_input(
    text: Optional[str], max_chars: int = MAX_USER_INPUT_CHARS
) -> tuple:
    """Check a user message. Returns (cleaned_text, error_message).

    Exactly one of the two is None.
    """
    if text is None or not text.strip():
        return None, "Please type a message before sending."
    cleaned = text.strip()
    if len(cleaned) > max_chars:
        return None, (
            f"That message is too long ({len(cleaned)} characters). "
            f"Please keep it under {max_chars} characters."
        )
    return cleaned, None


def build_model_messages(
    history: list, system_prompt: str, max_messages: int
) -> list:
    """Turn stored history into the message list sent to the model.

    - Only the most recent `max_messages` messages are sent (the "memory window").
    - The window always starts with a user message, because chat models expect
      the conversation to begin with the user.
    - The system prompt (if any) goes first.

    Returns plain dicts like {"role": "user", "content": "..."}; LangChain
    accepts these directly, so this module needs no LangChain import.
    """
    window = history[-max(1, max_messages):]
    while window and window[0]["role"] != "user":
        window = window[1:]

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend({"role": m["role"], "content": m["content"]} for m in window)
    return messages
