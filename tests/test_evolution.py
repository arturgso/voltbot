import json
from pathlib import Path
from urllib.request import Request

from datetime import date

from voltbot.domain import EnelBill, PendingDelivery, WhatsAppContact
from voltbot.evolution import (
    EvolutionClient,
    EvolutionSendResult,
    build_combined_message,
    build_delivery_message,
    build_intro_message,
    group_deliveries_by_contact,
    normalize_phone,
    send_pending_deliveries,
)
from voltbot.state import is_intro_sent, mark_intro_sent


class FakeResponse:
    status = 200

    def read(self) -> bytes:
        return b'{"ok": true}'


class FakeOpener:
    def __init__(self) -> None:
        self.requests: list[Request] = []
        self.payloads: list[dict[str, object]] = []
        self.timeouts: list[float] = []

    def __call__(self, request: Request, *, timeout: float) -> FakeResponse:
        self.requests.append(request)
        self.payloads.append(json.loads(request.data.decode("utf-8")))
        self.timeouts.append(timeout)
        return FakeResponse()


def test_normalize_phone_adds_brazil_prefix_to_local_number():
    assert normalize_phone("11934720814") == "5511934720814"


def test_build_delivery_message_has_bill_context():
    delivery = PendingDelivery(
        bill=EnelBill(
            installation="0200420281",
            subject="Enel - Conta por email",
            date=date(2026, 9, 18),
            pdf_name="conta.pdf",
            pdf_bytes=b"pdf",
            pdf_path="downloads/conta.pdf",
        ),
        contacts=[],
    )

    message = build_delivery_message(delivery, "Artur")

    assert "Olá, Artur!" in message
    assert "VoltBot" in message
    assert "Instalacao: 0200420281" in message
    assert "Data: 18/09/2026" in message
    assert "conta.pdf" not in message


def test_build_delivery_message_includes_installation_label():
    contact = WhatsAppContact(
        installation="0200420281", phone="551199999999", name="Bia",
        installation_label="Casa",
    )
    delivery = PendingDelivery(
        bill=EnelBill(
            installation="0200420281",
            subject="Enel - Conta por email",
            date=date(2026, 9, 18),
            pdf_name="conta.pdf",
            pdf_bytes=b"pdf",
            pdf_path="downloads/conta.pdf",
        ),
        contacts=[contact],
    )

    assert "Instalacao: 0200420281 (Casa)" in build_delivery_message(delivery, "Bia")
    assert "(Casa)" in build_delivery_message(delivery, "Bia", "Casa")


def test_build_intro_message_has_friendly_text_and_credits():
    msg_with_name = build_intro_message("Bia")
    assert "Olá, Bia!" in msg_with_name
    assert "Bia" in msg_with_name
    assert "Artur" in msg_with_name
    assert "Enel" in msg_with_name
    assert "WhatsApp" in msg_with_name
    assert "VoltBot" in msg_with_name
    assert "API" not in msg_with_name
    assert "Python" not in msg_with_name

    msg_without_name = build_intro_message(None)
    assert "Olá! Aqui é o VoltBot" in msg_without_name
    assert "Bia" in msg_without_name
    assert "Artur" in msg_without_name


def test_send_pending_deliveries_without_contacts_does_not_require_client():
    assert send_pending_deliveries([]) == []


def test_send_pending_deliveries_sends_intro_on_first_contact(
    monkeypatch, tmp_path: Path
):
    marked = []
    pdf = tmp_path / "conta.pdf"
    pdf.write_bytes(b"pdf")
    state_file = tmp_path / "state.json"
    delivery = PendingDelivery(
        bill=EnelBill(
            installation="0200420281",
            subject="Enel - Conta por email",
            date=date(2026, 9, 18),
            pdf_name="conta.pdf",
            pdf_bytes=b"pdf",
            pdf_path=str(pdf),
        ),
        contacts=[
            WhatsAppContact(
                installation="0200420281",
                phone="11934720814",
                name="Contato",
            )
        ],
    )

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str | None]] = []

        def send_text(self, number: str, text: str) -> EvolutionSendResult:
            self.calls.append(("text", number, text))
            return EvolutionSendResult(number, "/text", 201, {})

        def send_pdf(
            self, number: str, pdf_path: str | Path, caption: str | None = None
        ) -> EvolutionSendResult:
            self.calls.append(("pdf", number, str(pdf_path)))
            return EvolutionSendResult(number, "/pdf", 201, {})

    client = FakeClient()
    monkeypatch.setattr(
        "voltbot.evolution.mark_processed",
        lambda installation, pdf_name, path=None: marked.append((installation, pdf_name)),
    )

    results = send_pending_deliveries([delivery], client, state_path=state_file)

    assert [call[0] for call in client.calls] == ["text", "text", "pdf"]
    assert "Bia" in client.calls[0][2]
    assert "Artur" in client.calls[0][2]
    assert "Instalacao: 0200420281" in client.calls[1][2]
    assert is_intro_sent("11934720814", path=state_file)
    assert marked == [("0200420281", "conta.pdf")]
    assert len(results) == 3


