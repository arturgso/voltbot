from __future__ import annotations

from datetime import date

from imap_tools import AND, MailBox, MailMessage

from enel_auto.config import get_settings
from enel_auto.domain import SUBJECT_FILTER


def find_day_emails(day: date | None = None) -> list[MailMessage]:
    """Fetch Gmail messages for the requested day with the Enel subject filter.

    This module is deliberately limited to IMAP connection and fetching only.
    """
    settings = get_settings()
    target_day = day or date.today()

    with MailBox(settings.imap_host).login(
        settings.imap_user,
        settings.imap_pass,
        "INBOX",
    ) as mailbox:
        return list(
            mailbox.fetch(
                AND(subject=SUBJECT_FILTER, date=target_day),
                mark_seen=False,
                reverse=True,
            )
        )
