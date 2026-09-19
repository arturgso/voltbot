from __future__ import annotations

from enel_auto.config import get_settings
from enel_auto.domain import WhatsAppContact


def normalize_installation_key(installation: str) -> str:
    return str(installation).strip().replace(" ", "")


def load_contacts_for_installation(installation: str) -> list[WhatsAppContact]:
    """Return WhatsAppContact objects for a normalized installation key.

    Single source of truth is the SQLite database (managed via the web UI).
    It keeps the contact lookup isolated in its own module and creates no
    Evolution API or WhatsApp side effect.
    """
    from enel_auto.db import Database, seed_from_settings

    settings = get_settings()
    db = Database(settings.db_path)
    try:
        seed_from_settings(db, settings)
        rows = db.list_contacts(normalize_installation_key(installation))
    finally:
        db.close()
    return [
        WhatsAppContact(
            installation=normalize_installation_key(installation),
            phone=row["phone"],
            name=row["name"],
            installation_label=(row.get("installation_label") or None),
        )
        for row in rows
    ]
