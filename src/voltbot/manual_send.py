from __future__ import annotations

import argparse
from pathlib import Path

from voltbot.evolution import EvolutionClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Envia mensagens de teste pela Evolution API.")
    parser.add_argument("numbers", nargs="+", help="Numeros destino, com ou sem prefixo 55.")
    parser.add_argument("--text", help="Texto de teste para enviar antes do PDF.")
    parser.add_argument("--pdf", type=Path, help="Arquivo PDF para enviar como documento.")
    parser.add_argument("--caption", default="Teste de envio VoltBot", help="Legenda do PDF.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = EvolutionClient()

    for number in args.numbers:
        if args.text:
            result = client.send_text(number, args.text)
            print(f"texto {result.number}: HTTP {result.status_code}")
        if args.pdf:
            result = client.send_pdf(number, args.pdf, args.caption)
            print(f"pdf {result.number}: HTTP {result.status_code}")
