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

    def fake_run_cycle(target_day=None, *, month=None, dry_run=False, barcode_only=False):
        calls.append((target_day, month, dry_run, barcode_only))
        print("ciclo fake executado")
        return {"deliveries": 1, "messages": 2, "dry_run": dry_run}

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
    assert calls and calls[0][2] is True
    assert calls[0][3] is False

    listed = client.get("/api/runs").json()
    assert listed[0]["id"] == run_id

    assert client.delete(f"/api/runs/{run_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404
    assert client.get("/api/runs").json() == []


def test_run_forwards_barcode_only_flag(client, monkeypatch):
    calls = []

    def fake_run_cycle(target_day=None, *, month=None, dry_run=False, barcode_only=False):
        calls.append((target_day, month, dry_run, barcode_only))
        return {"deliveries": 1, "messages": 1, "dry_run": dry_run, "barcode_only": barcode_only}

    monkeypatch.setattr(web_module, "run_cycle", fake_run_cycle)

    res = client.post("/api/runs", json={"mode": "today", "barcode_only": True})
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
    assert calls and calls[0][3] is True


def test_index_serves_frontend(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "VoltBot" in res.text
