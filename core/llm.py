"""Thin wrapper around the xAI (Grok) API, used through the OpenAI-compatible SDK.

Every call goes through the Responses API, which is where xAI exposes its
server-side `web_search` tool. Transient failures (timeouts, rate limits,
5xx) are retried with exponential backoff; anything else surfaces as a
`GrokAPIError` with a French, human-readable message.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .config import Settings


class GrokAPIError(RuntimeError):
    """The Grok API could not produce an answer."""


@dataclass
class LLMResult:
    text: str
    sources: list[str] = field(default_factory=list)


class LLM(Protocol):
    def complete(self, system: str, user: str, *, web_search: bool = False) -> LLMResult: ...


class GrokClient:
    """Calls Grok through `openai.OpenAI(base_url="https://api.x.ai/v1")`."""

    def __init__(self, settings: Settings, client: Any | None = None, sleep=time.sleep):
        self.settings = settings
        self._sleep = sleep
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise GrokAPIError("Le paquet 'openai' n'est pas installé (pip install -r requirements.txt).") from exc
            client = OpenAI(
                api_key=settings.xai_api_key,
                base_url=settings.xai_base_url,
                timeout=settings.timeout_s,
                max_retries=0,  # retries are handled here, with clearer errors
            )
        self._client = client

    def complete(self, system: str, user: str, *, web_search: bool = False) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": self.settings.model,
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if web_search:
            kwargs["tools"] = [{"type": "web_search"}]

        last_error: Exception | None = None
        for attempt in range(1, self.settings.max_retries + 1):
            try:
                response = self._client.responses.create(**kwargs)
                text = (getattr(response, "output_text", "") or "").strip()
                if not text:
                    raise GrokAPIError("Réponse vide de l'API Grok.")
                return LLMResult(text=text, sources=_extract_sources(response))
            except GrokAPIError:
                raise
            except Exception as exc:  # noqa: BLE001 - classified below
                last_error = exc
                if not _is_transient(exc) or attempt == self.settings.max_retries:
                    break
                self._sleep(2 ** (attempt - 1))
        raise GrokAPIError(_explain(last_error)) from last_error


def _is_transient(exc: Exception) -> bool:
    name = type(exc).__name__
    if name in {"APITimeoutError", "APIConnectionError", "RateLimitError", "InternalServerError"}:
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and (status == 429 or status >= 500)


def _explain(exc: Exception | None) -> str:
    if exc is None:
        return "L'API Grok n'a pas répondu."
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__
    if status == 401 or name == "AuthenticationError":
        return "Clé XAI_API_KEY refusée (401). Vérifiez votre clé sur console.x.ai."
    if status == 404 or name == "NotFoundError":
        return "Modèle introuvable (404). Vérifiez GROK_MODEL dans votre .env."
    if status == 429 or name == "RateLimitError":
        return "Limite de requêtes atteinte (429). Réessayez dans quelques minutes."
    if name in {"APITimeoutError", "APIConnectionError"}:
        return "L'API Grok ne répond pas (délai dépassé ou réseau). Réessayez plus tard."
    return f"Erreur de l'API Grok : {name}."


def _extract_sources(response: Any) -> list[str]:
    """Collect cited URLs (url_citation annotations) from a Responses API object."""
    urls: list[str] = []
    for citation in getattr(response, "citations", None) or []:
        url = citation if isinstance(citation, str) else getattr(citation, "url", None)
        if url and url not in urls:
            urls.append(url)
    for item in getattr(response, "output", None) or []:
        for part in getattr(item, "content", None) or []:
            for ann in getattr(part, "annotations", None) or []:
                url = getattr(ann, "url", None)
                if url and url not in urls:
                    urls.append(url)
    return urls
