from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from enel_auto.config import get_settings
from enel_auto.domain import WhatsAppContact


def normalize_installation_key(installation: str) -> str:
    return str(installation).strip().replace(" ", "")


def load_contact_map(path: str | Path | None = None) -> dict[str, list[Any]]:
    """Load a YAML mapping of installation -> contacts.

    The repository uses an external YAML file; this module is limited to that
    file load and normalization. The structure is expected to be:
        0200420281:
          - 551199999999
          - 551188888888
    """
    configured_path = path or get_settings().contacts_path
    yaml_path = Path(configured_path)
    if not yaml_path.exists():
        return {}

    with yaml_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        return {}

    return {
        normalize_installation_key(str(key)): value
        for key, value in loaded.items()
    }


def load_contacts_for_installation(
    installation: str,
    path: str | Path | None = None,
) -> list[WhatsAppContact]:
    """Return WhatsAppContact objects for a normalized installation key.

    It keeps the contact lookup isolated in its own module and creates no
    Evolution API or WhatsApp side effect.
    """
    mapping = load_contact_map(path)
    contacts = mapping.get(normalize_installation_key(installation), [])
    if not isinstance(contacts, list):
        contacts = []

    result: list[WhatsAppContact] = []
    for item in contacts:
        if isinstance(item, str):
            result.append(
                WhatsAppContact(
                    installation=normalize_installation_key(installation),
                    phone=item.strip(),
                    name=None,
                )
            )
        elif isinstance(item, dict):
            phone = str(
                item.get("phone")
                or item.get("number")
                or item.get("telefone")
                or ""
            )
            raw_name = item.get("name") or item.get("nome")
            clean_name = str(raw_name).strip() if raw_name is not None else None
            resolved_name = clean_name or None
            if phone.strip():
                result.append(
                    WhatsAppContact(
                        installation=normalize_installation_key(installation),
                        phone=phone.strip(),
                        name=resolved_name,
                    )
                )

    return result
