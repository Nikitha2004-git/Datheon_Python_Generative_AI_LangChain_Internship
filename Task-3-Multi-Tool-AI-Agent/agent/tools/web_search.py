"""Real-time web search using DuckDuckGo (``ddgs`` package, no API key needed).

Results are retrieved snippets, NOT verified facts.
"""
from __future__ import annotations

from typing import Callable

MAX_QUERY_LENGTH = 300
MAX_SNIPPET_CHARS = 400


def _default_client_factory(timeout: int):
    from ddgs import DDGS  # imported lazily so a missing package gives a friendly error

    return DDGS(timeout=timeout)


def search_web(
    query: str,
    max_results: int = 5,
    timeout: int = 15,
    client_factory: Callable[[int], object] | None = None,
) -> str:
    """Tool entry point: always returns a string (never raises)."""
    if not isinstance(query, str) or not query.strip():
        return "Web search error: please provide a search query."
    query = query.strip()[:MAX_QUERY_LENGTH]
    factory = client_factory or _default_client_factory
    try:
        client = factory(timeout)
        results = client.text(query, max_results=max_results)
    except ImportError:
        return ("Web search error: the 'ddgs' package is not installed. "
                "Run: pip install -r requirements.txt")
    except Exception as exc:  # noqa: BLE001 - network libraries raise many exception types
        name = type(exc).__name__
        if "Ratelimit" in name:
            return "Web search error: rate limit reached. Please wait a minute and try again."
        if "Timeout" in name or isinstance(exc, TimeoutError):
            return "Web search error: the search timed out. Check your internet and try again."
        if "No results" in str(exc):
            return f"No web results found for: {query!r}."
        return ("Web search error: could not complete the search "
                f"({name}). Check your internet connection and try again.")
    results = list(results or [])
    if not results:
        return f"No web results found for: {query!r}."
    lines = [
        f"Web search results for {query!r} "
        "(retrieved snippets - not verified facts; may be incomplete or outdated):"
    ]
    for i, item in enumerate(results[:max_results], start=1):
        title = str(item.get("title") or "(no title)").strip()
        url = str(item.get("href") or item.get("url") or "(no URL)").strip()
        snippet = " ".join(str(item.get("body") or item.get("snippet") or "").split())
        if len(snippet) > MAX_SNIPPET_CHARS:
            snippet = snippet[:MAX_SNIPPET_CHARS] + "..."
        lines.append(f"{i}. {title}\n   URL: {url}\n   Snippet: {snippet or '(none)'}")
    return "\n".join(lines)
