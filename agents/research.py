"""Step 1: build the account brief from live web sources."""

from __future__ import annotations

from dataclasses import dataclass, field

from core import prompts
from core.config import Settings
from core.llm import LLM
from core.search import format_results, tavily_search

SYSTEM = "Tu es un analyste commercial rigoureux. Tu cites tes sources et tu n'inventes jamais."


@dataclass
class AccountBrief:
    company: str
    markdown: str
    sources: list[str] = field(default_factory=list)


def research(company: str, llm: LLM, settings: Settings, search_fn=tavily_search) -> AccountBrief:
    company = company.strip()
    if not company:
        raise ValueError("Le nom de l'entreprise est vide.")

    if settings.search_provider == "tavily":
        results = search_fn(
            f"{company} entreprise actualités levée de fonds recrutement 2026",
            api_key=settings.tavily_api_key,
        )
        context = "Résultats de recherche à utiliser comme seules sources :\n\n" + format_results(results)
        user = prompts.load("research", company=company, context=context)
        out = llm.complete(SYSTEM, user, web_search=False)
        sources = [r["url"] for r in results if r.get("url")]
    else:
        context = "Utilise l'outil de recherche web pour trouver des sources récentes."
        user = prompts.load("research", company=company, context=context)
        out = llm.complete(SYSTEM, user, web_search=True)
        sources = out.sources

    return AccountBrief(company=company, markdown=strip_preamble(out.text), sources=sources)


def strip_preamble(text: str) -> str:
    """Drop any narration the model emits before the brief heading (kept as is if absent)."""
    start = text.find("## Fiche compte")
    return text[start:] if start != -1 else text
