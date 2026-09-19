from types import SimpleNamespace

import pytest

import voltbot.contacts as contacts_module
from voltbot.contacts import load_contacts_for_installation, normalize_installation_key
from voltbot.db import Database


@pytest.fixture()
def tmp_settings(tmp_path, monkeypatch):
    db_path = str(tmp_path / "contacts.db")
    settings = SimpleNamespace(db_path=db_path, imap_user="", imap_pass="")
    monkeypatch.setattr(contacts_module, "get_settings", lambda: settings)
    return db_path


def test_load_contacts_from_db_with_labels(tmp_settings):
    db = Database(tmp_settings)
    db.upsert_installation("0200420281", "Casa")
    db.add_contact("0200420281", "551199999999", "Bia")
    db.add_contact("0200420281", "551188888888")
    db.close()

    contacts = load_contacts_for_installation("0200420281")

    assert len(contacts) == 2
    by_phone = {contact.phone: contact for contact in contacts}
    assert by_phone["551199999999"].name == "Bia"
    assert by_phone["551199999999"].installation_label == "Casa"
    assert by_phone["551188888888"].name is None


def test_load_contacts_normalizes_installation_key(tmp_settings):
    db = Database(tmp_settings)
    db.add_contact("0200420281", "551199999999", "Bia")
    db.close()

    assert len(load_contacts_for_installation(" 0200420281 ")) == 1
    assert load_contacts_for_installation("9999999999") == []


def test_normalize_installation_key():
    assert normalize_installation_key(" 0200420281 ") == "0200420281"
