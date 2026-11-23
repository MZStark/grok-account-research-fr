"""Step 3: write the first outreach message in French (under 120 words), then translate it."""

from __future__ import annotations

import re

from core import prompts
from core.llm import LLM

SYSTEM = "You write short, human, precise outreach messages in French for French companies."
TRANSLATE_SYSTEM = "You are a professional French-to-English translator."
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
        user += f"\n\nYour message is {count_words(message)} words long. Shorten it to under {MAX_WORDS} words, still in French."
    return message  # still too long after retries: returned as is, flagged by the pipeline


def translate_outreach(message: str, llm: LLM) -> str:
    """English translation of the final French message, for readers who do not speak French."""
    return llm.complete(TRANSLATE_SYSTEM, prompts.load("translation", message=message)).text.replace("—", ",").strip()
