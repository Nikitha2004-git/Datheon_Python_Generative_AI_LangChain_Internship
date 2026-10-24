# Task 4 – Interactive AI Chatbot (Streamlit + LangChain + Google Gemini)

A beginner-friendly chatbot with a clean chat interface, **streaming replies**, and
**conversation memory** for the active browser session. It uses Google Gemini
through the official `langchain-google-genai` integration.

## Features

- Chat UI built with `st.chat_message()` and `st.chat_input()`
- Streaming: the answer appears word by word while Gemini writes it
- Conversation memory: follow-up questions work ("Now make that shorter")
- Sidebar with a **New chat** button, sample prompts and app information
- Friendly handling of empty input, too-long input, missing API key and API errors
- API key read from `GOOGLE_API_KEY` (environment variable or `.env` file)
- Optional integration with the Task 3 agent (off by default, never required)
- Automated tests that use fakes: **no API key or internet needed**

## Project structure

```
Task-4-Streamlit-AI-Chatbot/
├── app.py                 # Streamlit interface only (draws the page)
├── chatbot/
│   ├── config.py          # reads .env / environment variables, validates the API key
│   ├── history.py         # session-state helpers + builds the messages sent to Gemini
│   ├── streaming.py       # draws streamed chunks into the page, handles failures
│   ├── llm.py             # creates the Gemini model through LangChain
│   ├── service.py         # one chat turn: validate -> call model -> save/discard
│   ├── errors.py          # friendly error messages, hides secrets
│   └── agent_bridge.py    # optional, failure-safe link to the Task 3 agent
├── tests/                 # pytest tests (all use fakes)
├── requirements.txt
├── .env.example           # placeholders only
├── .gitignore
├── pytest.ini
└── README.md
```

## Setup on Windows (Command Prompt)

You need **Python 3.12** and a free Gemini API key from
<https://aistudio.google.com/apikey>.

Open **Command Prompt** (not PowerShell) and run these one by one:

```cmd
cd path\to\Datheon_Python_Generative_AI_LangChain_Internship\Task-4-Streamlit-AI-Chatbot

python --version
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

After activation your prompt starts with `(.venv)`. If you close the window, run
`.venv\Scripts\activate` again next time.

### Configure your API key

```cmd
copy .env.example .env
notepad .env
```

Replace `your_api_key_here` with your real key, save, and close Notepad.
**Never share or commit the `.env` file.** It is already listed in `.gitignore`.

| Setting | Required | Meaning |
|---|---|---|
| `GOOGLE_API_KEY` | yes | Your Gemini API key |
| `GEMINI_MODEL` | no | Model code (default `gemini-3.5-flash-lite`) |
| `GEMINI_TEMPERATURE` | no | 0–2; empty = the model's own default |
| `MAX_HISTORY_MESSAGES` | no | How many recent messages are sent to the model (default 20) |
| `SYSTEM_PROMPT` | no | Custom instructions for the assistant |
| `ENABLE_TASK3_AGENT` and `TASK3_AGENT_*` | no | Optional Task 3 integration (see below) |

### Run the app

```cmd
streamlit run app.py
```

Your browser opens at <http://localhost:8501>. Press `Ctrl+C` in the Command Prompt
to stop it.

### Run the tests

```cmd
python -m pytest -v
```

The tests need no API key and no internet. The two UI tests in
`tests/test_app_ui.py` use Streamlit's `AppTest` and run automatically when
Streamlit is installed.

## Choosing or changing the Gemini model

The model is **not hardcoded**. Set `GEMINI_MODEL` in `.env` and restart the app:

```env
GEMINI_MODEL=gemini-3.8-flash
```

The default is `gemini-3.5-flash-lite`. Both it and `gemini-3.8-flash` were listed as
stable on Google's model page (<https://ai.google.dev/gemini-api/docs/models>) when
this project was written (October 2026). Model names and free-tier limits change, so
check that page if you get a "model not found" error.

## How it works (architecture)

1. **`app.py`** runs on every user action. Streamlit re-executes the whole script
   from top to bottom each time, so anything that must survive lives in
   `st.session_state`.
2. **`config.py`** loads `.env` and checks the API key. If it is missing, the app
   shows an error and disables the chat box instead of crashing.
3. **`service.submit_user_message`** trims and validates the text, then stores it.
4. **`history.build_model_messages`** prepares what Gemini receives: the system
   prompt plus the most recent messages.
5. **`llm.create_chat_model`** creates `ChatGoogleGenerativeAI`; **`llm.stream_chunks`**
   calls LangChain's `.stream()`.
6. **`streaming.stream_to_placeholder`** redraws one `st.empty()` placeholder as each
   chunk arrives and returns the full text.
7. **`service.finish_turn`** saves the assistant reply in history (or removes the
   unanswered question if something failed).

### Conversation memory explained

- The chat is a list in `st.session_state["messages"]`:
  `{"role": "user" | "assistant", "content": "..."}`.
- On every question, the **last `MAX_HISTORY_MESSAGES` messages** (default 20) are sent
  to Gemini together with your new question. That is how it answers follow-ups.
  Older messages stay visible on screen but are no longer sent to the model.
- **New chat** replaces the list with an empty one, so nothing from the old chat
  reaches the model.
- Memory lives **only in the current browser session**. Refreshing the page or opening
  a new tab starts an empty chat. Nothing is saved to disk or a database.

### Streaming and errors

- Chunks are shown with a cursor (▌) while the answer grows; the final text has no cursor.
- If an error happens (even in the middle of an answer), the half-finished text is
  removed, an error message is shown, and the question is dropped from history so
  you can simply send it again. You never see a duplicate or partial reply.
- Empty replies (for example when a safety filter blocks an answer) are reported
  as an error too.

## Optional: use the Task 3 agent

Task 4 works fully without Task 3. To try the integration:

1. Make sure the Task 3 folder sits next to this one
   (`...\Task-3-Multi-Tool-AI-Agent`).
2. In `.env` set `ENABLE_TASK3_AGENT=true`.
3. Tell Task 4 which function to call (a function that takes a question string and
   returns the answer text):
   ```env
   TASK3_AGENT_DIR=../Task-3-Multi-Tool-AI-Agent
   TASK3_AGENT_MODULE=agent
   TASK3_AGENT_FUNCTION=run_agent
   ```
   `agent` and `run_agent` are **default guesses**. Change them to match your real
   Task 3 file and function name.
4. Restart the app and tick **Use Task 3 agent (experimental)** in the sidebar.

If Task 3 is missing, switched off, or fails to import, the checkbox is disabled and
the sidebar shows the reason. The normal Gemini chatbot keeps working. Agent
answers appear all at once (no streaming) and the agent only receives your latest
question, not the whole chat.

If your Task 3 has no single "question in, answer out" function, create a small
adapter **inside the Task 4 folder** (so Task 3 stays untouched), for example
`my_task3_adapter.py`:

```python
import sys
sys.path.append(r"..\Task-3-Multi-Tool-AI-Agent")   # so Task 3's own imports work

