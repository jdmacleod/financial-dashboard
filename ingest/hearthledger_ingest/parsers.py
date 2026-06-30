"""Deterministic CSV / JSON statement parsers → canonical staging rows.

A canonical row is a dict with keys matching the HearthLedger staging API's
StagingRow schema: transaction_date (ISO str), amount (str), payee_raw, memo,
external_id, source, confidence. Deterministic parsers emit confidence 1.0 — the
value is real, not a model's guess. (LLM-parsed PDF, a later release, will emit a
real confidence score.)
"""

import csv
import io
import json
from typing import Any

from dateutil.parser import parse as parse_date

from hearthledger_ingest.pii import redact_pii

# Header keyword -> canonical field. First match wins per field.
_HEADER_HINTS: tuple[tuple[str, str], ...] = (
    ("date", "transaction_date"),
    ("amount", "amount"),
    ("description", "payee_raw"),
    ("payee", "payee_raw"),
    ("memo", "memo"),
    ("reference", "external_id"),
    ("id", "external_id"),
)


def _suggest_mapping(headers: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for header in headers:
        lower = header.lower()
        for hint, field in _HEADER_HINTS:
            if field in mapping:
                continue
            if hint in lower:
                mapping[field] = header
                break
    return mapping


def _clean_amount(raw: str) -> str:
    cleaned = raw.strip().replace("$", "").replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    return cleaned


def _row(
    transaction_date: str,
    amount: str,
    payee_raw: str | None,
    memo: str | None,
    external_id: str | None,
    source: str,
) -> dict[str, Any]:
    return {
        "transaction_date": transaction_date,
        "amount": amount,
        "payee_raw": redact_pii(payee_raw) or None,
        "memo": redact_pii(memo) or None,
        "external_id": external_id or None,
        "source": source,
        "confidence": "1.0",
    }


def parse_csv(content: bytes, mapping: dict[str, str] | None = None) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    resolved = mapping or _suggest_mapping(list(headers))
    if "transaction_date" not in resolved or "amount" not in resolved:
        raise ValueError("CSV must map at least transaction_date and amount columns")

    rows: list[dict[str, Any]] = []
    for raw in reader:
        date_str = parse_date(raw[resolved["transaction_date"]]).date().isoformat()
        amount = _clean_amount(raw[resolved["amount"]])
        rows.append(
            _row(
                transaction_date=date_str,
                amount=amount,
                payee_raw=_opt(raw, resolved, "payee_raw"),
                memo=_opt(raw, resolved, "memo"),
                external_id=_opt(raw, resolved, "external_id"),
                source="csv",
            )
        )
    return rows


def _opt(raw: dict[str, str], mapping: dict[str, str], field: str) -> str | None:
    header = mapping.get(field)
    if not header:
        return None
    return (raw.get(header) or "").strip() or None


def parse_json(content: bytes) -> list[dict[str, Any]]:
    """Parse a JSON array of objects with canonical-ish keys.

    Accepts {date|transaction_date, amount, payee|payee_raw|description, memo,
    external_id|id}. Amounts may be numbers or strings.
    """
    data = json.loads(content.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("JSON ingest expects a top-level array of transactions")

    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each JSON transaction must be an object")
        date_val = item.get("transaction_date") or item.get("date")
        if date_val is None or "amount" not in item:
            raise ValueError("Each JSON transaction needs a date and an amount")
        rows.append(
            _row(
                transaction_date=parse_date(str(date_val)).date().isoformat(),
                amount=_clean_amount(str(item["amount"])),
                payee_raw=item.get("payee_raw") or item.get("payee") or item.get("description"),
                memo=item.get("memo"),
                external_id=(
                    str(item["external_id"])
                    if item.get("external_id") is not None
                    else (str(item["id"]) if item.get("id") is not None else None)
                ),
                source="json",
            )
        )
    return rows


def parse_file(path: str, content: bytes, mapping: dict[str, str] | None = None) -> list[dict[str, Any]]:
    lower = path.lower()
    if lower.endswith(".csv"):
        return parse_csv(content, mapping)
    if lower.endswith(".json"):
        return parse_json(content)
    raise ValueError(f"Unsupported file type for {path!r}; expected .csv or .json")
