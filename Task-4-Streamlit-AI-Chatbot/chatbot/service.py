"""One chat turn, step by step, with no Streamlit import.

app.py calls these functions in order:
    1. submit_user_message   - validate the text and store it in history
    2. generate_assistant_reply - call the model (or Task 3 agent) and stream it
    3. finish_turn           - store the reply, or drop the question on failure
"""

from __future__ import annotations

from typing import Callable, MutableMapping, Optional

from chatbot import history, llm
from chatbot.config import AppConfig, ConfigError
from chatbot.errors import describe_error
from chatbot.streaming import StreamResult, stream_to_placeholder


def submit_user_message(state: MutableMapping, text: Optional[str]) -> tuple:
    """Validate and store a user message. Returns (cleaned_text, error)."""
    cleaned, error = history.validate_user_input(text)
    if error:
        return None, error
    history.add_message(state, "user", cleaned)
    return cleaned, None


def generate_assistant_reply(
    state: MutableMapping,
    config: AppConfig,
    placeholder,
    model_factory: Optional[Callable] = None,
    agent_runner: Optional[Callable[[str], str]] = None,
) -> StreamResult:
    """Produce the assistant reply and draw it in `placeholder`.

    Never raises: every failure comes back as `StreamResult(error=...)`.
    """
    messages = history.get_messages(state)

    # Optional path: Task 3 agent (answers all at once, no token streaming).
    if agent_runner is not None:
        question = messages[-1]["content"]
        try:
            answer = agent_runner(question)
        except Exception as exc:  # noqa: BLE001
            return StreamResult(error=f"The Task 3 agent failed: {describe_error(exc, config.google_api_key)}")
        if not answer.strip():
            return StreamResult(error="The Task 3 agent returned an empty answer.")
        placeholder.markdown(answer)
        return StreamResult(text=answer)

    # Normal path: Gemini via LangChain with streaming.
    # (Looked up at call time so tests can swap in a fake factory.)
    factory = model_factory or llm.create_chat_model
    try:
        model = factory(config)
    except ConfigError as exc:
        return StreamResult(error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return StreamResult(error=describe_error(exc, config.google_api_key))

    model_messages = history.build_model_messages(
        messages, config.system_prompt, config.max_history_messages
    )
    return stream_to_placeholder(
        llm.stream_chunks(model, model_messages), placeholder, secret=config.google_api_key
    )


def finish_turn(state: MutableMapping, result: StreamResult) -> None:
    """Save the assistant reply, or remove the unanswered user message."""
    if result.ok:
        history.add_message(state, "assistant", result.text)
    else:
        history.discard_last_user_message(state)
