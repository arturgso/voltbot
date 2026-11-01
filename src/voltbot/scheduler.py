"""Weekly scheduling persisted separately from the user-visible run history."""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import date, timedelta
from typing import Callable

from voltbot.db import Database

WEEK_SECONDS = 7 * 24 * 60 * 60
# Manual and scheduled web jobs share this lock, including stdout capture/state writes.
RUN_LOCK = threading.Lock()


def next_run_at(db: Database, now: float) -> float:
    db._conn.execute(
        "INSERT OR IGNORE INTO schedule (id, next_run_at) VALUES (1, ?)",
        (now + WEEK_SECONDS,),
    )
    db._conn.commit()
    return db._conn.execute("SELECT next_run_at FROM schedule WHERE id = 1").fetchone()[0]


def claim_due_run(db: Database, now: float) -> tuple[int, dict] | None:
    """Claim one due execution atomically; skip missed slots without a send burst."""
    next_run_at(db, now)
    db._conn.execute("BEGIN IMMEDIATE")
    try:
        due = db._conn.execute("SELECT next_run_at FROM schedule WHERE id = 1").fetchone()[0]
        if due > now:
            db._conn.rollback()
            return None
        following = due + (int((now - due) // WEEK_SECONDS) + 1) * WEEK_SECONDS
        end = date.today() + timedelta(days=1)
        params = {"mode": "week", "start": (end - timedelta(days=8)).isoformat(),
                  "end": end.isoformat(), "scheduled": True, "dry_run": False}
        cursor = db._conn.execute(
            "INSERT INTO runs (kind, params_json, dry_run, status, created_at) VALUES (?, ?, 0, 'running', ?)",
            ("week", json.dumps(params), date_time_now()),
        )
        db._conn.execute("UPDATE schedule SET next_run_at = ? WHERE id = 1", (following,))
        db._conn.commit()
        return cursor.lastrowid, params
    except Exception:
        db._conn.rollback()
        raise


def date_time_now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def scheduler_loop(db_path: str, stop: threading.Event, execute: Callable) -> None:
    while not stop.is_set():
        try:
            # Wait for manual runs to finish before claiming the scheduled slot.
            if RUN_LOCK.acquire(blocking=False):
                try:
                    db = Database(db_path)
                    try:
                        claimed = claim_due_run(db, time.time())
                    finally:
                        db.close()
                    if claimed:
                        run_id, params = claimed
                        execute(db_path, run_id, params)
                finally:
                    RUN_LOCK.release()
        except Exception:
            logging.getLogger(__name__).exception("Falha no agendador semanal; nova tentativa em 15 segundos.")
        stop.wait(15)
