from voltbot.parsers import extract_amount_from_body, extract_installation_from_body


def test_extract_installation_from_body_with_uc_marker():
    body = "\nOlá,\nA sua instalação é: INSTALAÇÃO/UC: 0200420281\n"

    assert extract_installation_from_body(body) == "0200420281"


def test_extract_amount_from_body_with_pagar_label():
    body = "Quanto eu vou pagar?\n\nR$         142,79\n\nData de vencimento"

    assert extract_amount_from_body(body) == "142,79"


def test_extract_amount_from_body_with_valor_label_and_thousands():
    body = "Valor total a pagar R$ 1.234,56 referente ao mês"

    assert extract_amount_from_body(body) == "1.234,56"


def test_extract_amount_from_body_falls_back_to_first_reais_value():
    assert extract_amount_from_body("Sua conta: R$ 89,90.") == "89,90"


def test_extract_amount_from_body_without_value_returns_none():
    assert extract_amount_from_body("Sem valores aqui") is None
    assert extract_amount_from_body("") is None
