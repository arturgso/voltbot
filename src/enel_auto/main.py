from __future__ import annotations

import argparse
import time
import traceback
from datetime import date, datetime

from enel_auto.config import get_settings
from enel_auto.contacts import load_contacts_for_installation
from enel_auto.domain import EnelBill, PendingDelivery
from enel_auto.evolution import EvolutionError, send_pending_deliveries
from enel_auto.imap_client import find_day_emails
from enel_auto.parsers import parse_mail_message
from enel_auto.state import already_processed
from enel_auto.storage import save_pdf

DEFAULT_POLL_INTERVAL_SECONDS = 3600


def process_day(day: date | None = None) -> list[PendingDelivery]:
    """Orchestrate the IMAP fetch, parser, contacts and storage steps.

    This function returns domain-ready objects for the message-delivery layer.
    The state is marked only after a successful delivery.
    """
    resolved_day = day or date.today()
    emails = find_day_emails(resolved_day)
    deliveries: list[PendingDelivery] = []

    for msg in emails:
        bill = parse_mail_message(msg)
        if bill is None:
            continue

        if already_processed(bill.installation, bill.pdf_name):
            continue

        pdf_path = save_pdf(bill)
        contacts = load_contacts_for_installation(bill.installation)
        bill_with_path = EnelBill(
            installation=bill.installation,
            subject=bill.subject,
            date=bill.date,
            pdf_name=bill.pdf_name,
            pdf_bytes=bill.pdf_bytes,
            pdf_path=pdf_path,
        )
        deliveries.append(PendingDelivery(bill=bill_with_path, contacts=contacts))

    return deliveries


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Processa faturas da Enel recebidas por email e envia via Evolution API."
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        help="Data para busca de faturas no email (formato AAAA-MM-DD). "
        "Se omitido, usa o dia atual a cada ciclo.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=None,
        help="Intervalo entre ciclos em segundos (padrão: POLL_INTERVAL_SECONDS ou 3600). "
        "Use 0 para rodar uma única vez.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Roda um único ciclo e sai (equivale a --interval-seconds 0).",
    )
    return parser.parse_args(args)


def resolve_target_day(cli_date: date | None) -> date:
    """Dia a processar: fixo via --date ou o dia atual (para virar o dia no loop)."""
    return cli_date or date.today()


def resolve_interval_seconds(cli_interval: int | None) -> int:
    """Intervalo entre ciclos: flag --interval-seconds ou POLL_INTERVAL_SECONDS do ambiente."""
    if cli_interval is not None:
        return cli_interval
    try:
        return get_settings().poll_interval_seconds
    except Exception:
        return DEFAULT_POLL_INTERVAL_SECONDS


def run_cycle(target_day: date) -> int:
    print(f"[{datetime.now():%d/%m/%Y %H:%M:%S}] Buscando faturas para o dia {target_day:%d/%m/%Y}...")
    deliveries = process_day(target_day)
    print(f"Encontradas {len(deliveries)} contas")

    for delivery in deliveries:
        bill = delivery.bill
        print(
            f"- Instalação {bill.installation} | {bill.date} | "
            f"{bill.pdf_name} ({len(bill.pdf_bytes):,} bytes)"
        )

    results = send_pending_deliveries(deliveries)
    print(f"Enviadas {len(results)} mensagens pela Evolution API")
    return len(results)


def main() -> None:
    cli_args = parse_args()
    interval = 0 if cli_args.once else resolve_interval_seconds(cli_args.interval_seconds)

    if interval <= 0:
        try:
            run_cycle(resolve_target_day(cli_args.date))
        except EvolutionError as exc:
            raise SystemExit(f"Falha no envio pela Evolution API: {exc}") from exc
        return

    print(f"Loop ativado: ciclo a cada {interval}s (use --once para rodada única).")
    while True:
        try:
            run_cycle(resolve_target_day(cli_args.date))
        except EvolutionError as exc:
            print(f"Falha no envio pela Evolution API: {exc} — tentando de novo em {interval}s")
        except Exception:
            print("Erro inesperado no ciclo — tentando de novo no próximo intervalo:")
            traceback.print_exc()
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Encerrando loop.")
            break


if __name__ == "__main__":
    main()
