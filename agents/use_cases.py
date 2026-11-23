"""Step 2: derive the 3 most relevant Grok Bot use cases from the account brief."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from core import prompts
from core.llm import LLM, GrokAPIError

SYSTEM = "Tu es solutions engineer. Tu réponds uniquement en JSON valide."
REQUIRED = ("titre", "equipe", "probleme", "benefice", "signal")


@dataclass
class UseCase:
    titre: str
    equipe: str
    probleme: str
    benefice: str
    signal: str


def derive_use_cases(account_markdown: str, llm: LLM, retries: int = 1) -> list[UseCase]:
    user = prompts.load("use_cases", product=prompts.load("product"), account=account_markdown)
    last_error = ""
    for _ in range(retries + 1):
        text = llm.complete(SYSTEM, user).text
        try:
            return _parse(text)
        except ValueError as exc:
            last_error = str(exc)
            user += f"\n\nTa réponse précédente était invalide ({last_error}). Renvoie uniquement le JSON demandé."
    raise GrokAPIError(f"Use cases still unreadable after a retry: {last_error}")


def _parse(text: str) -> list[UseCase]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("aucun objet JSON trouvé")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalide : {exc.msg}") from exc
    items = data.get("cas_usage")
    if not isinstance(items, list) or len(items) < 3:
        raise ValueError("il faut 3 cas d'usage")
    cases = []
    for item in items[:3]:
        missing = [k for k in REQUIRED if not str(item.get(k, "")).strip()]
        if missing:
            raise ValueError(f"champs manquants : {', '.join(missing)}")
        cases.append(UseCase(**{k: str(item[k]).strip() for k in REQUIRED}))
    return cases


def to_markdown(cases: list[UseCase]) -> str:
    lines = ["## Cas d'usage Grok Bot"]
    for i, c in enumerate(cases, 1):
        lines += [
            "",
            f"### {i}. {c.titre}",
            f"- **Équipe concernée** : {c.equipe}",
            f"- **Problème** : {c.probleme}",
            f"- **Bénéfice attendu** : {c.benefice}",
            f"- **Signal** : {c.signal}",
        ]
    return "\n".join(lines)
