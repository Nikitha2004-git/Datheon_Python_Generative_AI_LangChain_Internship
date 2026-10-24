"""Console entry point for the Multi-Tool Autonomous AI Agent.

Usage:
    python run.py                 interactive session
    python run.py --check         configuration check (no secrets shown, no network)
    python run.py -q "your question"   run one question and exit
"""
from __future__ import annotations

import argparse
import sys

from agent import __version__
from agent.agent_runner import AgentRunner, TraceEvent
from agent.config import ConfigError, Settings
from agent.tools.file_reader import list_permitted_files

LINE = "-" * 70
LABELS = {
    "user_query": "USER QUERY ",
    "action": "ACTION     ",
    "observation": "OBSERVATION",
    "final": "FINAL ANSWER",
    "error": "ERROR      ",
}


def print_event(event: TraceEvent) -> None:
    if event.kind == "user_query":
        print(f"\n{LINE}\n[{LABELS['user_query']}] {event.text}\n{LINE}")
    elif event.kind == "action":
        print(f"[STEP {event.step}] Tool selected: {event.tool}")
        print(f"   Input      : {event.text}")
    elif event.kind == "observation":
        body = event.text.replace("\n", "\n               ")
        print(f"   Observation: {body}")
        print("   Next       : model reads this result and decides the next step...")
    elif event.kind == "final":
        print(f"\n{LINE}\n[FINAL ANSWER]\n{event.text}\n{LINE}")
    elif event.kind == "error":
        print(f"\n[ERROR] {event.text}")
    sys.stdout.flush()


def run_checks() -> int:
    print(f"Multi-Tool AI Agent v{__version__} - configuration check\n")
    problems = 0
    print(f"Python version : {sys.version.split()[0]}", end="")
    if sys.version_info[:2] in ((3, 11), (3, 12), (3, 13)):
        print("  [OK]")
    else:
        print("  [WARN] 3.11 or 3.12 recommended"); problems += 1
    for module in ("langchain", "langchain_google_genai", "ddgs", "dotenv", "pydantic"):
        try:
            __import__(module); print(f"Package {module:<24}[OK]")
        except ImportError:
            print(f"Package {module:<24}[MISSING] run: pip install -r requirements.txt"); problems += 1
    try:
        settings = Settings.load()
    except ConfigError as exc:
        print(f"Settings       : [ERROR] {exc}"); return 1
    for key, value in settings.safe_summary().items():
        print(f"{key:<15}: {value}")
    if not settings.google_api_key:
        print("\n[WARN] GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key.")
        problems += 1
    files = list_permitted_files(settings.workspace_dir)
    print(f"Readable files : {', '.join(files) if files else '[NONE FOUND]'}")
    if not files:
        problems += 1
    print("\nResult:", "all checks passed." if problems == 0 else f"{problems} issue(s) found.")
    return 0 if problems == 0 else 1


WELCOME = """
======================================================================
   Multi-Tool Autonomous AI Agent  (Datheon Internship - Task 3)
======================================================================
Tools the agent can choose from:
  1. web_search : current information from the web (DuckDuckGo)
  2. calculator : safe math (+ - * / ** sqrt, parentheses)
  3. read_file  : read .txt/.md/.json files from the sample_files folder
Type your question and press Enter.  Type 'exit' or 'quit' to leave.
Tip: files you can ask about: {files}
"""


def interactive(runner: AgentRunner, files: list[str]) -> None:
    print(WELCOME.format(files=", ".join(files) or "none"))
    while True:
        try:
            query = input("\nYou> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            return
        if query.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            return
        if not query:
            continue
        try:
            runner.run(query)
        except KeyboardInterrupt:
            print("\n[Interrupted] Question cancelled. Ask another or type 'exit'.")
        except Exception as exc:  # noqa: BLE001
            print(f"\n[ERROR] Unexpected problem: {type(exc).__name__}. Please try again.")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Multi-Tool Autonomous AI Agent")
    parser.add_argument("--check", action="store_true", help="run configuration checks and exit")
    parser.add_argument("-q", "--query", help="run a single question and exit")
    args = parser.parse_args(argv)
    if args.check:
        return run_checks()
    try:
        settings = Settings.load()
        runner = AgentRunner(settings, on_event=print_event)
    except ConfigError as exc:
        print(f"[CONFIG ERROR] {exc}\nTip: run 'python run.py --check' for details.")
        return 1
    if args.query:
        result = runner.run(args.query)
        return 0 if result.ok else 1
    interactive(runner, list_permitted_files(settings.workspace_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
