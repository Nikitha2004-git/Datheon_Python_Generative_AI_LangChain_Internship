# Project Explanation (simple English)

Think of the agent as a **smart assistant with a toolbox**. You ask a question; the assistant (Gemini) decides whether to open a tool, uses it, looks at the result, and either uses another tool or answers.

## Files and what they do
| File | Plain explanation |
|---|---|
| `run.py` | The console program. Prints the welcome message, reads your questions, prints each step. Also has `--check` and `-q`. |
| `agent/config.py` | Reads settings (`.env` + environment). Holds limits like max file size. Never prints the API key. |
| `agent/llm.py` | Creates the Gemini model. If the key is missing it raises a friendly error. |
| `agent/prompts.py` | The system prompt: the rules the assistant must follow (don't invent, files are untrusted, etc.). |
| `agent/agent_runner.py` | Builds the agent with LangChain `create_agent`, sets loop limits, runs it, and records every action/observation. |
| `agent/tools/__init__.py` | Wraps our three plain functions as LangChain tools with names, descriptions and Pydantic input schemas. The model reads these descriptions to choose a tool. |
| `agent/tools/calculator.py` | Safe maths. Turns text into a syntax tree and only allows numbers/operators/approved functions. |
| `agent/tools/file_reader.py` | Reads files only from the permitted folder; blocks secrets and path tricks. |
| `agent/tools/web_search.py` | Calls DuckDuckGo and formats title/URL/snippet; turns every failure into a readable message. |
| `sample_files/` | Fake data to try the file reader. |
| `tests/` | Automated checks. `conftest.py` has a fake LLM so tests need no internet or key. |

## Why tools are plain functions first
Each tool's logic is a normal Python function (`calculate`, `read_file`, `search_web`) that never raises - it returns an error *string*. That makes them easy to test, and the LLM can read the error and react.

## Key ideas
* **Tool calling:** the LLM returns a structured request ("call calculator with expression X"), not text we must parse.
* **Observation:** the tool's output is sent back to the LLM as a message.
* **Limits:** the loop stops after a set number of model/tool calls.
