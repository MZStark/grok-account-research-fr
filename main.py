"""CLI: python main.py "Nom de l'entreprise" [-o rapport.md]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.config import ConfigError, Settings
from core.llm import GrokAPIError
from core.pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recherche de compte Grok Bot pour une entreprise française.")
    parser.add_argument("company", help="Nom de l'entreprise, ex. \"Qonto\"")
    parser.add_argument("-o", "--output", type=Path, help="Fichier Markdown de sortie (sinon : affichage)")
    args = parser.parse_args(argv)

    try:
        settings = Settings.from_env()
        report = run(args.company, settings, log=lambda m: print(m, file=sys.stderr))
    except (ConfigError, GrokAPIError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrompu.", file=sys.stderr)
        return 130

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Rapport écrit dans {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
