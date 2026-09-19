from __future__ import annotations

import re
from datetime import date

from imap_tools import MailMessage

from voltbot.domain import EnelBill

INSTALLATION_REGEX = re.compile(r"INSTALA[ÇC][ÃA]O/UC[:\s]*(\d+)", re.IGNORECASE)


def extract_installation_from_body(body: str) -> str | None:
    """Extract the installation number from the plain or HTML body text.

    The regex is kept out of imap_client.py and stays here by design.
    """
    match = INSTALLATION_REGEX.search(body or "")
    if not match:
        return None
    return match.group(1)


def extract_pdf_from_message(msg: MailMessage) -> tuple[str, bytes] | None:
    """Extract the first PDF attachment from a fetched message.

    Returns filename + payload bytes. No IMAP resolution is performed here.
    """
    for att in getattr(msg, "attachments", []):
        filename = (att.filename or "").lower()
        if filename.endswith(".pdf") or att.content_type == "application/pdf":
            return att.filename, att.payload
    return None


def parse_mail_message(msg: MailMessage) -> EnelBill | None:
    """Parse an IMAP message into an EnelBill domain object.

    This parser intentionally does not talk to IMAP; it only reads message body
    and attachment metadata already in the message object.
    """
    body = msg.text or msg.html or ""
    installation = extract_installation_from_body(body)
    if not installation:
        return None

    pdf = extract_pdf_from_message(msg)
    if not pdf:
        return None

    pdf_name, pdf_bytes = pdf
    return EnelBill(
        installation=installation,
        subject=msg.subject,
        date=msg.date.date(),
        pdf_name=pdf_name,
        pdf_bytes=pdf_bytes,
    )
