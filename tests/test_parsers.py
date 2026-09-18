from enel_auto.parsers import extract_installation_from_body


def test_extract_installation_from_body_with_uc_marker():
    body = "\nOlá,\nA sua instalação é: INSTALAÇÃO/UC: 0200420281\n"

    assert extract_installation_from_body(body) == "0200420281"
