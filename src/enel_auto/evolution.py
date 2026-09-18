from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from enel_auto.config import get_settings
from enel_auto.domain import PendingDelivery
from enel_auto.state import mark_processed


class UrlOpen(Protocol):
    def __call__(self, request: Request, *, timeout: float) -> Any: ...


class EvolutionError(RuntimeError):
    """Raised when Evolution API rejects or cannot process a request."""


@dataclass(frozen=True)
class EvolutionSendResult:
    number: str
    endpoint: str
    status_code: int
    response: Any


class EvolutionClient:
    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        instance: str | None = None,
        timeout: float = 30,
        opener: UrlOpen = urlopen,
    ) -> None:
        settings = (
            get_settings()
            if api_url is None or api_key is None or instance is None
            else None
        )
        self.api_url = (
            api_url if api_url is not None else settings.evolution_api_url
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.evolution_api_key
        self.instance = instance if instance is not None else settings.evolution_instance
        self.timeout = timeout
        self._opener = opener

        if not self.api_key:
            raise EvolutionError("EVOLUTION_API_KEY nao configurada")
        if not self.instance:
            raise EvolutionError("EVOLUTION_INSTANCE nao configurada")

    def send_text(self, number: str, text: str) -> EvolutionSendResult:
        payload = {"number": normalize_phone(number), "text": text}
        return self._post(f"/message/sendText/{quote(self.instance)}", payload)

    def send_pdf(
        self,
        number: str,
        pdf_path: str | Path,
        caption: str | None = None,
    ) -> EvolutionSendResult:
        path = Path(pdf_path)
        media = base64.b64encode(path.read_bytes()).decode("ascii")
        payload = {
            "number": normalize_phone(number),
            "mediatype": "document",
            "mimetype": "application/pdf",
            "media": media,
            "fileName": path.name,
        }
        if caption:
            payload["caption"] = caption
        return self._post(f"/message/sendMedia/{quote(self.instance)}", payload)

    def _post(self, endpoint: str, payload: dict[str, Any]) -> EvolutionSendResult:
        request = Request(
            f"{self.api_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "apikey": self.api_key,
            },
            method="POST",
        )
        try:
            response = self._opener(request, timeout=self.timeout)
            body = response.read().decode("utf-8")
            status_code = getattr(response, "status", 200)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise EvolutionError(
                f"Evolution API retornou HTTP {exc.code} em {endpoint}: {body}"
            ) from exc
        except URLError as exc:
            raise EvolutionError(f"Falha ao conectar na Evolution API: {exc}") from exc

        decoded: Any
        try:
            decoded = json.loads(body) if body else {}
        except json.JSONDecodeError:
            decoded = body

        return EvolutionSendResult(
            number=str(payload["number"]),
            endpoint=endpoint,
            status_code=status_code,
            response=decoded,
        )


def normalize_phone(number: str) -> str:
    digits = "".join(char for char in str(number) if char.isdigit())
    if len(digits) in {10, 11}:
        return f"55{digits}"
    return digits


def build_delivery_message(delivery: PendingDelivery, contact_name: str | None = None) -> str:
    greeting = f"Ola, {contact_name}!" if contact_name else "Ola!"
    bill = delivery.bill
    return (
        f"{greeting}\n"
        "Segue a conta Enel recebida por email.\n\n"
        f"Instalacao: {bill.installation}\n"
        f"Data da conta: {bill.date:%d/%m/%Y}\n"
        f"Arquivo: {bill.pdf_name}\n\n"
        "Mensagem automatica do Enel Auto."
    )


def send_pending_deliveries(
    deliveries: list[PendingDelivery],
    client: EvolutionClient | None = None,
) -> list[EvolutionSendResult]:
    deliveries_with_contacts = [
        delivery for delivery in deliveries if delivery.contacts
    ]
    if not deliveries_with_contacts:
        return []

    resolved_client = client or EvolutionClient()
    results: list[EvolutionSendResult] = []

    for delivery in deliveries_with_contacts:
        delivery_results: list[EvolutionSendResult] = []
        for contact in delivery.contacts:
            if not delivery.bill.pdf_path:
                raise EvolutionError(
                    f"PDF sem caminho salvo para {delivery.bill.installation}"
                )
            message = build_delivery_message(delivery, contact.name)
            delivery_results.append(resolved_client.send_text(contact.phone, message))
            caption = f"Conta Enel - instalacao {delivery.bill.installation}"
            delivery_results.append(
                resolved_client.send_pdf(contact.phone, delivery.bill.pdf_path, caption)
            )

        mark_processed(delivery.bill.installation, delivery.bill.pdf_name)
        results.extend(delivery_results)

    return results
