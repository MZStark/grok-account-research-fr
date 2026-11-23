"""Configuration loaded from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # python-dotenv is optional at runtime
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


class ConfigError(RuntimeError):
    """Raised when a required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    xai_api_key: str
    xai_base_url: str = "https://api.x.ai/v1"
    model: str = "grok-4.7"
    search_provider: str = "grok"  # "grok" (built-in web_search tool) or "tavily"
    tavily_api_key: str | None = None
    timeout_s: float = 300.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.getenv("XAI_API_KEY", "").strip()
        if not key:
            raise ConfigError(
                "XAI_API_KEY est manquante. Copiez .env.example en .env et renseignez votre clé xAI."
            )
        provider = os.getenv("SEARCH_PROVIDER", "grok").strip().lower()
        if provider not in {"grok", "tavily"}:
            raise ConfigError("SEARCH_PROVIDER doit valoir 'grok' ou 'tavily'.")
        tavily = os.getenv("TAVILY_API_KEY", "").strip() or None
        if provider == "tavily" and not tavily:
            raise ConfigError("SEARCH_PROVIDER=tavily demande TAVILY_API_KEY.")
        return cls(
            xai_api_key=key,
            xai_base_url=os.getenv("XAI_BASE_URL", cls.xai_base_url).strip(),
            model=os.getenv("GROK_MODEL", cls.model).strip(),
            search_provider=provider,
            tavily_api_key=tavily,
            timeout_s=float(os.getenv("REQUEST_TIMEOUT_S", cls.timeout_s)),
            max_retries=int(os.getenv("MAX_RETRIES", cls.max_retries)),
        )
