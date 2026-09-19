from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS installations (
    code TEXT PRIMARY KEY,
    label TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    installation TEXT NOT NULL REFERENCES installations(code) ON DELETE CASCADE,
    phone TEXT NOT NULL,
    name TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (installation, phone)
);
CREATE TABLE IF NOT EXISTS email_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    host TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    dry_run INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    created_at TEXT NOT NULL,
    finished_at TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ts TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_run_logs_run_id ON run_logs(run_id);
"""


@dataclass(frozen=True)
class EmailAccount:
    id: int
    label: str
    host: str
    username: str
    password: str
    enabled: bool


def _utcnow() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    """SQLite storage for installations, contacts, email accounts and runs.

    stdlib sqlite3 only. One connection per Database instance; callers that
    write from threads should use a dedicated instance (see web job runner).
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- installations ----------------------------------------------------
    def upsert_installation(self, code: str, label: str | None = None) -> str:
        code = code.strip().replace(" ", "")
        self._conn.execute(
            "INSERT INTO installations (code, label, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(code) DO UPDATE SET label=COALESCE(excluded.label, installations.label)",
            (code, label, _utcnow()),
        )
        self._conn.commit()
        return code

    def delete_installation(self, code: str) -> None:
        self._conn.execute("DELETE FROM installations WHERE code = ?", (code,))
        self._conn.commit()

    def list_installations(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT code, label FROM installations ORDER BY code"
        ).fetchall()
        result = []
        for row in rows:
            count = self._conn.execute(
                "SELECT COUNT(*) AS n FROM contacts WHERE installation = ?",
                (row["code"],),
            ).fetchone()["n"]
            result.append(
                {"code": row["code"], "label": row["label"], "contacts": count}
            )
        return result

    # -- contacts ----------------------------------------------------------
    def add_contact(self, installation: str, phone: str, name: str | None = None) -> int:
        code = self.upsert_installation(installation)
        clean_name = (name or "").strip() or None
        cursor = self._conn.execute(
            "INSERT INTO contacts (installation, phone, name, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(installation, phone) DO UPDATE SET name=excluded.name",
            (code, phone.strip(), clean_name, _utcnow()),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT id FROM contacts WHERE installation = ? AND phone = ?",
            (code, phone.strip()),
        ).fetchone()
        return row["id"] if row else cursor.lastrowid

    def delete_contact(self, contact_id: int) -> None:
        self._conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        self._conn.commit()

    def update_contact(
        self, contact_id: int, phone: str | None = None, name: str | None = None
    ) -> dict[str, Any] | None:
        """Update phone and/or name. Raises sqlite3.IntegrityError on duplicate."""
        row = self._conn.execute(
            "SELECT c.id, c.installation, c.phone, c.name, "
            "i.label AS installation_label FROM contacts c "
            "LEFT JOIN installations i ON i.code = c.installation "
            "WHERE c.id = ?",
            (contact_id,),
        ).fetchone()
        if not row:
            return None
        new_phone = phone.strip() if phone is not None else row["phone"]
        new_name = (name.strip() or None) if name is not None else row["name"]
        self._conn.execute(
            "UPDATE contacts SET phone = ?, name = ? WHERE id = ?",
            (new_phone, new_name, contact_id),
        )
        self._conn.commit()
        return {
            "id": contact_id,
            "installation": row["installation"],
            "phone": new_phone,
            "name": new_name,
            "installation_label": row["installation_label"],
        }

    def list_contacts(self, installation: str | None = None) -> list[dict[str, Any]]:
        base = (
            "SELECT c.id, c.installation, c.phone, c.name, "
            "i.label AS installation_label FROM contacts c "
            "LEFT JOIN installations i ON i.code = c.installation"
        )
        if installation:
            rows = self._conn.execute(
                base + " WHERE c.installation = ? ORDER BY c.name, c.phone",
                (installation,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                base + " ORDER BY c.installation, c.name, c.phone"
            ).fetchall()
        return [dict(row) for row in rows]

    # -- email accounts -----------------------------------------------------
    def add_email_account(
        self, label: str, host: str, username: str, password: str, enabled: bool = True
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO email_accounts (label, host, username, password, enabled, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(username) DO UPDATE SET label=excluded.label, host=excluded.host, "
            "password=excluded.password, enabled=excluded.enabled",
            (label.strip(), host.strip(), username.strip(), password, int(enabled), _utcnow()),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT id FROM email_accounts WHERE username = ?", (username.strip(),)
        ).fetchone()
        return row["id"] if row else cursor.lastrowid

    def set_email_account_enabled(self, account_id: int, enabled: bool) -> None:
        self._conn.execute(
            "UPDATE email_accounts SET enabled = ? WHERE id = ?",
            (int(enabled), account_id),
        )
        self._conn.commit()

    def delete_email_account(self, account_id: int) -> None:
        self._conn.execute("DELETE FROM email_accounts WHERE id = ?", (account_id,))
        self._conn.commit()

    def list_email_accounts(self, *, include_password: bool = False) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, label, host, username, password, enabled FROM email_accounts "
            "ORDER BY label"
        ).fetchall()
        result = []
        for row in rows:
            item: dict[str, Any] = {
                "id": row["id"],
                "label": row["label"],
                "host": row["host"],
                "username": row["username"],
                "enabled": bool(row["enabled"]),
            }
            if include_password:
                item["password"] = row["password"]
            result.append(item)
        return result

    def enabled_email_accounts(self) -> list[EmailAccount]:
        rows = self._conn.execute(
            "SELECT id, label, host, username, password, enabled FROM email_accounts "
            "WHERE enabled = 1 ORDER BY label"
        ).fetchall()
        return [
            EmailAccount(
                id=row["id"],
                label=row["label"],
                host=row["host"],
                username=row["username"],
                password=row["password"],
                enabled=True,
            )
            for row in rows
        ]

    # -- runs ---------------------------------------------------------------
    def create_run(self, kind: str, params: dict[str, Any], dry_run: bool) -> int:
        import json

        cursor = self._conn.execute(
            "INSERT INTO runs (kind, params_json, dry_run, status, created_at) "
            "VALUES (?, ?, ?, 'running', ?)",
            (kind, json.dumps(params), int(dry_run), _utcnow()),
        )
        self._conn.commit()
        return cursor.lastrowid

    def log(self, run_id: int, level: str, message: str) -> None:
        self._conn.execute(
            "INSERT INTO run_logs (run_id, ts, level, message) VALUES (?, ?, ?, ?)",
            (run_id, _utcnow(), level, message),
        )
        self._conn.commit()

    def finish_run(self, run_id: int, status: str, summary: dict[str, Any]) -> None:
        import json

        self._conn.execute(
            "UPDATE runs SET status = ?, finished_at = ?, summary_json = ? WHERE id = ?",
            (status, _utcnow(), json.dumps(summary, ensure_ascii=False), run_id),
        )
        self._conn.commit()

    def delete_run(self, run_id: int) -> None:
        self._conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        self._conn.commit()

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        import json

        row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        logs = self._conn.execute(
            "SELECT ts, level, message FROM run_logs WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return {
            "id": row["id"],
            "kind": row["kind"],
            "params": json.loads(row["params_json"]),
            "dry_run": bool(row["dry_run"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "finished_at": row["finished_at"],
            "summary": json.loads(row["summary_json"]),
            "logs": [dict(log) for log in logs],
        }

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        import json

        rows = self._conn.execute(
            "SELECT id, kind, params_json, dry_run, status, created_at, finished_at, "
            "summary_json FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "params": json.loads(row["params_json"]),
                "dry_run": bool(row["dry_run"]),
                "status": row["status"],
                "created_at": row["created_at"],
                "finished_at": row["finished_at"],
                "summary": json.loads(row["summary_json"]),
            }
            for row in rows
        ]


def seed_from_settings(db: Database, settings: Any) -> dict[str, int]:
    """First-run migration: .env IMAP account into SQLite.

    Idempotent: only seeds when the accounts table is currently empty.
    Contacts and installations are managed via the web UI.
    """
    seeded = {"email_accounts": 0}
    if not db.list_email_accounts() and getattr(settings, "imap_user", ""):
        db.add_email_account(
            label="Principal",
            host=settings.imap_host,
            username=settings.imap_user,
            password=settings.imap_pass,
        )
        seeded["email_accounts"] += 1
    return seeded
