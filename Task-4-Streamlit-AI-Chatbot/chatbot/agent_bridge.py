"""Optional bridge to the Task 3 Multi-Tool Agent.

The chatbot never depends on this file working. `load_agent_runner` never
raises: if Task 3 is switched off, missing, or broken, it returns an
`AgentStatus` that says why, and the normal Gemini chatbot keeps working.

Contract with Task 3: a function that takes one question (str) and returns the
answer (str, or a dict with an "output" key). Which module and function to use
is set in `.env` (TASK3_AGENT_DIR / TASK3_AGENT_MODULE / TASK3_AGENT_FUNCTION).
The names come from configuration only, never from chat messages.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from chatbot.config import AppConfig


@dataclass
class AgentStatus:
    available: bool
    reason: str
    runner: Optional[Callable[[str], str]] = None


def _is_dotted_identifier(name: str) -> bool:
    return bool(name) and all(part.isidentifier() for part in name.split("."))


def normalize_agent_output(result) -> str:
    """Convert whatever the agent returns into plain text."""
    if isinstance(result, dict):
        result = result.get("output", result)
    return str(result)


def load_agent_runner(config: AppConfig) -> AgentStatus:
    """Try to import the Task 3 agent function. Never raises."""
    if not config.enable_task3_agent:
        return AgentStatus(False, "Task 3 agent is turned off (ENABLE_TASK3_AGENT=false).")

    agent_dir = Path(config.task3_agent_dir)
    if not agent_dir.is_dir():
        return AgentStatus(False, f"Task 3 folder not found: {agent_dir}")

    module_name = config.task3_agent_module
    function_name = config.task3_agent_function
    if not _is_dotted_identifier(module_name) or not function_name.isidentifier():
        return AgentStatus(False, "TASK3_AGENT_MODULE / TASK3_AGENT_FUNCTION are not valid Python names.")

    # Make sure the module really lives in the Task 3 folder before importing.
    top = module_name.split(".")[0]
    if not ((agent_dir / f"{top}.py").is_file() or (agent_dir / top / "__init__.py").is_file()):
        return AgentStatus(False, f"Module '{top}' was not found in {agent_dir}")

    try:
        if str(agent_dir) not in sys.path:
            sys.path.insert(0, str(agent_dir))
        importlib.invalidate_caches()
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
    except AttributeError:
        return AgentStatus(False, f"'{module_name}' has no function named '{function_name}'.")
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - Task 3 must never crash Task 4
        return AgentStatus(False, f"Could not import the Task 3 agent ({type(exc).__name__}: {exc}).")

    if not callable(function):
        return AgentStatus(False, f"'{function_name}' in '{module_name}' is not callable.")

    def runner(question: str) -> str:
        return normalize_agent_output(function(question))

    return AgentStatus(True, "Task 3 agent loaded.", runner)
