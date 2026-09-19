from pathlib import Path

from enel_auto.contacts import load_contacts_for_installation


def test_load_contacts_supports_name_and_nome(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
        0200420281:
          - phone: "5511998550758"
            name: "Bia"
          - telefone: "5511934720814"
            nome: "Artur"
          - "5511911111111"
        """,
        encoding="utf-8",
    )

    contacts = load_contacts_for_installation("0200420281", path=config_file)

    assert len(contacts) == 3
    assert contacts[0].phone == "5511998550758"
    assert contacts[0].name == "Bia"

    assert contacts[1].phone == "5511934720814"
    assert contacts[1].name == "Artur"

    assert contacts[2].phone == "5511911111111"
    assert contacts[2].name is None


def test_load_contacts_handles_empty_or_whitespace_name(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
        0200420281:
          - phone: "5511999999999"
            name: "   "
        """,
        encoding="utf-8",
    )

    contacts = load_contacts_for_installation("0200420281", path=config_file)
    assert len(contacts) == 1
    assert contacts[0].name is None
