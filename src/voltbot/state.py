from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from voltbot.config import get_settings
from voltbot.domain import normalize_phone


def state_path_for_key(path: str | Path | None = None) -> Path:
    configured = Path(path or get_settings().state_path)
    configured.parent.mkdir(parents=True, exist_ok=True)
    return configured


def load_state(path: str | Path | None = None) -> dict[str, Any]:
    file_path = state_path_for_key(path)
    if not file_path.exists():
        return {}
    try:
        loaded = json.loads(file_path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def mark_processed(installation: str, pdf_name: str, path: str | Path | None = None) -> None:
    file_path = state_path_for_key(path)
    state = load_state(file_path)
    key = f"{installation}:{pdf_name}"
    state[key] = {"processed": True}
    file_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def already_processed(installation: str, pdf_name: str, path: str | Path | None = None) -> bool:
    return f"{installation}:{pdf_name}" in load_state(path)


def is_intro_sent(phone: str, path: str | Path | None = None) -> bool:
    normalized = normalize_phone(phone)
    return f"intro:{normalized}" in load_state(path)


def mark_intro_sent(phone: str, path: str | Path | None = None) -> None:
    normalized = normalize_phone(phone)
    file_path = state_path_for_key(path)
    state = load_state(file_path)
    state[f"intro:{normalized}"] = {
        "sent": True,
        "sent_at": datetime.now().isoformat(),
    }
    file_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

