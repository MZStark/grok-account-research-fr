"""Step 2: derive the 3 most relevant Grok Bot use cases from the account brief."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from core import prompts
from core.llm import LLM, GrokAPIError

SYSTEM = "You are a solutions engineer. You answer only with valid JSON."
REQUIRED = ("title", "team", "problem", "benefit", "signal")


@dataclass
class UseCase:
    title: str
    team: str
    problem: str
    benefit: str
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
            user += f"\n\nYour previous answer was invalid ({last_error}). Return only the requested JSON."
    raise GrokAPIError(f"Use cases still unreadable after a retry: {last_error}")


def _parse(text: str) -> list[UseCase]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc
    items = data.get("use_cases")
    if not isinstance(items, list) or len(items) < 3:
        raise ValueError("3 use cases are required")
    cases = []
    for item in items[:3]:
        missing = [k for k in REQUIRED if not str(item.get(k, "")).strip()]
        if missing:
            raise ValueError(f"missing fields: {', '.join(missing)}")
        cases.append(UseCase(**{k: str(item[k]).strip() for k in REQUIRED}))
    return cases


def to_markdown(cases: list[UseCase]) -> str:
    lines = ["## Grok Bot use cases"]
    for i, c in enumerate(cases, 1):
        lines += [
            "",
            f"### {i}. {c.title}",
            f"- **Team**: {c.team}",
            f"- **Problem**: {c.problem}",
            f"- **Expected benefit**: {c.benefit}",
            f"- **Signal**: {c.signal}",
        ]
    return "\n".join(lines)
