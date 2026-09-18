from __future__ import annotations

from datetime import date, timedelta

from enel_auto.contacts import load_contacts_for_installation
from enel_auto.domain import EnelBill, PendingDelivery
from enel_auto.imap_client import find_day_emails
from enel_auto.parsers import parse_mail_message
from enel_auto.state import already_processed, mark_processed
from enel_auto.storage import save_pdf


def process_day(day: date | None = None) -> list[PendingDelivery]:
    """Orchestrate the IMAP fetch, parser, contacts and storage steps.

    This function returns domain-ready objects for a future message-delivery
    layer. It intentionally avoids any WhatsApp or Evolution API integration.
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
        mark_processed(bill.installation, bill.pdf_name)

    return deliveries


def main() -> None:
    test_day = date.today() - timedelta(days=1)
    deliveries = process_day(test_day)
    print(f"Encontradas {len(deliveries)} contas")

    for delivery in deliveries:
        bill = delivery.bill
        print(
            f"- Instalação {bill.installation} | {bill.date} | "
            f"{bill.pdf_name} ({len(bill.pdf_bytes):,} bytes)"
        )


if __name__ == "__main__":
    main()