def test_send_pending_deliveries_skips_intro_when_already_sent(
    monkeypatch, tmp_path: Path
):
    marked = []
    pdf = tmp_path / "conta.pdf"
    pdf.write_bytes(b"pdf")
    state_file = tmp_path / "state.json"
    mark_intro_sent("11934720814", path=state_file)

    delivery = PendingDelivery(
        bill=EnelBill(
            installation="0200420281",
            subject="Enel - Conta por email",
            date=date(2026, 9, 18),
            pdf_name="conta.pdf",
            pdf_bytes=b"pdf",
            pdf_path=str(pdf),
        ),
        contacts=[
            WhatsAppContact(
                installation="0200420281",
                phone="11934720814",
                name="Contato",
            )
        ],
    )

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str | None]] = []

        def send_text(self, number: str, text: str) -> EvolutionSendResult:
            self.calls.append(("text", number, text))
            return EvolutionSendResult(number, "/text", 201, {})

        def send_pdf(
            self, number: str, pdf_path: str | Path, caption: str | None = None
        ) -> EvolutionSendResult:
            self.calls.append(("pdf", number, str(pdf_path)))
            return EvolutionSendResult(number, "/pdf", 201, {})

    client = FakeClient()
    monkeypatch.setattr(
        "voltbot.evolution.mark_processed",
        lambda installation, pdf_name, path=None: marked.append((installation, pdf_name)),
    )

    results = send_pending_deliveries([delivery], client, state_path=state_file)

    assert [call[0] for call in client.calls] == ["text", "pdf"]
    assert "Instalacao: 0200420281" in client.calls[0][2]
    assert marked == [("0200420281", "conta.pdf")]
    assert len(results) == 2


def test_send_text_uses_instance_endpoint_and_normalized_number():
    opener = FakeOpener()
    client = EvolutionClient(
        api_url="http://localhost:8080",
        api_key="secret",
        instance="enel-teste",
        opener=opener,
    )

    result = client.send_text("11934720814", "teste")

    assert result.status_code == 200
    assert opener.requests[0].full_url == "http://localhost:8080/message/sendText/enel-teste"
    assert opener.requests[0].headers["Apikey"] == "secret"
    assert opener.payloads[0] == {"number": "5511934720814", "text": "teste"}


def test_send_pdf_sends_document_payload_with_base64_media(tmp_path: Path):
    pdf = tmp_path / "conta.pdf"
    pdf.write_bytes(b"%PDF teste")
    opener = FakeOpener()
    client = EvolutionClient(
        api_url="http://localhost:8080",
        api_key="secret",
        instance="enel-teste",
        opener=opener,
    )

    client.send_pdf("5511998550758", pdf, "Conta Enel")

    assert opener.requests[0].full_url == "http://localhost:8080/message/sendMedia/enel-teste"
    assert opener.payloads[0] == {
        "number": "5511998550758",
        "mediatype": "document",
        "mimetype": "application/pdf",
        "media": "JVBERiB0ZXN0ZQ==",
        "fileName": "conta.pdf",
        "caption": "Conta Enel",
    }


def _bill(installation: str, pdf_name: str, pdf_path: str) -> EnelBill:
    return EnelBill(
        installation=installation,
        subject="Enel - Conta por email",
        date=date(2026, 9, 18),
        pdf_name=pdf_name,
        pdf_bytes=b"pdf",
        pdf_path=pdf_path,
    )


