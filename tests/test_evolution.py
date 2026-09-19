import json
from pathlib import Path
from urllib.request import Request

from datetime import date

from enel_auto.domain import EnelBill, PendingDelivery, WhatsAppContact
from enel_auto.evolution import (
    EvolutionClient,
    EvolutionSendResult,
    build_delivery_message,
    build_intro_message,
    normalize_phone,
    send_pending_deliveries,
)
from enel_auto.state import is_intro_sent, mark_intro_sent


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

    assert "Ola, Artur!" in message
    assert "Instalacao: 0200420281" in message
    assert "Data da conta: 18/09/2026" in message
    assert "Arquivo: conta.pdf" in message


def test_build_intro_message_has_friendly_text_and_credits():
    msg_with_name = build_intro_message("Bia")
    assert "Olá, Bia!" in msg_with_name
    assert "Bia" in msg_with_name
    assert "Artur" in msg_with_name
    assert "Enel" in msg_with_name
    assert "WhatsApp" in msg_with_name
    assert "API" not in msg_with_name
    assert "Python" not in msg_with_name

    msg_without_name = build_intro_message(None)
    assert "Olá! Tudo bem?" in msg_without_name
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
        "enel_auto.evolution.mark_processed",
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
        "enel_auto.evolution.mark_processed",
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
