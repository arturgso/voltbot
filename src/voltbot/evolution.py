from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from voltbot.config import get_settings
from voltbot.domain import PendingDelivery, normalize_phone
from voltbot.state import is_intro_sent, mark_intro_sent, mark_processed


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


def format_installation_line(
    installation: str, installation_label: str | None, bill_date=None
) -> str:
    label = f" ({installation_label})" if (installation_label or "").strip() else ""
    line = f"Instalacao: {installation}{label}"
    if bill_date is not None:
        line += f" | Data: {bill_date:%d/%m/%Y}"
    return line


def format_barcode_block(barcode: str | None) -> str:
    """Bloco copia-e-cola do codigo de barras (somente digitos)."""
    digits = "".join(ch for ch in str(barcode or "") if ch.isdigit())
    if not digits:
        return ""
    return f"Código de barras (copia e cola):\n{digits}"


def build_intro_message(contact_name: str | None = None) -> str:
    greeting = f"Olá, {contact_name}! Aqui é o VoltBot ⚡" if contact_name else "Olá! Aqui é o VoltBot ⚡"
    return (
        f"{greeting} Tudo bem? 😊\n\n"
        "Sou eu quem vai te mandar a conta de luz da Enel aqui no WhatsApp "
        "assim que ela chegar, pra facilitar o seu dia a dia e você não "
        "precisar se preocupar!\n\n"
        "Fui criado pelo Artur com a ideia da Bia.\n\n"
        "Já estou te enviando a fatura deste mês logo abaixo! 👇"
    )


def build_delivery_message(
    delivery: PendingDelivery,
    contact_name: str | None = None,
    installation_label: str | None = None,
) -> str:
    greeting = f"Olá, {contact_name}! Aqui é o VoltBot ⚡" if contact_name else "Olá! Aqui é o VoltBot ⚡"
    bill = delivery.bill
    if installation_label is None:
        for contact in delivery.contacts:
            if contact.installation == bill.installation and contact.installation_label:
                installation_label = contact.installation_label
                break
    text = (
        f"{greeting}\n"
        "Acabei de receber a sua conta de luz da Enel por e-mail e já estou te enviando 👇\n\n"
        f"{format_installation_line(bill.installation, installation_label, bill.date)}"
    )
    barcode_block = format_barcode_block(bill.barcode)
    if barcode_block:
        text += f"\n\n{barcode_block}"
    return text


def build_combined_message(
    items: list[tuple[PendingDelivery, str | None]],
    contact_name: str | None = None,
) -> str:
    """Plural message for one contact receiving bills from several installations.

    ``items`` holds (delivery, installation_label) pairs.
    """
    greeting = f"Olá, {contact_name}! Aqui é o VoltBot ⚡" if contact_name else "Olá! Aqui é o VoltBot ⚡"
    parts: list[str] = []
    for delivery, label in items:
        parts.append(
            f"- {format_installation_line(delivery.bill.installation, label, delivery.bill.date)}"
        )
        barcode_block = format_barcode_block(delivery.bill.barcode)
        if barcode_block:
            indented = barcode_block.replace("\n", "\n  ")
            parts.append(f"  {indented}")
    listing = "\n".join(parts)
    return (
        f"{greeting}\n"
        f"Acabei de receber {len(items)} contas de luz da Enel no e-mail e já estou te enviando 👇\n\n"
        f"{listing}"
    )


@dataclass
class ContactDeliveryGroup:
    """All bills of a cycle for a single normalized phone number."""

    phone: str
    name: str | None
    items: list[tuple[PendingDelivery, str | None]]
    needs_intro: bool


def group_deliveries_by_contact(
    deliveries: list[PendingDelivery],
    state_path: str | Path | None = None,
) -> list[ContactDeliveryGroup]:
    """Group deliveries by normalized phone so shared contacts get one message.

    The intro flag is resolved per phone, keeping first-contact behavior when
    the same number appears under several installations.
    """
    grouped: dict[str, ContactDeliveryGroup] = {}
    for delivery in deliveries:
        if not delivery.contacts:
            continue
        for contact in delivery.contacts:
            key = normalize_phone(contact.phone)
            group = grouped.get(key)
            if group is None:
                group = ContactDeliveryGroup(
                    phone=contact.phone,
                    name=contact.name,
                    items=[],
                    needs_intro=not is_intro_sent(contact.phone, path=state_path),
                )
                grouped[key] = group
            if not group.name and contact.name:
                group.name = contact.name
            label = (contact.installation_label or "").strip() or None
            group.items.append((delivery, label))
    return list(grouped.values())


def send_pending_deliveries(
    deliveries: list[PendingDelivery],
    client: EvolutionClient | None = None,
    state_path: str | Path | None = None,
) -> list[EvolutionSendResult]:
    deliveries_with_contacts = [
        delivery for delivery in deliveries if delivery.contacts
    ]
    if not deliveries_with_contacts:
        return []

    resolved_client = client or EvolutionClient()
    results: list[EvolutionSendResult] = []

    for group in group_deliveries_by_contact(deliveries_with_contacts, state_path=state_path):
        for delivery, _label in group.items:
            if not delivery.bill.pdf_path:
                raise EvolutionError(
                    f"PDF sem caminho salvo para {delivery.bill.installation}"
                )
        if group.needs_intro:
            intro_message = build_intro_message(group.name)
            results.append(resolved_client.send_text(group.phone, intro_message))
            mark_intro_sent(group.phone, path=state_path)

        if len(group.items) == 1:
            delivery, label = group.items[0]
            message = build_delivery_message(delivery, group.name, label)
        else:
            message = build_combined_message(group.items, group.name)
        results.append(resolved_client.send_text(group.phone, message))

        for delivery, label in group.items:
            caption = format_installation_line(delivery.bill.installation, label)
            results.append(
                resolved_client.send_pdf(group.phone, delivery.bill.pdf_path, caption)
            )
            mark_processed(delivery.bill.installation, delivery.bill.pdf_name, path=state_path)

    return results
