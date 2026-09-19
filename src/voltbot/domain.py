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
    barcode: str | None = None
    amount: str | None = None


@dataclass(frozen=True)
class WhatsAppContact:
    installation: str
    phone: str
    name: str | None = None
    installation_label: str | None = None


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


def normalize_phone(number: str) -> str:
    digits = "".join(char for char in str(number) if char.isdigit())
    if len(digits) in {10, 11}:
        return f"55{digits}"
    return digits

