"""Task 4 - Interactive AI chatbot (Streamlit + LangChain + Google Gemini).

Run with:  streamlit run app.py

This file only draws the interface. The real logic lives in the `chatbot/`
package so it can be tested without a browser.
"""

import streamlit as st

from chatbot import agent_bridge, history, llm, service
from chatbot.config import load_config

SAMPLE_PROMPTS = [
    "Explain what RAG means in simple words",
    "Give me 3 tips to learn Python faster",
    "Write a short email asking my mentor for feedback",
    "Now make that shorter",  # tests follow-up memory after the previous answer
]


def render_sidebar(config, agent_status) -> None:
    """Sidebar: new chat button, sample prompts and basic app information."""
    with st.sidebar:
        st.header("💬 AI Chatbot")
        st.button(
            "🗑️ New chat",
            key="new_chat",
            on_click=history.reset_conversation,
            args=(st.session_state,),
        )

        st.subheader("Try a sample prompt")
        for i, prompt in enumerate(SAMPLE_PROMPTS):
            st.button(
                prompt,
                key=f"sample_{i}",
                on_click=history.queue_prompt,
                args=(st.session_state, prompt),
                disabled=bool(config.errors),
            )

        st.subheader("Options")
        st.checkbox(
            "Use Task 3 agent (experimental)",
            key="use_agent",
            value=False,
            disabled=not agent_status.available,
            help="Routes your messages through the Task 3 multi-tool agent instead "
            "of plain Gemini. Replies appear all at once (no streaming).",
        )
        if not agent_status.available:
            st.caption(f"Agent unavailable: {agent_status.reason}")

        st.subheader("About")
        n_messages = len(history.get_messages(st.session_state))
        st.markdown(
            f"- **Model:** `{config.model_name}`\n"
            f"- **Memory window:** last {config.max_history_messages} messages\n"
            f"- **Messages in this chat:** {n_messages}\n"
            "- **Streaming:** on"
        )
        st.caption(
            "Memory lasts only for this browser session. Refreshing the page or "
            "opening a new tab starts a fresh chat; nothing is saved to disk."
        )


def main() -> None:
    st.set_page_config(page_title="AI Chatbot", page_icon="💬", layout="centered")

    config = load_config()
    history.init_session_state(st.session_state)

    # Load the optional Task 3 agent once per browser session.
    if "agent_status" not in st.session_state:
        st.session_state["agent_status"] = agent_bridge.load_agent_runner(config)
    agent_status = st.session_state["agent_status"]

    st.title("💬 AI Chatbot")
    st.caption("Ask me anything. I remember earlier messages in this chat.")

    for message in config.errors:
        st.error(message)
    for message in config.warnings:
        st.warning(message)

    # Show earlier messages (this is how the chat survives each Streamlit rerun).
    for message in history.get_messages(st.session_state):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    empty_hint = st.empty()
    if not history.get_messages(st.session_state) and not config.errors:
        empty_hint.info("👋 Type a message below, or pick a sample prompt in the sidebar.")

    typed = st.chat_input("Type your message...", disabled=bool(config.errors))
    queued = history.pop_pending_prompt(st.session_state)
    user_text = typed if typed is not None else queued

    # Without a valid API key the input is disabled and nothing is sent.
    if user_text is not None and not config.errors:
        empty_hint.empty()
        cleaned, problem = service.submit_user_message(st.session_state, user_text)
        if problem:
            st.warning(problem)
        else:
            with st.chat_message("user"):
                st.markdown(cleaned)
            with st.chat_message("assistant"):
                placeholder = st.empty()
                use_agent = agent_status.available and st.session_state.get("use_agent", False)
                with st.spinner("Thinking..."):
                    result = service.generate_assistant_reply(
                        st.session_state,
                        config,
                        placeholder,
                        model_factory=llm.create_chat_model,
                        agent_runner=agent_status.runner if use_agent else None,
                    )
            service.finish_turn(st.session_state, result)
            if not result.ok:
                st.error(result.error)
                st.caption("Your message was not saved to the chat. Please try again.")

    # Drawn last so the message count is up to date.
    render_sidebar(config, agent_status)


main()
