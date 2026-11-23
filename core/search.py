"""Fallback web search (Tavily) for when Grok's built-in web_search tool is not used."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .llm import GrokAPIError

TAVILY_URL = "https://api.tavily.com/search"


def tavily_search(query: str, api_key: str, max_results: int = 8, timeout_s: float = 30.0) -> list[dict]:
    """Return a list of {title, url, content} results."""
    payload = json.dumps(
        {"query": query, "max_results": max_results, "search_depth": "advanced", "topic": "general"}
    ).encode()
    request = urllib.request.Request(
        TAVILY_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as resp:  # noqa: S310 - fixed https URL
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GrokAPIError(f"Web search (Tavily) failed: {exc}") from exc
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
        for r in data.get("results", [])
    ]


def format_results(results: list[dict]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}\n{r['url']}\n{r['content'][:800]}")
    return "\n\n".join(lines)
