from datetime import date

from enel_auto.main import parse_args


def test_parse_args_defaults_to_fixed_date():
    args = parse_args([])
    assert args.date == date(2026, 9, 13)


def test_parse_args_accepts_custom_date():
    args = parse_args(["--date", "2026-09-18"])
    assert args.date == date(2026, 9, 18)
