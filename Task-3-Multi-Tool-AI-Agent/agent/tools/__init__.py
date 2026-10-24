"""LangChain tool wrappers. Each wraps a plain, separately-tested function."""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..config import Settings
from .calculator import calculate
from .file_reader import read_file
from .web_search import search_web


class SearchInput(BaseModel):
    query: str = Field(description="What to search the web for. Keep it short and specific.")


class CalcInput(BaseModel):
    expression: str = Field(
        description="Math expression, e.g. '(1250 * 3) + 450' or 'sqrt(144)'. Numbers only."
    )


class FileInput(BaseModel):
    filename: str = Field(
        description="File name inside the permitted folder (e.g. 'project_budget.txt'). "
                    "Use '.' to list the readable files."
    )


def build_tools(settings: Settings) -> list[StructuredTool]:
    def web_search(query: str) -> str:
        return search_web(query, settings.search_max_results, settings.search_timeout)

    def calculator(expression: str) -> str:
        return calculate(expression)

    def read_file_tool(filename: str) -> str:
        return read_file(filename, settings.workspace_dir, settings.max_file_bytes)

    return [
        StructuredTool.from_function(
            func=web_search, name="web_search", args_schema=SearchInput,
            description="Search the web (DuckDuckGo) for current or changing information. "
                        "Returns titles, URLs and snippets. Results are not verified facts."),
        StructuredTool.from_function(
            func=calculator, name="calculator", args_schema=CalcInput,
            description="Safely evaluate an arithmetic expression. Supports + - * / // % **, "
                        "parentheses, sqrt, abs, round, min, max, floor, ceil, log, pi, e."),
        StructuredTool.from_function(
            func=read_file_tool, name="read_file", args_schema=FileInput,
            description="Read a .txt, .md or .json file from the permitted folder (read-only). "
                        "Use filename '.' to list available files."),
    ]
