import re
from dataclasses import dataclass
from datetime import date, timedelta

from imap_tools import AND, MailBox, MailMessage

from enel_auto.config import get_settings

SUBJECT_FILTER = "Enel - Conta por email"

INSTALLATION_REGEX = re.compile(
    r"INSTALA[ÇC][ÃA]O/UC[:\s]*(\d+)",
    re.IGNORECASE,
)


@dataclass
class EnelBill:
    installation: str      # mantém zero à esquerda: "0200420281"
    subject: str
    date: date
    pdf_name: str
    pdf_bytes: bytes


def _extract_installation(msg: MailMessage) -> str | None:
    body = msg.text or msg.html or ""
    match = INSTALLATION_REGEX.search(body)
    return match.group(1) if match else None


def _extract_pdf(msg: MailMessage) -> tuple[str, bytes] | None:
    for att in msg.attachments:
        name = (att.filename or "").lower()
        if name.endswith(".pdf") or att.content_type == "application/pdf":
            return att.filename, att.payload
    return None


def _find_day_emails(day: date) -> list[MailMessage]:
    settings = get_settings()
    with MailBox(settings.imap_host).login(
        settings.imap_user, settings.imap_pass, "INBOX"
    ) as mailbox:
        return list(
            mailbox.fetch(
                AND(subject=SUBJECT_FILTER, date=day),
                mark_seen=False,
                reverse=True,
            )
        )


def find_bills_for_day(day: date | None = None) -> list[EnelBill]:
    day = day or date.today()
    bills: list[EnelBill] = []

    for msg in _find_day_emails(day):
        installation = _extract_installation(msg)
        if not installation:
            print(f"[SKIP] Sem instalação: {msg.subject} ({msg.date})")
            continue

        pdf = _extract_pdf(msg)
        if not pdf:
            print(f"[SKIP] Sem PDF: instalação {installation} ({msg.date})")
            continue

        pdf_name, pdf_bytes = pdf
        bills.append(
            EnelBill(
                installation=installation,
                subject=msg.subject,
                date=msg.date.date(),
                pdf_name=pdf_name,
                pdf_bytes=pdf_bytes,
            )
        )

    return bills


def main():
    test_day = date.today() - timedelta(days=1)
    bills = find_bills_for_day(test_day)
    print(f"Encontradas {len(bills)} contas")

    for b in bills:
        print(
            f"- Instalação {b.installation} | {b.date} | "
            f"{b.pdf_name} ({len(b.pdf_bytes):,} bytes)"
        )


if __name__ == "__main__":
    main()