def test_build_combined_message_lists_all_installations_with_labels():
    deliveries = [
        PendingDelivery(bill=_bill("0200420281", "casa.pdf", "x"), contacts=[]),
        PendingDelivery(bill=_bill("0300530392", "sitio.pdf", "x"), contacts=[]),
    ]
    message = build_combined_message(
        [(deliveries[0], "Casa"), (deliveries[1], "Sítio")], "Bia"
    )

    assert "Olá, Bia!" in message
    assert "VoltBot" in message
    assert "2 contas" in message
    assert "Instalacao: 0200420281 (Casa)" in message
    assert "Instalacao: 0300530392 (Sítio)" in message
    assert "casa.pdf" not in message and "sitio.pdf" not in message


def test_group_deliveries_by_contact_merges_shared_phone(tmp_path: Path):
    state_file = tmp_path / "state.json"
    shared = WhatsAppContact(
        installation="0200420281", phone="11934720814", name="Bia",
        installation_label="Casa",
    )
    other = WhatsAppContact(
        installation="0300530392", phone="5511934720814", name="Bia",
        installation_label="Sítio",
    )
    deliveries = [
        PendingDelivery(bill=_bill("0200420281", "a.pdf", "x"), contacts=[shared]),
        PendingDelivery(bill=_bill("0300530392", "b.pdf", "x"), contacts=[other]),
        PendingDelivery(bill=_bill("0400640403", "c.pdf", "x"), contacts=[]),
    ]

    groups = group_deliveries_by_contact(deliveries, state_path=state_file)

    # mesmos dígitos com e sem 55 caem no mesmo grupo; sem contatos é ignorado
    assert len(groups) == 1
    assert groups[0].phone == "11934720814"
    assert groups[0].name == "Bia"
    assert groups[0].needs_intro is True
    assert [delivery.bill.pdf_name for delivery, _ in groups[0].items] == ["a.pdf", "b.pdf"]


def test_send_shared_contact_gets_single_plural_text_and_both_pdfs(
    monkeypatch, tmp_path: Path
):
    marked = []
    pdf_a = tmp_path / "a.pdf"
    pdf_a.write_bytes(b"pdf")
    pdf_b = tmp_path / "b.pdf"
    pdf_b.write_bytes(b"pdf")
    state_file = tmp_path / "state.json"
    shared_a = WhatsAppContact(
        installation="0200420281", phone="11934720814", name="Bia",
        installation_label="Casa",
    )
    shared_b = WhatsAppContact(
        installation="0300530392", phone="5511934720814", name="Bia",
        installation_label="Sítio",
    )
    deliveries = [
        PendingDelivery(bill=_bill("0200420281", "a.pdf", str(pdf_a)), contacts=[shared_a]),
        PendingDelivery(bill=_bill("0300530392", "b.pdf", str(pdf_b)), contacts=[shared_b]),
    ]

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str | None]] = []

        def send_text(self, number: str, text: str) -> EvolutionSendResult:
            self.calls.append(("text", number, text))
            return EvolutionSendResult(number, "/text", 201, {})

        def send_pdf(
            self, number: str, pdf_path: str | Path, caption: str | None = None
        ) -> EvolutionSendResult:
            self.calls.append(("pdf", number, str(pdf_path)))
            return EvolutionSendResult(number, "/pdf", 201, {})

    client = FakeClient()
    monkeypatch.setattr(
        "voltbot.evolution.mark_processed",
        lambda installation, pdf_name, path=None: marked.append((installation, pdf_name)),
    )

    results = send_pending_deliveries(deliveries, client, state_path=state_file)

    # intro uma vez + texto único no plural + um pdf por conta
    assert [call[0] for call in client.calls] == ["text", "text", "pdf", "pdf"]
    combined = client.calls[1][2]
    assert "2 contas" in combined
    assert "Instalacao: 0200420281 (Casa)" in combined
    assert "Instalacao: 0300530392 (Sítio)" in combined
    assert is_intro_sent("5511934720814", path=state_file)
    assert marked == [("0200420281", "a.pdf"), ("0300530392", "b.pdf")]
    assert len(results) == 4
