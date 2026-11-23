"""Load the plain-text prompts stored in prompts/."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load(name: str, **values: str) -> str:
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text
