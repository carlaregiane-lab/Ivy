"""Interface de texto da Ivy Lab."""

from __future__ import annotations

import argparse
from pathlib import Path

from .assistant import run_assistant
from .interpreter import interpret_requirements
from .reporting import render_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transforma um pedido informal em requisitos de engenharia."
    )
    parser.add_argument("request", nargs="?", help="Descrição do projeto")
    parser.add_argument(
        "--assistant",
        action="store_true",
        help="Abre a conversa contínua com a assistente Ivy",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "demo", "api"),
        default="auto",
        help="auto usa a API quando disponível; demo funciona localmente",
    )
    parser.add_argument("--json", action="store_true", help="Mostra JSON em vez do relatório")
    parser.add_argument("--save", type=Path, help="Salva também o briefing em JSON")
    parser.add_argument(
        "--memory",
        type=Path,
        help="Arquivo alternativo para a memória local da assistente",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.assistant or args.request is None:
        try:
            return run_assistant(mode=args.mode, memory_path=args.memory)
        except (ValueError, RuntimeError) as exc:
            print(f"Erro: {exc}")
            return 2

    request = args.request

    try:
        brief = interpret_requirements(request, mode=args.mode)
    except (ValueError, RuntimeError) as exc:
        print(f"Erro: {exc}")
        return 2

    json_output = brief.model_dump_json(indent=2)
    print(json_output if args.json else render_report(brief))

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(json_output + "\n", encoding="utf-8")
        print(f"\nBriefing salvo em: {args.save.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
