from voltbot.db import Database, seed_from_settings
from types import SimpleNamespace


def test_contacts_crud(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_installation("0200420281", label="Casa")
    db.add_contact("0200420281", "551199999999", "Bia")
    db.add_contact("0200420281", "551188888888")

    rows = db.list_contacts("0200420281")
    assert len(rows) == 2
    by_phone = {row["phone"]: row for row in rows}
    assert by_phone["551199999999"]["name"] == "Bia"
    assert by_phone["551188888888"]["name"] is None

    # upsert atualiza o nome sem duplicar
    db.add_contact("0200420281", "551188888888", "Artur")
    rows = db.list_contacts("0200420281")
    assert len(rows) == 2

    installations = db.list_installations()
    assert installations[0]["code"] == "0200420281"
    assert installations[0]["contacts"] == 2

    db.delete_contact(rows[0]["id"])
    assert len(db.list_contacts("0200420281")) == 1

    db.delete_installation("0200420281")
    assert db.list_contacts("0200420281") == []
    db.close()


def test_email_accounts_crud(tmp_path):
    db = Database(tmp_path / "test.db")
    acc_id = db.add_email_account("Principal", "imap.gmail.com", "a@gmail.com", "segredo")
    db.add_email_account("Extra", "imap.outro.com", "b@outro.com", "x", enabled=False)

    assert len(db.enabled_email_accounts()) == 1
    masked = db.list_email_accounts()
    assert all("password" not in item for item in masked)

    db.set_email_account_enabled(acc_id, False)
    assert db.enabled_email_accounts() == []

    db.set_email_account_enabled(acc_id, True)
    db.delete_email_account(acc_id)
    assert len(db.list_email_accounts()) == 1
    db.close()


def test_seed_imports_settings_account_once(tmp_path):
    settings = SimpleNamespace(imap_host="imap.gmail.com", imap_user="a@gmail.com", imap_pass="segredo")
    db = Database(tmp_path / "test.db")
    first = seed_from_settings(db, settings)
    assert first == {"email_accounts": 1}
    assert len(db.enabled_email_accounts()) == 1
    second = seed_from_settings(db, settings)
    assert second == {"email_accounts": 0}
    db.close()


def test_runs_lifecycle(tmp_path):
    db = Database(tmp_path / "test.db")
    run_id = db.create_run("today", {"date": "2026-09-19"}, dry_run=True)
    db.log(run_id, "INFO", "inicio")
    db.log(run_id, "INFO", "fim")
    db.finish_run(run_id, "done", {"deliveries": 1})

    run = db.get_run(run_id)
    assert run["status"] == "done"
    assert run["dry_run"] is True
    assert run["summary"] == {"deliveries": 1}
    assert [log["message"] for log in run["logs"]] == ["inicio", "fim"]

    listed = db.list_runs()
    assert len(listed) == 1 and listed[0]["id"] == run_id
    db.close()
