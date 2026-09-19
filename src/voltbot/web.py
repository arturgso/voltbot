from __future__ import annotations

import argparse
import io
import sqlite3
import threading
import traceback
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from voltbot.config import get_settings
from voltbot.db import Database, seed_from_settings
from voltbot.evolution import EvolutionError
from voltbot.main import parse_month, run_cycle

STATIC_DIR = Path(__file__).parent / "static"


class RunRequest(BaseModel):
    mode: Literal["today", "date", "month"] = "today"
    date: str | None = Field(default=None, description="AAAA-MM-DD para mode=date")
    month: str | None = Field(default=None, description="AAAA-MM para mode=month")
    dry_run: bool = False


class InstallationCreate(BaseModel):
    code: str
    label: str | None = None


class ContactCreate(BaseModel):
    installation: str
    phone: str
    name: str | None = None


class ContactUpdate(BaseModel):
    phone: str | None = None
    name: str | None = None


class EmailAccountCreate(BaseModel):
    label: str
    host: str = "imap.gmail.com"
    username: str
    password: str
    enabled: bool = True


class EmailAccountToggle(BaseModel):
    enabled: bool


def _db(request_db_path: str | None = None) -> Database:
    settings = get_settings()
    db = Database(request_db_path or settings.db_path)
    seed_from_settings(db, settings)
    return db


