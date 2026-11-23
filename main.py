"""CLI: python main.py "Company name" [-o report.md]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.config import ConfigError, Settings
from core.llm import GrokAPIError
from core.pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grok Bot account research for a French company.")
    parser.add_argument("company", help="Company name, e.g. \"Qonto\"")
    parser.add_argument("-o", "--output", type=Path, help="Output Markdown file (default: print to stdout)")
    args = parser.parse_args(argv)

    try:
        settings = Settings.from_env()
        report = run(args.company, settings, log=lambda m: print(m, file=sys.stderr))
    except (ConfigError, GrokAPIError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
