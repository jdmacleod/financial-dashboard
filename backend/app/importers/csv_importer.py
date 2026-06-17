import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from dateutil.parser import parse as parse_date

REQUIRED_FIELDS = ("transaction_date", "amount")
OPTIONAL_FIELDS = ("payee_raw", "memo", "post_date", "external_id")

_HEADER_HINTS: tuple[tuple[str, str], ...] = (
    ("debit", "debit_amount"),
    ("credit", "credit_amount"),
    ("amount", "amount"),
    ("description", "payee_raw"),
    ("payee", "payee_raw"),
    ("memo", "memo"),
    ("reference", "external_id"),
    ("id", "external_id"),
    ("date", "transaction_date"),
)


@dataclass
class ParsedRow:
    transaction_date: date
    amount: Decimal
    payee_raw: str | None = None
    memo: str | None = None
    post_date: date | None = None
    external_id: str | None = None


def preview(
    content: bytes, max_rows: int = 10
) -> tuple[list[str], list[list[str]], dict[str, str]]:
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig")))
    rows = list(reader)
    headers = rows[0] if rows else []
    preview_rows = rows[1 : 1 + max_rows]
    return headers, preview_rows, suggest_mapping(headers)


def suggest_mapping(headers: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for header in headers:
        lower = header.lower()
        for hint, field in _HEADER_HINTS:
            if field in mapping.values():
                continue
            if hint in lower:
                mapping[field] = header
                break
    return mapping


def _parse_amount(raw: str) -> Decimal:
    cleaned = raw.strip().replace("$", "").replace(",", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid amount: {raw!r}") from exc
    return -value if negative else value


def _optional_str(raw_row: dict[str, str], mapping: dict[str, str], field: str) -> str | None:
    header = mapping.get(field)
    if not header:
        return None
    return (raw_row.get(header) or "").strip() or None


def parse_rows(content: bytes, mapping: dict[str, str]) -> list[ParsedRow]:
    if "transaction_date" not in mapping:
        raise ValueError("transaction_date must be mapped")
    if "amount" not in mapping and not ("debit_amount" in mapping and "credit_amount" in mapping):
        raise ValueError("amount (or debit_amount + credit_amount) must be mapped")

    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    parsed: list[ParsedRow] = []
    for raw_row in reader:
        transaction_date = parse_date(raw_row[mapping["transaction_date"]]).date()

        if "amount" in mapping:
            amount = _parse_amount(raw_row[mapping["amount"]])
        else:
            debit = _parse_amount(raw_row[mapping["debit_amount"]] or "0")
            credit = _parse_amount(raw_row[mapping["credit_amount"]] or "0")
            amount = credit - debit

        post_date = (
            parse_date(raw_row[mapping["post_date"]]).date()
            if mapping.get("post_date") and raw_row.get(mapping["post_date"])
            else None
        )

        parsed.append(
            ParsedRow(
                transaction_date=transaction_date,
                amount=amount,
                payee_raw=_optional_str(raw_row, mapping, "payee_raw"),
                memo=_optional_str(raw_row, mapping, "memo"),
                post_date=post_date,
                external_id=_optional_str(raw_row, mapping, "external_id"),
            )
        )
    return parsed
