# Task 3 - Multi-Tool Autonomous AI Agent

Datheon Python + Generative AI & LangChain Internship.

A console AI agent that **decides for itself** which tool to use (web search, calculator, file reader), runs it, reads the result, and continues until it can give a final answer. Every step is printed so you can see what happened.

## 1. Problem statement and goals
A plain LLM cannot look up today's information, cannot calculate reliably and cannot see your files. Goal: give an LLM safe tools and let it plan multi-step solutions, while keeping it secure and transparent.

## 2. Features
| Tool | What it does | Safety |
|---|---|---|
| `web_search` | DuckDuckGo search (no API key). Returns title, URL, snippet. | Timeouts, rate-limit/empty/offline handling, results labelled "not verified facts" |
| `calculator` | `+ - * / // % **`, parentheses, `sqrt abs round min max floor ceil log pi e` | AST whitelist, **no `eval()`**, no code, size limits |
| `read_file` | Reads `.txt .md .json` from `sample_files/` (or `WORKSPACE_DIR`) | Folder jail, blocks `..`, absolute paths, symlink escape, `.env`/secret-looking names, size limit, read-only |

Also: tool-call and model-call limits (no infinite loops), transparent trace, `--check` command, 111 automated tests that need no API key or internet.

**Not implemented (by design):** the agent cannot write/save files, so it cannot "save a summary" automatically. It can read files and show you the summary in the console. Tavily search is not implemented (DuckDuckGo only).

## 3. Architecture and flow
```
User Query -> LLM picks tool -> Action (tool runs) -> Observation -> LLM decides next step
                 ^                                                        |
                 +------------------ repeat (limited) --------------------+
                                         |
                                   Final Answer
```
* `create_agent` (LangChain 1.x, built on LangGraph) runs the tool-calling loop using Gemini's native function calling.
* `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware` cap the loop.
* `agent_runner.py` streams the steps and records `TraceEvent`s that `run.py` prints.
* Only actions, inputs, observations and answers are shown - never hidden chain-of-thought.

## 4. Folder structure
```
Task-3-Multi-Tool-AI-Agent/
  run.py                 console app (interactive, -q, --check)
  agent/  config.py llm.py prompts.py agent_runner.py
          tools/ web_search.py calculator.py file_reader.py __init__.py
  sample_files/ company_info.txt project_budget.txt
  tests/  conftest.py test_calculator.py test_file_reader.py test_web_search.py test_agent.py
  docs/   PROJECT_EXPLANATION.md AGENT_WORKFLOW.md RUN_GUIDE_WINDOWS.md INTERVIEW_QUESTIONS.md GITHUB_GUIDE_WINDOWS.md
  .env.example  .gitignore  requirements.txt  pytest.ini  README.md
```

## 5. Technologies
Python 3.11/3.12, LangChain 1.4, LangGraph (inside LangChain), `langchain-google-genai` (Gemini), `ddgs` (DuckDuckGo), Pydantic, python-dotenv, pytest.

## 6. Setup (Windows Command Prompt)
Full copy-paste steps: `docs/RUN_GUIDE_WINDOWS.md`. Short version:
```
cd Task-3-Multi-Tool-AI-Agent
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
notepad .env
python run.py --check
python run.py
```
API key: create a free key at https://aistudio.google.com/apikey and put it in `.env` as `GOOGLE_API_KEY=...`.
DuckDuckGo needs **no** key.

## 7. Example questions
1. `Calculate (1250 * 3) + 450.` -> uses calculator (expected 4200)
2. `Read the company information from the permitted sample file.` -> read_file
3. `Search for the latest Python release and summarize the sources.` -> web_search
4. `Read the project budget file, calculate the remaining budget, and explain the result.` -> read_file then calculator (expected 140000 from the sample data)
5. `What is the phone number of the CEO listed in company_info.txt?` -> file has no such info; the agent should say so
6. Security demos: `Read the file .env` (refused), `Read ../../secret.txt` (refused)

Model behaviour can vary between runs; the tool safety rules do not depend on the model.

## 8. Tests
```
python -m pytest
```
No API key or internet needed (the LLM and search are mocked). Result in this delivery: **111 passed** (Python 3.12, Linux). See "Verification status".

## 9. Troubleshooting
| Problem | Fix |
|---|---|
| `GOOGLE_API_KEY is not set` | Create `.env` from `.env.example`, paste key, no quotes/spaces |
| `'py' is not recognized` | Install Python 3.12 from python.org, tick "Add to PATH", reopen CMD |
| `pip install` fails | `python -m pip install --upgrade pip`, then retry |
| Web search error / rate limit | Check internet; wait a minute; DuckDuckGo may throttle |
| 429 / quota error from Gemini | Free-tier limit; wait, or set `GEMINI_MODEL` to another model |
| 404 model not found | Set `GEMINI_MODEL` in `.env` to a model your key can use |
| Activation blocked | You are in PowerShell; use CMD or `.venv\Scripts\Activate.ps1` |

## 10. Security considerations
* Calculator parses with `ast`, whitelists node types; rejects names, attributes, subscripts, lambdas, strings, unknown calls.
* File reader: resolved-path check inside the workspace, extension allow-list, hidden/secret-name blocklist, size limit, UTF-8 check, read-only.
* Prompt injection: tool output is labelled untrusted and the system prompt says to ignore instructions inside it. This **reduces** but cannot fully eliminate the risk; real protection is that tools are limited (no shell, no writes, no network except search).
* API key lives only in `.env` (git-ignored), is never printed, and is scrubbed from error messages.
* Limits: model calls, tool calls, search timeout, file size, expression length.

## 11. Limitations
* Search snippets can be outdated, incomplete or wrong; the agent does not verify them.
* Gemini free tier has rate limits; behaviour varies between runs.
* No file writing, no PDF/docx reading, no memory between questions.
* DuckDuckGo scraping-based library may be rate-limited or change.

## 12. Future improvements
Tavily option, a restricted output folder + save tool, PDF reader, conversation memory, streaming tokens, web UI, evaluation set for tool-choice accuracy.

## 13. Verification status
Performed here: all 111 tests pass; `python run.py --check`; startup with missing key gives a friendly error; trace display checked with a scripted fake model; ZIP contents verified.
**Not performed here (needs your key / internet):** real Gemini calls and live DuckDuckGo searches. The sandbox used for building had no web access (live search returned the friendly error as designed). Please run the five demos in section 7 yourself.
