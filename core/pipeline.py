"""Runs the three agents in sequence and assembles the final Markdown report."""

from __future__ import annotations

import re
from datetime import date

from agents.outreach import MAX_WORDS, count_words, write_outreach
from agents.research import research
from agents.use_cases import derive_use_cases, to_markdown
from core.config import Settings
from core.llm import LLM, GrokClient


def run(company: str, settings: Settings, llm: LLM | None = None, log=lambda msg: None) -> str:
    llm = llm or GrokClient(settings)

    log("1/3 Researching the company...")
    brief = research(company, llm, settings)

    log("2/3 Deriving use cases...")
    cases_md = to_markdown(derive_use_cases(brief.markdown, llm))

    log("3/3 Writing the outreach message...")
    message = write_outreach(brief.markdown, cases_md, llm)
    words = count_words(message)
    warning = f"\n\n> Attention : {words} mots, au-dessus de la limite de {MAX_WORDS}." if words >= MAX_WORDS else ""

    sources = "\n".join(f"- {url}" for url in brief.sources) or "- (aucune source renvoyée par l'API)"
    report = (
        f"# {brief.company} : recherche de compte Grok Bot\n\n"
        f"_Généré le {date.today():%d/%m/%Y} avec le modèle {settings.model}. "
        f"À vérifier avant tout envoi._\n\n"
        f"{brief.markdown.strip()}\n\n"
        f"{cases_md}\n\n"
        f"## Premier message de prospection ({words} mots)\n\n{message}{warning}\n\n"
        f"## Sources\n\n{sources}\n"
    )
    return dedupe_citations(report)


_DUPLICATE_CITATION = re.compile(r"(\[\[\d+\]\]\([^)\s]*\))(?:\s*\1)+")


def dedupe_citations(text: str) -> str:
    """Collapse identical adjacent citations: "[[1]](u) [[1]](u)" -> "[[1]](u)"."""
    return _DUPLICATE_CITATION.sub(r"\1", text)
