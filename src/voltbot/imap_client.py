from __future__ import annotations

from datetime import date

from imap_tools import AND, MailBox, MailMessage

from voltbot.config import get_settings
from voltbot.domain import SUBJECT_FILTER


def _fetch_from_account(
    host: str, username: str, password: str, criteria: AND
) -> list[MailMessage]:
    """Fetch messages from a single IMAP account. Limited to IMAP I/O."""
    with MailBox(host).login(username, password, "INBOX") as mailbox:
        return list(mailbox.fetch(criteria, mark_seen=False, reverse=True))


def _iter_account_credentials() -> list[tuple[str, str, str, str]]:
    """Return (label, host, username, password) for every enabled email account.

    Prefers the SQLite accounts table (seeded from settings on first use) so
    new accounts added via UI are picked up without restart.
    """
    from voltbot.db import Database, seed_from_settings

    settings = get_settings()
    try:
        db = Database(settings.db_path)
    except Exception:
        db = None
    if db is None:
        return [("Principal", settings.imap_host, settings.imap_user, settings.imap_pass)]
    try:
        seed_from_settings(db, settings)
        accounts = db.enabled_email_accounts()
    finally:
        db.close()
    if not accounts:
        return [("Principal", settings.imap_host, settings.imap_user, settings.imap_pass)]
    return [(acc.label, acc.host, acc.username, acc.password) for acc in accounts]


def find_day_emails(day: date | None = None) -> list[MailMessage]:
    """Fetch Enel messages for the requested day across all enabled accounts.

    This module is deliberately limited to IMAP connection and fetching only.
    """
    target_day = day or date.today()
    criteria = AND(subject=SUBJECT_FILTER, date=target_day)
    messages: list[MailMessage] = []
    for _label, host, username, password in _iter_account_credentials():
        messages.extend(_fetch_from_account(host, username, password, criteria))
    return messages


def find_range_emails(start: date, end_exclusive: date) -> list[MailMessage]:
    """Fetch Enel messages in [start, end_exclusive) across all accounts.

    Used by the "whole month" mode: pass the first day of the month and the
    first day of the next month.
    """
    criteria = AND(subject=SUBJECT_FILTER, date_gte=start, date_lt=end_exclusive)
    messages: list[MailMessage] = []
    for _label, host, username, password in _iter_account_credentials():
        messages.extend(_fetch_from_account(host, username, password, criteria))
    return messages
