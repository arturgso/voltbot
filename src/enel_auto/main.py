from __future__ import annotations

import argparse
from datetime import date

from enel_auto.contacts import load_contacts_for_installation
from enel_auto.domain import EnelBill, PendingDelivery
from enel_auto.evolution import EvolutionError, send_pending_deliveries
from enel_auto.imap_client import find_day_emails
from enel_auto.parsers import parse_mail_message
from enel_auto.state import already_processed
from enel_auto.storage import save_pdf


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
        default=date(2026, 9, 13),
        help="Data para busca de faturas no email (formato AAAA-MM-DD). Padrão: 2026-09-13.",
    )
    return parser.parse_args(args)


def main() -> None:
    cli_args = parse_args()
    target_day = cli_args.date
    print(f"Buscando faturas para o dia {target_day:%d/%m/%Y}...")
    deliveries = process_day(target_day)
    print(f"Encontradas {len(deliveries)} contas")

    for delivery in deliveries:
        bill = delivery.bill
        print(
            f"- Instalação {bill.installation} | {bill.date} | "
            f"{bill.pdf_name} ({len(bill.pdf_bytes):,} bytes)"
        )

    try:
        results = send_pending_deliveries(deliveries)
    except EvolutionError as exc:
        raise SystemExit(f"Falha no envio pela Evolution API: {exc}") from exc

    print(f"Enviadas {len(results)} mensagens pela Evolution API")


if __name__ == "__main__":
    main()
