"""Unit tests for the deterministic CSV/JSON parsers."""

import json

import pytest

from hearthledger_ingest.parsers import parse_csv, parse_file, parse_json


def test_parse_csv_auto_mapping() -> None:
    content = b"Date,Amount,Description,Reference\n2026-01-05,-42.10,Coffee Shop,REF1\n"
    rows = parse_csv(content)
    assert len(rows) == 1
    r = rows[0]
    assert r["transaction_date"] == "2026-01-05"
    assert r["amount"] == "-42.10"
    assert r["payee_raw"] == "Coffee Shop"
    assert r["external_id"] == "REF1"
    assert r["source"] == "csv"
    assert r["confidence"] == "1.0"


def test_parse_csv_parenthesised_negative_and_currency() -> None:
    content = b"Date,Amount,Description\n01/15/2026,\"($1,234.56)\",Rent\n"
    rows = parse_csv(content)
    assert rows[0]["amount"] == "-1234.56"
    assert rows[0]["transaction_date"] == "2026-01-15"


def test_parse_csv_redacts_pii_in_payee() -> None:
    content = b"Date,Amount,Description\n2026-01-05,-1.00,ACH 4111111111111111\n"
    rows = parse_csv(content)
    assert "4111111111111111" not in rows[0]["payee_raw"]
    assert "1111" in rows[0]["payee_raw"]


def test_parse_csv_requires_date_and_amount() -> None:
    with pytest.raises(ValueError, match="transaction_date and amount"):
        parse_csv(b"Foo,Bar\n1,2\n")


def test_parse_json_array() -> None:
    payload = json.dumps(
        [
            {"date": "2026-02-01", "amount": -9.99, "payee": "Music", "id": "x1"},
            {"transaction_date": "2026-02-02", "amount": "100.00", "external_id": "x2"},
        ]
    ).encode()
    rows = parse_json(payload)
    assert len(rows) == 2
    assert rows[0]["amount"] == "-9.99"
    assert rows[0]["external_id"] == "x1"
    assert rows[0]["source"] == "json"
    assert rows[1]["transaction_date"] == "2026-02-02"


def test_parse_json_rejects_non_array() -> None:
    with pytest.raises(ValueError, match="array"):
        parse_json(b'{"date": "2026-01-01", "amount": 1}')


def test_parse_json_requires_date_and_amount() -> None:
    with pytest.raises(ValueError, match="date and an amount"):
        parse_json(b'[{"payee": "x"}]')


def test_parse_file_dispatch_and_unsupported() -> None:
    csv_rows = parse_file("a.csv", b"Date,Amount\n2026-01-01,1.00\n")
    assert csv_rows[0]["source"] == "csv"
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_file("a.pdf", b"...")
