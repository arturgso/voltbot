from __future__ import annotations

import html as html_module
import re
from datetime import date

from imap_tools import MailMessage

from voltbot.domain import EnelBill

INSTALLATION_REGEX = re.compile(r"INSTALA[ÇC][ÃA]O/UC[:\s]*(\d+)", re.IGNORECASE)

# Rotulos que costumam anteceder a linha digitavel no corpo do e-mail da Enel.
BARCODE_LABELED_REGEX = re.compile(
    r"(?:c[oó]digo\s+de\s+barras|linha\s+digit[aá]vel|c[oó]d\.?\s*barras)"
    r"[^0-9]{0,80}([0-9][0-9\s.\-]{42,90}[0-9])",
    re.IGNORECASE,
)
# Sequencias longas de digitos (com ou sem separadores) — cobre 44/47/48 digitos.
BARCODE_CANDIDATE_REGEX = re.compile(r"[0-9][0-9\s.\-]{42,90}[0-9]")
BARCODE_PLAIN_REGEX = re.compile(r"\d{44,48}")

VALID_BARCODE_LENGTHS = {44, 47, 48}

# Valor da fatura no corpo do e-mail ("Quanto eu vou pagar? R$ 142,79").
AMOUNT_LABELED_REGEX = re.compile(
    r"(?:quanto\s+(?:eu\s+)?vou\s+pagar|valor\s+(?:total\s+)?(?:a\s+pagar|da\s+(?:conta|fatura)))"
    r"[^0-9R$]{0,40}R\$\s*(\d[\d.]*,\d{2})",
    re.IGNORECASE,
)
AMOUNT_FALLBACK_REGEX = re.compile(r"R\$\s*(\d[\d.]*,\d{2})")


def strip_html(value: str) -> str:
    """Remove tags HTML e entidades para facilitar a busca por regex."""
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_barcode(raw: str) -> str:
    """Mantem somente digitos (formato copia-e-cola)."""
    return re.sub(r"\D", "", raw or "")


def extract_barcode_from_body(body: str) -> str | None:
    """Extrai a linha digitavel / codigo de barras do corpo do e-mail.

    Retorna somente digitos (44, 47 ou 48 posicoes) ou None quando ausente.
    Prioriza o trecho rotulado ("codigo de barras", "linha digitavel").
    """
    if not body:
        return None
    text = strip_html(body)

    labeled = BARCODE_LABELED_REGEX.search(text)
    if labeled:
        digits = normalize_barcode(labeled.group(1))
        if len(digits) in VALID_BARCODE_LENGTHS:
            return digits
        # Rotulado mas com tamanho inesperado: tenta aproveitar os digitos
        # contiguos dentro do trecho (ex.: quebras extras).
        for match in BARCODE_PLAIN_REGEX.finditer(digits):
            candidate = match.group(0)
            if len(candidate) in VALID_BARCODE_LENGTHS:
                return candidate
        if 40 <= len(digits) <= 60:
            return digits

    # Contiguo puro (mais confiavel): 44..48 digitos colados.
    plain_match = BARCODE_PLAIN_REGEX.search(text)
    if plain_match:
        return plain_match.group(0)

    # Formatado com espacos/pontos/tracos: avalia candidatos por tamanho.
    best: str | None = None
    for match in BARCODE_CANDIDATE_REGEX.finditer(text):
        digits = normalize_barcode(match.group(0))
        if len(digits) in VALID_BARCODE_LENGTHS:
            # Prefere 48 (arrecadacao Enel) e o primeiro encontrado.
            if best is None or (len(best) != 48 and len(digits) == 48):
                best = digits
            if best == digits and len(best) == 48:
                break
    return best


def format_barcode_for_display(barcode: str | None) -> str | None:
    """Formata 48 digitos em 4 blocos de 12 para leitura (mantem copia-e-cola)."""
    digits = normalize_barcode(barcode or "")
    if len(digits) == 48:
        return " ".join(digits[i : i + 12] for i in range(0, 48, 12))
    return digits or None


def extract_amount_from_body(body: str) -> str | None:
    """Extrai o valor da fatura (ex.: "142,79") do corpo do e-mail.

    Prioriza o trecho rotulado ("quanto vou pagar", "valor a pagar");
    sem rotulo, usa o primeiro valor em R$. Retorna None quando ausente.
    """
    if not body:
        return None
    text = strip_html(body)

    labeled = AMOUNT_LABELED_REGEX.search(text)
    if labeled:
        return labeled.group(1)
    fallback = AMOUNT_FALLBACK_REGEX.search(text)
    if fallback:
        return fallback.group(1)
    return None


def extract_installation_from_body(body: str) -> str | None:
    """Extract the installation number from the plain or HTML body text.

    The regex is kept out of imap_client.py and stays here by design.
    """
    match = INSTALLATION_REGEX.search(body or "")
    if not match:
        return None
    return match.group(1)


def extract_pdf_from_message(msg: MailMessage) -> tuple[str, bytes] | None:
    """Extract the first PDF attachment from a fetched message.

    Returns filename + payload bytes. No IMAP resolution is performed here.
    """
    for att in getattr(msg, "attachments", []):
        filename = (att.filename or "").lower()
        if filename.endswith(".pdf") or att.content_type == "application/pdf":
            return att.filename, att.payload
    return None


def parse_mail_message(msg: MailMessage) -> EnelBill | None:
    """Parse an IMAP message into an EnelBill domain object.

    This parser intentionally does not talk to IMAP; it only reads message body
    and attachment metadata already in the message object.
    """
    body = msg.text or msg.html or ""
    installation = extract_installation_from_body(body)
    if not installation:
        return None

    pdf = extract_pdf_from_message(msg)
    if not pdf:
        return None

    pdf_name, pdf_bytes = pdf
    barcode = extract_barcode_from_body(body)
    amount = extract_amount_from_body(body)
    return EnelBill(
        installation=installation,
        subject=msg.subject,
        date=msg.date.date(),
        pdf_name=pdf_name,
        pdf_bytes=pdf_bytes,
        barcode=barcode,
        amount=amount,
    )
