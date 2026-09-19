from datetime import date
from types import SimpleNamespace

import enel_auto.main as main_module
from enel_auto.main import parse_args, resolve_interval_seconds, resolve_target_day


def test_parse_args_defaults_to_today_and_loop():
    args = parse_args([])
    assert args.date is None
    assert args.once is False
    assert args.interval_seconds is None
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
