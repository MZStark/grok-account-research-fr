"""Step 3: write the first outreach message (under 120 words)."""

from __future__ import annotations

import re

from core import prompts
from core.llm import LLM

SYSTEM = "Tu écris des messages de prospection courts, humains et précis, en français."
MAX_WORDS = 120


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


def write_outreach(account_markdown: str, use_cases_markdown: str, llm: LLM, retries: int = 1) -> str:
    user = prompts.load(
        "outreach",
        account=account_markdown,
        use_cases=use_cases_markdown,
        max_words=str(MAX_WORDS),
    )
    message = ""
    for _ in range(retries + 1):
        message = llm.complete(SYSTEM, user).text.replace("—", ",").strip()
        if count_words(message) < MAX_WORDS:
            return message
        user += f"\n\nTon message fait {count_words(message)} mots. Raccourcis-le sous {MAX_WORDS} mots."
    return message  # still too long after retries: returned as is, flagged by the pipeline
