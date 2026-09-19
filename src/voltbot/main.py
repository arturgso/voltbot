from __future__ import annotations

import argparse
import time
import traceback
from datetime import date, datetime

from imap_tools import MailMessage

from voltbot.config import get_settings
from voltbot.contacts import load_contacts_for_installation
from voltbot.domain import EnelBill, PendingDelivery
from voltbot.evolution import (
    EvolutionError,
    build_delivery_message,
    send_pending_deliveries,
)
from voltbot.imap_client import find_day_emails, find_range_emails
from voltbot.parsers import parse_mail_message
from voltbot.state import already_processed
from voltbot.storage import save_pdf

DEFAULT_POLL_INTERVAL_SECONDS = 3600


def collect_deliveries(messages: list[MailMessage]) -> list[PendingDelivery]:
    """Turn fetched IMAP messages into domain-ready pending deliveries."""
    deliveries: list[PendingDelivery] = []

    for msg in messages:
        bill = parse_mail_message(msg)
        if bill is None:
            continue

        if already_processed(bill.installation, bill.pdf_name):
            continue

        pdf_path = save_pdf(bill)
        contacts = load_contacts_for_installation(bill.installation)
        bill_with_path = EnelBill(
            installation=bill.installation,
            subject=bill.subject,
            date=bill.date,
            pdf_name=bill.pdf_name,
            pdf_bytes=bill.pdf_bytes,
            pdf_path=pdf_path,
            barcode=bill.barcode,
            amount=bill.amount,
        )
        deliveries.append(PendingDelivery(bill=bill_with_path, contacts=contacts))

    return deliveries