def _execute_run(db_path: str, run_id: int, payload: dict) -> None:
    """Background job: runs a cycle, persisting prints + summary in SQLite."""
    db = Database(db_path)
    buffer = io.StringIO()

    def flush_buffer(level: str = "INFO") -> None:
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for line in text.splitlines():
            if line.strip():
                db.log(run_id, level, line)

    try:
        db.log(run_id, "INFO", f"início: modo={payload.get('mode')} dry_run={payload.get('dry_run')}")
        with redirect_stdout(buffer):
            if payload.get("mode") == "month":
                year, month = parse_month(payload["month"])
                summary = run_cycle(month=(year, month), dry_run=payload.get("dry_run", False))
            else:
                target = (
                    date.fromisoformat(payload["date"])
                    if payload.get("mode") == "date" and payload.get("date")
                    else date.today()
                )
                summary = run_cycle(target, dry_run=payload.get("dry_run", False))
        flush_buffer()
        db.finish_run(run_id, "done", summary)
    except EvolutionError as exc:
        flush_buffer()
        db.log(run_id, "ERROR", f"Falha na Evolution API: {exc}")
        db.finish_run(run_id, "error", {"error": str(exc)})
    except Exception as exc:
        flush_buffer()
        db.log(run_id, "ERROR", f"Erro inesperado: {exc}")
        db.log(run_id, "ERROR", traceback.format_exc())
        db.finish_run(run_id, "error", {"error": str(exc)})
    finally:
        db.close()


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="VoltBot")
    app.state.db_path = db_path or get_settings().db_path

    # Seed at startup so the UI already shows migrated data.
    db = Database(app.state.db_path)
    try:
        seed_from_settings(db, get_settings())
    finally:
        db.close()

    @app.get("/api/status")
    def status() -> dict:
        settings = get_settings()
        database = _db(app.state.db_path)
        try:
            runs = database.list_runs(limit=1)
            installations = database.list_installations()
            contacts = database.list_contacts()
            accounts = database.list_email_accounts()
        finally:
            database.close()
        return {
            "evolution_configured": bool(settings.evolution_api_key and settings.evolution_instance),
            "evolution_instance": settings.evolution_instance,
            "poll_interval_seconds": settings.poll_interval_seconds,
            "email_accounts": len(accounts),
            "email_accounts_enabled": sum(1 for acc in accounts if acc["enabled"]),
            "installations": len(installations),
            "contacts": len(contacts),
            "last_run": runs[0] if runs else None,
        }

    @app.get("/api/installations")
    def list_installations() -> list[dict]:
        database = _db(app.state.db_path)
        try:
            return database.list_installations()
        finally:
            database.close()

    @app.post("/api/installations", status_code=201)
    def create_installation(payload: InstallationCreate) -> dict:
        code = payload.code.strip().replace(" ", "")
        if not code:
            raise HTTPException(status_code=422, detail="Código da instalação é obrigatório")
        database = _db(app.state.db_path)
        try:
            database.upsert_installation(code, (payload.label or "").strip() or None)
            return {"code": code, "label": payload.label}
        finally:
            database.close()

    @app.delete("/api/installations/{code}", status_code=204)
    def delete_installation(code: str) -> None:
        database = _db(app.state.db_path)
        try:
            database.delete_installation(code)
        finally:
            database.close()

    @app.get("/api/contacts")
    def list_contacts(installation: str | None = None) -> list[dict]:
        database = _db(app.state.db_path)
        try:
            return database.list_contacts(installation)
        finally:
            database.close()

    @app.post("/api/contacts", status_code=201)
    def create_contact(payload: ContactCreate) -> dict:
        digits = "".join(ch for ch in payload.phone if ch.isdigit())
        if len(digits) < 10:
            raise HTTPException(status_code=422, detail="Telefone inválido (mínimo 10 dígitos)")
        database = _db(app.state.db_path)
        try:
            contact_id = database.add_contact(payload.installation, digits, payload.name)
            return {"id": contact_id}
        finally:
            database.close()

    @app.delete("/api/contacts/{contact_id}", status_code=204)
    def delete_contact(contact_id: int) -> None:
        database = _db(app.state.db_path)
        try:
            database.delete_contact(contact_id)
        finally:
            database.close()

    @app.patch("/api/contacts/{contact_id}")
    def update_contact(contact_id: int, payload: ContactUpdate) -> dict:
        digits = None
        if payload.phone is not None:
            digits = "".join(ch for ch in payload.phone if ch.isdigit())
            if len(digits) < 10:
                raise HTTPException(status_code=422, detail="Telefone inválido (mínimo 10 dígitos)")
        database = _db(app.state.db_path)
        try:
            try:
                updated = database.update_contact(contact_id, digits, payload.name)
            except sqlite3.IntegrityError as exc:
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um contato com esse número nesta instalação",
                ) from exc
        finally:
            database.close()
        if not updated:
            raise HTTPException(status_code=404, detail="Contato não encontrado")
        return updated

    @app.get("/api/accounts")
    def list_accounts() -> list[dict]:
        database = _db(app.state.db_path)
        try:
            return database.list_email_accounts()
        finally:
            database.close()

    @app.post("/api/accounts", status_code=201)
    def create_account(payload: EmailAccountCreate) -> dict:
        if not payload.username.strip() or not payload.password:
            raise HTTPException(status_code=422, detail="Usuário e senha são obrigatórios")
        database = _db(app.state.db_path)
        try:
            account_id = database.add_email_account(
                payload.label, payload.host, payload.username, payload.password,
                enabled=payload.enabled,
            )
            return {"id": account_id}
        finally:
            database.close()

    @app.patch("/api/accounts/{account_id}")
    def toggle_account(account_id: int, payload: EmailAccountToggle) -> dict:
        database = _db(app.state.db_path)
        try:
            database.set_email_account_enabled(account_id, payload.enabled)
            return {"id": account_id, "enabled": payload.enabled}
        finally:
            database.close()

    @app.delete("/api/accounts/{account_id}", status_code=204)
    def delete_account(account_id: int) -> None:
        database = _db(app.state.db_path)
        try:
            database.delete_email_account(account_id)
        finally:
            database.close()

    @app.post("/api/runs", status_code=202)
    def start_run(payload: RunRequest) -> dict:
        params = payload.model_dump()
        if payload.mode == "date":
            if not payload.date:
                raise HTTPException(status_code=422, detail="Informe date (AAAA-MM-DD)")
            try:
                date.fromisoformat(payload.date)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Data inválida, use AAAA-MM-DD") from exc
        if payload.mode == "month":
            if not payload.month:
                raise HTTPException(status_code=422, detail="Informe month (AAAA-MM)")
            try:
                parse_month(payload.month)
            except Exception as exc:
                raise HTTPException(status_code=422, detail="Mês inválido, use AAAA-MM") from exc
        database = _db(app.state.db_path)
        try:
            run_id = database.create_run(payload.mode, params, payload.dry_run)
        finally:
            database.close()
        thread = threading.Thread(
            target=_execute_run, args=(app.state.db_path, run_id, params), daemon=True
        )
        thread.start()
        return {"id": run_id}

    @app.get("/api/runs")
    def list_runs(limit: int = 20) -> list[dict]:
        database = _db(app.state.db_path)
        try:
            return database.list_runs(limit=min(limit, 100))
        finally:
            database.close()

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: int) -> dict:
        database = _db(app.state.db_path)
        try:
            run = database.get_run(run_id)
        finally:
            database.close()
        if not run:
            raise HTTPException(status_code=404, detail="Execução não encontrada")
        return run

    @app.delete("/api/runs/{run_id}", status_code=204)
    def delete_run(run_id: int) -> None:
        database = _db(app.state.db_path)
        try:
            if not database.get_run(run_id):
                raise HTTPException(status_code=404, detail="Execução não encontrada")
            database.delete_run(run_id)
        finally:
            database.close()

    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app


def serve() -> None:
    parser = argparse.ArgumentParser(description="Serve a interface web do VoltBot.")
    parser.add_argument("--host", default=None, help="Host (padrão: WEB_HOST ou 127.0.0.1).")
    parser.add_argument("--port", type=int, default=None, help="Porta (padrão: WEB_PORT ou 8000).")
    cli = parser.parse_args()
    settings = get_settings()
    import uvicorn

    uvicorn.run(
        create_app(),
        host=cli.host or settings.web_host,
        port=cli.port or settings.web_port,
        log_level="info",
    )


if __name__ == "__main__":
    serve()
