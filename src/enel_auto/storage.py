from __future__ import annotations

from pathlib import Path

from enel_auto.config import get_settings
from enel_auto.domain import EnelBill


def save_pdf(bill: EnelBill, downloads_dir: str | Path | None = None) -> str:
    """Persist an EnelBill PDF attachment to the configured downloads folder.

    No parsing or IMAP logic is placed here; this is a file side-effect module.
    """
    storage_path = Path(downloads_dir or get_settings().downloads_dir)
    storage_path.mkdir(parents=True, exist_ok=True)

    destination = storage_path / bill.pdf_name
    destination.write_bytes(bill.pdf_bytes)

    return str(destination)
