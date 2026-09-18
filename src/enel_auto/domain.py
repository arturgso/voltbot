from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

SUBJECT_FILTER = "Enel - Conta por email"
INSTALLATION_KEY = "INSTALAÇÃO/UC"


@dataclass(frozen=True)
class EnelBill:
    installation: str
    subject: str
    date: date
    pdf_name: str
    pdf_bytes: bytes
    pdf_path: str | None = None


@dataclass(frozen=True)
class WhatsAppContact:
    installation: str
    phone: str
    name: str | None = None


@dataclass(frozen=True)
class PendingDelivery:
    bill: EnelBill
    contacts: list[WhatsAppContact]


@dataclass(frozen=True)
class ProcessingState:
    installation: str
    pdf_name: str
    processed_at: date
    metadata: dict[str, Any] | None = None