def process_day(day: date | None = None) -> list[PendingDelivery]:
    """Orchestrate the IMAP fetch, parser, contacts and storage steps.

    This function returns domain-ready objects for the message-delivery layer.
    The state is marked only after a successful delivery.
    """
    resolved_day = day or date.today()
    return collect_deliveries(find_day_emails(resolved_day))


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return (first_day, first_day_of_next_month) for a YYYY-MM reference."""
    first = date(year, month, 1)
    following = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return first, following


def process_month(year: int, month: int) -> list[PendingDelivery]:
    """Fetch and prepare every Enel bill of a whole month (all accounts)."""
    start, end = month_bounds(year, month)
    return collect_deliveries(find_range_emails(start, end))


def collect_barcode_catchup(
    messages: list[MailMessage], *, include_unprocessed: bool = False
) -> tuple[list[PendingDelivery], dict]:
    """Keep bills that still need the barcode-only message.

    By default only bills already marked as sent are returned; with
    ``include_unprocessed`` every bill with barcode and contacts is kept.
    No PDF is saved and no state is touched. Returns (deliveries, stats)
    where stats breaks down each filter stage for log diagnostics.
    """
    stats = {
        "emails": len(messages),
        "parsed": 0,
        "with_barcode": 0,
        "already_sent": 0,
        "with_contacts": 0,
    }
    deliveries: list[PendingDelivery] = []

    for msg in messages:
        bill = parse_mail_message(msg)
        if bill is None:
            continue
        stats["parsed"] += 1

        if not bill.barcode:
            continue
        stats["with_barcode"] += 1

        is_sent = already_processed(bill.installation, bill.pdf_name)
        if is_sent:
            stats["already_sent"] += 1
        elif not include_unprocessed:
            continue

        contacts = load_contacts_for_installation(bill.installation)
        if not contacts:
            continue
        stats["with_contacts"] += 1
        deliveries.append(PendingDelivery(bill=bill, contacts=contacts))

    return deliveries, stats


def process_barcode_catchup_day(
    day: date | None = None, *, include_unprocessed: bool = False
) -> tuple[list[PendingDelivery], dict]:
    """Barcode-only catch-up for bills of a single day already delivered."""
    resolved_day = day or date.today()
    return collect_barcode_catchup(
        find_day_emails(resolved_day), include_unprocessed=include_unprocessed
    )


def process_barcode_catchup_month(
    year: int, month: int, *, include_unprocessed: bool = False
) -> tuple[list[PendingDelivery], dict]:
    """Barcode-only catch-up for bills of a whole month already delivered."""
    start, end = month_bounds(year, month)
    return collect_barcode_catchup(
        find_range_emails(start, end), include_unprocessed=include_unprocessed
    )


def parse_month(value: str) -> tuple[int, int]:
    try:
        year_str, month_str = value.split("-", 1)
        year, month = int(year_str), int(month_str)
        date(year, month, 1)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            f"mês inválido {value!r}, use o formato AAAA-MM"
        ) from exc
    return year, month


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Processa faturas da Enel recebidas por email e envia via Evolution API."
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        help="Data para busca de faturas no email (formato AAAA-MM-DD). "
        "Se omitido, usa o dia atual a cada ciclo.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=None,
        help="Intervalo entre ciclos em segundos (padrão: POLL_INTERVAL_SECONDS ou 3600). "
        "Use 0 para rodar uma única vez.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Roda um único ciclo e sai (equivale a --interval-seconds 0).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prevê o que seria enviado sem disparar WhatsApp nem gravar estado.",
    )
    parser.add_argument(
        "--month",
        type=parse_month,
        default=None,
        metavar="AAAA-MM",
        help="Busca todas as contas do mês (roda uma única vez e sai).",
    )
    parser.add_argument(
        "--barcode-only",
        action="store_true",
        help="Envia APENAS o código de barras (mensagem própria) das contas "
        "já enviadas no período, sem reenviar texto nem PDF.",
    )
    parser.add_argument(
        "--barcode-all",
        action="store_true",
        help="Com --barcode-only, inclui também contas ainda não marcadas "
        "como enviadas (todas com código de barras e contato).",
    )
    return parser.parse_args(args)


def resolve_target_day(cli_date: date | None) -> date:
    """Dia a processar: fixo via --date ou o dia atual (para virar o dia no loop)."""
    return cli_date or date.today()


def resolve_interval_seconds(cli_interval: int | None) -> int:
    """Intervalo entre ciclos: flag --interval-seconds ou POLL_INTERVAL_SECONDS do ambiente."""
    if cli_interval is not None:
        return cli_interval
    try:
        return get_settings().poll_interval_seconds
    except Exception:
        return DEFAULT_POLL_INTERVAL_SECONDS


def build_preview(
    deliveries: list[PendingDelivery], state_path=None, *, barcode_only: bool = False
) -> list[dict]:
    """Describe what a dry run would send, without any side effect.

    Mirrors the grouped sending: one text per contact (plus intro when due),
    one barcode-only message per bill with barcode, and one PDF per bill.
    With ``barcode_only`` only the standalone barcode messages are previewed.
    """
    from voltbot.evolution import (
        build_barcode_message,
        build_combined_message,
        build_delivery_message,
        group_deliveries_by_contact,
    )

    preview = []
    for group in group_deliveries_by_contact(deliveries, state_path=state_path):
        if len(group.items) == 1:
            delivery, label = group.items[0]
            text = build_delivery_message(delivery, group.name, label)
        else:
            text = build_combined_message(group.items, group.name)
        barcode_messages = [
            barcode_message
            for delivery, _label in group.items
            if (barcode_message := build_barcode_message(delivery.bill.barcode))
        ]
        preview.append(
            {
                "phone": group.phone,
                "name": group.name,
                "intro": group.needs_intro and not barcode_only,
                "text": "" if barcode_only else text,
                "barcode_messages": barcode_messages,
                "bills": [
                    {
                        "installation": delivery.bill.installation,
                        "installation_label": label,
                        "bill_date": delivery.bill.date.isoformat(),
                        "pdf_name": delivery.bill.pdf_name,
                        "barcode": delivery.bill.barcode,
                        "amount": delivery.bill.amount,
                    }
                    for delivery, label in group.items
                ],
            }
        )
    return preview


def run_cycle(
    target_day: date | None = None,
    *,
    month: tuple[int, int] | None = None,
    dry_run: bool = False,
    barcode_only: bool = False,
    barcode_all: bool = False,
) -> dict:
    catchup_stats: dict | None = None
    if month is not None:
        label = f"{month[0]:04d}-{month[1]:02d}"
        print(f"[{datetime.now():%d/%m/%Y %H:%M:%S}] Buscando faturas do mês {label}...")
        if barcode_only:
            deliveries, catchup_stats = process_barcode_catchup_month(
                *month, include_unprocessed=barcode_all
            )
        else:
            deliveries = process_month(*month)
    else:
        resolved_day = target_day or date.today()
        print(
            f"[{datetime.now():%d/%m/%Y %H:%M:%S}] "
            f"Buscando faturas para o dia {resolved_day:%d/%m/%Y}..."
        )
        if barcode_only:
            deliveries, catchup_stats = process_barcode_catchup_day(
                resolved_day, include_unprocessed=barcode_all
            )
        else:
            deliveries = process_day(resolved_day)
    if barcode_only and catchup_stats is not None:
        print(
            f"E-mails lidos: {catchup_stats['emails']} | faturas: {catchup_stats['parsed']} | "
            f"com barras: {catchup_stats['with_barcode']} | "
            f"já enviadas: {catchup_stats['already_sent']} | "
            f"com contato: {catchup_stats['with_contacts']}"
        )
        print(f"Encontradas {len(deliveries)} contas para reenvio só do código de barras")
    else:
        print(f"Encontradas {len(deliveries)} contas")

    for delivery in deliveries:
        bill = delivery.bill
        barcode_info = f" | barras: {bill.barcode}" if bill.barcode else " | barras: ausente"
        print(
            f"- Instalação {bill.installation} | {bill.date} | "
            f"{bill.pdf_name} ({len(bill.pdf_bytes):,} bytes){barcode_info}"
        )

    if dry_run:
        preview = build_preview(deliveries, barcode_only=barcode_only)
        if barcode_only:
            total_messages = sum(len(item["barcode_messages"]) for item in preview)
        else:
            total_messages = sum(
                len(item["bills"])
                + len(item.get("barcode_messages", []))
                + 1
                + (1 if item["intro"] else 0)
                for item in preview
            )
        print(f"[dry-run] {total_messages} mensagens seriam enviadas (nada disparado)")
        return {
            "deliveries": len(deliveries),
            "contacts": len(preview),
            "messages": total_messages,
            "dry_run": True,
            "barcode_only": barcode_only,
            "barcode_all": barcode_all,
            "catchup_stats": catchup_stats,
            "preview": preview,
        }

    if barcode_only:
        from voltbot.evolution import send_barcode_only_deliveries

        results = send_barcode_only_deliveries(deliveries)
    else:
        results = send_pending_deliveries(deliveries)
    print(f"Enviadas {len(results)} mensagens pela Evolution API")
    return {
        "deliveries": len(deliveries),
        "messages": len(results),
        "dry_run": False,
        "barcode_only": barcode_only,
        "barcode_all": barcode_all,
    }


def main() -> None:
    cli_args = parse_args()
    if cli_args.month is not None:
        try:
            run_cycle(
                month=cli_args.month,
                dry_run=cli_args.dry_run,
                barcode_only=cli_args.barcode_only,
                barcode_all=cli_args.barcode_all,
            )
        except EvolutionError as exc:
            raise SystemExit(f"Falha no envio pela Evolution API: {exc}") from exc
        return
    interval = 0 if cli_args.once else resolve_interval_seconds(cli_args.interval_seconds)

    if interval <= 0:
        try:
            run_cycle(
                resolve_target_day(cli_args.date),
                dry_run=cli_args.dry_run,
                barcode_only=cli_args.barcode_only,
                barcode_all=cli_args.barcode_all,
            )
        except EvolutionError as exc:
            raise SystemExit(f"Falha no envio pela Evolution API: {exc}") from exc
        return

    print(f"Loop ativado: ciclo a cada {interval}s (use --once para rodada única).")
    while True:
        try:
            run_cycle(
                resolve_target_day(cli_args.date),
                dry_run=cli_args.dry_run,
                barcode_only=cli_args.barcode_only,
                barcode_all=cli_args.barcode_all,
            )
        except EvolutionError as exc:
            print(f"Falha no envio pela Evolution API: {exc} — tentando de novo em {interval}s")
        except Exception:
            print("Erro inesperado no ciclo — tentando de novo no próximo intervalo:")
            traceback.print_exc()
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Encerrando loop.")
            break


if __name__ == "__main__":
    main()
