from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from enel_auto.config import get_settings


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
