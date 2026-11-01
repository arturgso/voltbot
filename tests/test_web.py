import time

import pytest
from fastapi.testclient import TestClient

import voltbot.web as web_module
from voltbot.web import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(web_module, "seed_from_settings", lambda db, settings: {})
    app = create_app(str(tmp_path / "web.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_health_returns_ok(client):
    for path in ("/health", "/api/health"):
        res = client.get(path)
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


def test_installation_pdf_password_create_update_preserve_and_clear(client):
    payload = {"code": "0000123", "label": "Casa", "pdf_password": "001234"}
    assert client.post("/api/installations", json=payload).json()["pdf_password"] == "001234"
    client.post("/api/contacts", json={"installation": "0000123", "phone": "5511999999999"})
    client.post("/api/installations", json={"code": "0000123", "label": "Casa nova"})
    assert client.get("/api/installations").json()[0]["pdf_password"] == "001234"
    payload["pdf_password"] = "000567"
    client.post("/api/installations", json=payload)
    assert client.get("/api/installations").json()[0]["pdf_password"] == "000567"
    for value in (None, ""):
        client.post("/api/installations", json={**payload, "pdf_password": value})
        assert client.get("/api/installations").json()[0]["pdf_password"] is None
    assert len(client.get("/api/contacts").json()) == 1


def test_status_shape(client):
    data = client.get("/api/status").json()
    assert set(data) >= {
        "evolution_configured", "email_accounts", "installations",
        "contacts", "last_run", "poll_interval_seconds",
    }


def test_installations_and_contacts_crud(client):
    assert client.get("/api/installations").json() == []

    res = client.post("/api/installations", json={"code": "0200420281", "label": "Casa"})
    assert res.status_code == 201

    res = client.post(
        "/api/contacts",
        json={"installation": "0200420281", "phone": "(11) 99999-9999", "name": "Bia"},
    )
    assert res.status_code == 201

    contacts = client.get("/api/contacts").json()
    assert len(contacts) == 1
    assert contacts[0]["phone"] == "11999999999"
    assert contacts[0]["installation_label"] == "Casa"

    res = client.post("/api/contacts", json={"installation": "0200420281", "phone": "abc"})
    assert res.status_code == 422

    contact_id = contacts[0]["id"]
    assert client.delete(f"/api/contacts/{contact_id}").status_code == 204
    assert client.get("/api/contacts").json() == []

    assert client.delete("/api/installations/0200420281").status_code == 204
    assert client.get("/api/installations").json() == []


def test_update_contact_phone_and_name(client):
    client.post("/api/installations", json={"code": "0200420281", "label": "Casa"})
    first = client.post(
        "/api/contacts", json={"installation": "0200420281", "phone": "551199999999", "name": "Bia"}
    ).json()["id"]
    second = client.post(
        "/api/contacts", json={"installation": "0200420281", "phone": "551188888888"}
    ).json()["id"]

    res = client.patch(f"/api/contacts/{first}", json={"phone": "(11) 97777-7777", "name": "Beatriz"})
    assert res.status_code == 200
    assert res.json()["phone"] == "11977777777"
    assert res.json()["name"] == "Beatriz"
    assert res.json()["installation_label"] == "Casa"

    # nome pode ser limpo sem tocar no telefone
    res = client.patch(f"/api/contacts/{first}", json={"name": "  "})
    assert res.json()["name"] is None
    assert res.json()["phone"] == "11977777777"

    assert client.patch(f"/api/contacts/{first}", json={"phone": "123"}).status_code == 422
    assert client.patch(f"/api/contacts/{first}", json={"phone": "551188888888"}).status_code == 409
    assert client.patch("/api/contacts/999", json={"phone": "551199999999"}).status_code == 404


def test_accounts_crud_masks_password(client):
    res = client.post(
        "/api/accounts",
        json={"label": "Teste", "host": "imap.test.com", "username": "a@test.com", "password": "segredo"},
    )
    assert res.status_code == 201
    account_id = res.json()["id"]

    accounts = client.get("/api/accounts").json()
    assert len(accounts) == 1
    assert "password" not in accounts[0]
    assert accounts[0]["enabled"] is True

    res = client.patch(f"/api/accounts/{account_id}", json={"enabled": False})
    assert res.json()["enabled"] is False

    assert client.delete(f"/api/accounts/{account_id}").status_code == 204
    assert client.get("/api/accounts").json() == []


def test_run_validation(client):
    assert client.post("/api/runs", json={"mode": "date"}).status_code == 422
    assert client.post("/api/runs", json={"mode": "date", "date": "hoje"}).status_code == 422
    assert client.post("/api/runs", json={"mode": "month"}).status_code == 422
    assert client.get("/api/runs/999").status_code == 404
    assert client.delete("/api/runs/999").status_code == 404


def test_run_executes_in_background_with_dry_run(client, monkeypatch):
    calls = []

    def fake_run_cycle(target_day=None, **kwargs):
        calls.append((target_day, kwargs))
        print("ciclo fake executado")
        return {"deliveries": 1, "messages": 2, "dry_run": kwargs.get("dry_run", False)}

    monkeypatch.setattr(web_module, "run_cycle", fake_run_cycle)

    res = client.post("/api/runs", json={"mode": "today", "dry_run": True})
    assert res.status_code == 202
    run_id = res.json()["id"]

    deadline = time.time() + 10
    while time.time() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] != "running":
            break
        time.sleep(0.1)

    assert run["status"] == "done"
    assert run["summary"]["messages"] == 2
    assert any("ciclo fake" in log["message"] for log in run["logs"])
    assert calls and calls[0][1].get("dry_run") is True
    assert calls[0][1].get("barcode_only") is False

    listed = client.get("/api/runs").json()
    assert listed[0]["id"] == run_id

    assert client.delete(f"/api/runs/{run_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404
    assert client.get("/api/runs").json() == []


def test_run_forwards_barcode_only_flag(client, monkeypatch):
    calls = []

    def fake_run_cycle(target_day=None, **kwargs):
        calls.append((target_day, kwargs))
        return {
            "deliveries": 1,
            "messages": 1,
            "dry_run": kwargs.get("dry_run", False),
            "barcode_only": kwargs.get("barcode_only", False),
            "barcode_all": kwargs.get("barcode_all", False),
        }

    monkeypatch.setattr(web_module, "run_cycle", fake_run_cycle)

    res = client.post(
        "/api/runs",
        json={"mode": "today", "barcode_only": True, "barcode_all": True},
    )
    assert res.status_code == 202
    run_id = res.json()["id"]

    deadline = time.time() + 10
    while time.time() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] != "running":
            break
        time.sleep(0.1)

    assert run["status"] == "done"
    assert run["summary"]["barcode_only"] is True
    assert run["summary"]["barcode_all"] is True
    assert calls and calls[0][1].get("barcode_only") is True
    assert calls[0][1].get("barcode_all") is True


def test_index_serves_frontend(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "VoltBot" in res.text


def test_email_failure_has_actionable_log_without_traceback(client, monkeypatch):
    from voltbot.imap_client import EmailAccountError

    def fail(*args, **kwargs):
        print('Consultando conta de e-mail “Principal”...')
        raise EmailAccountError('Login recusado na conta Principal. Confira a senha em E-mails.')

    monkeypatch.setattr(web_module, 'run_cycle', fail)
    response = client.post('/api/runs', json={'mode': 'today', 'dry_run': True})
    run_id = response.json()['id']
    deadline = time.time() + 10
    while time.time() < deadline:
        run = client.get(f'/api/runs/{run_id}').json()
        if run['status'] != 'running':
            break
        time.sleep(0.1)
    assert run['status'] == 'error'
    logs = '\n'.join(log['message'] for log in run['logs'])
    assert 'Simulação iniciada' in logs
    assert 'Nenhuma mensagem será enviada' in logs
    assert 'Consultando conta' in logs
    assert 'Login recusado' in logs
    assert 'Traceback' not in logs
    assert 'Erro inesperado' not in logs


def test_manual_run_preserves_next_schedule(client, monkeypatch):
    monkeypatch.setattr(web_module, 'run_cycle', lambda *args, **kwargs: {})
    before = client.get('/api/status').json()['schedule']
    assert before['active'] is True
    client.post('/api/runs', json={'mode': 'today', 'dry_run': True})
    after = client.get('/api/status').json()['schedule']
    assert after['next_run_at'] == before['next_run_at']


def test_scheduled_run_uses_date_range_and_sends(tmp_path, monkeypatch):
    from voltbot.db import Database
    calls = []
    monkeypatch.setattr(web_module, 'run_cycle', lambda **kwargs: calls.append(kwargs) or {})
    db = Database(tmp_path / 'scheduled.db')
    params = {'mode': 'week', 'start': '2026-10-30', 'end': '2026-11-07', 'scheduled': True, 'dry_run': False}
    run_id = db.create_run('week', params, False)
    web_module._execute_run(str(db.path), run_id, params)
    from datetime import date
    assert calls == [{'date_range': (date(2026, 10, 30), date(2026, 11, 7))}]
    assert db.get_run(run_id)['status'] == 'done'
    db.close()