def run_agent(question: str) -> str:
    # Call your real Task 3 code here and return the final answer as text.
    raise NotImplementedError
```

Then set `TASK3_AGENT_DIR=.`, `TASK3_AGENT_MODULE=my_task3_adapter` in `.env`.

## Security and privacy

- The API key is read only from `GOOGLE_API_KEY`; it is never hardcoded, never shown
  in the UI, and is removed from error messages.
- `.env`, `.venv`, caches and secrets are excluded by `.gitignore`.
- The app never runs code typed by the user. Messages are only sent to Gemini.
- The app does not read local files, so there is no file-access surface to protect.
- Your messages are sent to Google's Gemini API. Do not type passwords or private data.
- The optional Task 3 module and function names come from `.env` only, never from chat.

## Sample prompts

- `Explain what RAG means in simple words`
- `Give me 3 tips to learn Python faster`
- then a follow-up: `Now make that shorter`
- `Write a short email asking my mentor for feedback`
- `My name is Priya. What is a good name for a Python project?` then `What is my name?`
- `Explain LangChain streaming like I'm a beginner`

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Install Python 3.12 and tick **Add Python to PATH**, then reopen Command Prompt. |
| `'streamlit' is not recognized` | Activate the venv first: `.venv\Scripts\activate`, then `pip install -r requirements.txt`. |
| `ModuleNotFoundError: No module named 'chatbot'` | Run commands from inside the `Task-4-Streamlit-AI-Chatbot` folder. |
| Red error "GOOGLE_API_KEY is missing" | Create `.env` (`copy .env.example .env`), add your key, restart the app. |
| "Google rejected the API key" | Re-copy the key from AI Studio; no spaces or quotes; make sure the Gemini API is available for it. |
| "model was not found" | Check `GEMINI_MODEL` against <https://ai.google.dev/gemini-api/docs/models>. |
| "rate limit or quota" | Wait a minute, or try another `GEMINI_MODEL`. Free tiers have daily limits. |
| Edited `.env` but nothing changed | Stop the app (`Ctrl+C`) and start it again. |
| Port 8501 is busy | `streamlit run app.py --server.port 8502` |
| `pip install` version conflict | Use a fresh venv: delete `.venv`, run `python -m venv .venv` again, reinstall. |
| Task 3 agent unavailable | Read the reason in the sidebar; check the `TASK3_AGENT_*` values in `.env`. |

## Limitations

- **Memory is per browser session only.** Refresh, a new tab, or restarting the app
  clears the chat. Nothing is stored permanently.
- Only the most recent `MAX_HISTORY_MESSAGES` messages are sent to the model, so very
  long chats can "forget" their beginning.
- A message that fails is removed from the chat; you have to send it again.
- Gemini can make mistakes. Check important facts.
- No file upload, no web search and no tools in the basic chatbot; those exist only
  through the optional Task 3 agent, which is not streamed and sees only your last message.
- The automated tests use fakes. They prove the app logic, not that your API key or
  Google's service works. Send one real message to confirm your setup.
- Free API tiers have rate limits that can change.

## Adding this folder to your internship repository

Copy the whole `Task-4-Streamlit-AI-Chatbot` folder into the repo root, next to the
other task folders. Before committing, run `git status` and confirm that `.env` and
`.venv` are **not** listed.
