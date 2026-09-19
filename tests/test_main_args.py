from datetime import date
from types import SimpleNamespace

import voltbot.main as main_module
from voltbot.main import (
    month_bounds,
    parse_args,
    resolve_interval_seconds,
    resolve_target_day,
)


def test_parse_args_defaults_to_today_and_loop():
    args = parse_args([])
    assert args.date is None
    assert args.once is False
    assert args.interval_seconds is None
    assert args.dry_run is False
    assert args.month is None
    assert resolve_target_day(args.date) == date.today()


def test_parse_args_accepts_custom_date():
    args = parse_args(["--date", "2026-09-18"])
    assert args.date == date(2026, 9, 18)
    assert resolve_target_day(args.date) == date(2026, 9, 18)


def test_parse_args_once_and_interval():
    assert parse_args(["--once"]).once is True
    assert parse_args(["--interval-seconds", "60"]).interval_seconds == 60
    assert resolve_interval_seconds(60) == 60
    assert resolve_interval_seconds(0) == 0


def test_parse_args_dry_run_and_month():
    assert parse_args(["--dry-run"]).dry_run is True
    assert parse_args(["--month", "2026-09"]).month == (2026, 9)


def test_parse_args_barcode_only_defaults_to_false():
    assert parse_args([]).barcode_only is False
    assert parse_args(["--barcode-only"]).barcode_only is True
    assert parse_args([]).barcode_all is False
    assert parse_args(["--barcode-only", "--barcode-all"]).barcode_all is True


def _fake_msg(body_extra="", *, installation="0200420281", pdf_name="conta.pdf", barcode="1" * 48):
    from datetime import datetime

    att = SimpleNamespace(filename=pdf_name, content_type="application/pdf", payload=b"%PDF")
    text = f"INSTALAÇÃO/UC: {installation}"
    if barcode:
        text += f" Código de barras: {barcode}"
    text += body_extra
    return SimpleNamespace(
        text=text,
        html="",
        subject="Enel - Conta por email",
        date=datetime(2026, 9, 19, 10, 0, 0),
        attachments=[att],
    )


def test_collect_barcode_catchup_only_resends_processed_with_barcode(monkeypatch):
    from voltbot.domain import WhatsAppContact
    from voltbot.main import collect_barcode_catchup

    contact = WhatsAppContact(installation="0200420281", phone="11999999999", name="Bia")
    monkeypatch.setattr(
        main_module, "already_processed", lambda installation, pdf_name: pdf_name == "enviada.pdf"
    )
    monkeypatch.setattr(
        main_module, "load_contacts_for_installation", lambda installation: [contact]
    )

    messages = [
        _fake_msg(pdf_name="enviada.pdf", barcode="2" * 48),  # enviada hoje, com barras
        _fake_msg(pdf_name="nova.pdf", barcode="3" * 48),  # ainda nao enviada
        _fake_msg(pdf_name="enviada.pdf", barcode=None),  # enviada, mas sem barras
    ]

    deliveries, stats = collect_barcode_catchup(messages)

    assert len(deliveries) == 1
    assert deliveries[0].bill.barcode == "2" * 48
    assert deliveries[0].contacts == [contact]
    assert stats == {
        "emails": 3,
        "parsed": 3,
        "with_barcode": 2,
        "already_sent": 1,
        "with_contacts": 1,
    }


def test_collect_barcode_catchup_with_all_includes_unprocessed(monkeypatch):
    from voltbot.domain import WhatsAppContact
    from voltbot.main import collect_barcode_catchup

    contact = WhatsAppContact(installation="0200420281", phone="11999999999", name="Bia")
    monkeypatch.setattr(main_module, "already_processed", lambda installation, pdf_name: False)
    monkeypatch.setattr(
        main_module, "load_contacts_for_installation", lambda installation: [contact]
    )

    deliveries, stats = collect_barcode_catchup(
        [_fake_msg(pdf_name="nova.pdf", barcode="3" * 48)], include_unprocessed=True
    )

    assert len(deliveries) == 1
    assert stats["already_sent"] == 0
    assert stats["with_contacts"] == 1


def test_collect_barcode_catchup_skips_installation_without_contacts(monkeypatch):
    from voltbot.main import collect_barcode_catchup

    monkeypatch.setattr(main_module, "already_processed", lambda installation, pdf_name: True)
    monkeypatch.setattr(main_module, "load_contacts_for_installation", lambda installation: [])

    deliveries, stats = collect_barcode_catchup([_fake_msg()])

    assert deliveries == []
    assert stats["with_contacts"] == 0


def test_month_bounds_spans_full_month():
    assert month_bounds(2026, 9) == (date(2026, 9, 1), date(2026, 10, 1))
    assert month_bounds(2026, 12) == (date(2026, 12, 1), date(2027, 1, 1))


def test_resolve_interval_falls_back_to_settings(monkeypatch):
    monkeypatch.setattr(
        main_module, "get_settings", lambda: SimpleNamespace(poll_interval_seconds=123)
    )
    assert resolve_interval_seconds(None) == 123


def test_resolve_interval_defaults_when_settings_fail(monkeypatch):
    def _boom():
        raise ValueError("sem settings")

    monkeypatch.setattr(main_module, "get_settings", _boom)
    assert resolve_interval_seconds(None) == 3600
