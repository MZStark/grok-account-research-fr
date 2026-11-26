"""Generate account strategies from the command line (no dependencies).

Strategies are saved to data/plans/<company>.json, where the web app picks them
up and shows them as ready in the Examples section.

    export XAI_API_KEY=xai-...
    python planner.py "Doctolib"
    python planner.py --examples      # every company in data/examples.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
SCHEMA = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
SYSTEM_PROMPT = (ROOT / "prompts" / "system.md").read_text(encoding="utf-8")
PLANS_DIR = ROOT / "data" / "plans"
API_URL = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/") + "/responses"


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def extract_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    for item in data.get("output", []):
        for part in item.get("content", []) or []:
            if part.get("type") == "output_text" and part.get("text"):
                return part["text"]
    raise RuntimeError("No text in model response")


def build_plan(company: str, model: str) -> dict:
    payload = {
        "model": model,
        "tools": [{"type": "web_search"}],
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Company: {company}\nSearch the web first, then build the account strategy.",
            },
        ],
        "text": {
            "format": {"type": "json_schema", "name": "account_plan", "schema": SCHEMA, "strict": True}
        },
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['XAI_API_KEY']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")
        raise RuntimeError(f"Grok API error {err.code}: {detail}") from err
    return json.loads(extract_text(data))


def save(plan: dict, company: str) -> Path:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    path = PLANS_DIR / f"{slugify(company)}.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate sourced account strategies.")
    parser.add_argument("company", nargs="?", help="Company name, e.g. 'Doctolib'")
    parser.add_argument("--examples", action="store_true", help="Generate every company in data/examples.json")
    parser.add_argument("--model", default=os.environ.get("GROK_MODEL", "grok-4.7"))
    args = parser.parse_args(argv)

    if not os.environ.get("XAI_API_KEY"):
        print("Set XAI_API_KEY first (see .env.example).", file=sys.stderr)
        return 1

    if args.examples:
        companies = [a["name"] for a in json.loads((ROOT / "data" / "examples.json").read_text(encoding="utf-8"))]
    elif args.company:
        companies = [args.company]
    else:
        parser.error("give a company name or --examples")

    failures = 0
    for company in companies:
        print(f"→ {company} …", flush=True)
        try:
            path = save(build_plan(company, args.model), company)
            print(f"  saved {path.relative_to(ROOT)}")
        except Exception as err:  # keep going through the list
            failures += 1
            print(f"  failed: {err}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
