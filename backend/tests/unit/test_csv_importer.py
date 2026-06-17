from datetime import date
from decimal import Decimal

import pytest

from app.importers import csv_importer


def test_suggest_mapping_matches_doc_example() -> None:
    headers = ["Date", "Amount", "Description", "Balance"]
    mapping = csv_importer.suggest_mapping(headers)
    assert mapping == {
        "transaction_date": "Date",
        "amount": "Amount",
        "payee_raw": "Description",
    }


def test_suggest_mapping_finds_debit_credit_and_reference() -> None:
    headers = ["Posting Date", "Debit", "Credit", "Memo", "Reference"]
    mapping = csv_importer.suggest_mapping(headers)
    assert mapping["debit_amount"] == "Debit"
    assert mapping["credit_amount"] == "Credit"
    assert mapping["memo"] == "Memo"
    assert mapping["external_id"] == "Reference"
    assert mapping["transaction_date"] == "Posting Date"


def test_preview_returns_headers_and_rows() -> None:
    content = b"Date,Amount,Description\n2025-01-15,-84.23,WHOLEFDS #123\n"
    headers, rows, mapping = csv_importer.preview(content)
    assert headers == ["Date", "Amount", "Description"]
    assert rows == [["2025-01-15", "-84.23", "WHOLEFDS #123"]]
    assert mapping["transaction_date"] == "Date"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("-84.23", Decimal("-84.23")),
        ("$1,204.56", Decimal("1204.56")),
        ("(45.10)", Decimal("-45.10")),
        ("  12.00 ", Decimal("12.00")),
    ],
)
def test_parse_amount_handles_currency_formatting(raw: str, expected: Decimal) -> None:
    assert csv_importer._parse_amount(raw) == expected


def test_parse_amount_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="Invalid amount"):
        csv_importer._parse_amount("not-a-number")


def test_parse_rows_with_signed_amount_column() -> None:
    content = (
        b"Date,Description,Amount,Reference\n"
        b"2025-01-15,WHOLEFDS #123,-84.23,TXN-1\n"
        b"2025-01-16,PAYROLL DEPOSIT,2500.00,TXN-2\n"
    )
    mapping = {
        "transaction_date": "Date",
        "amount": "Amount",
        "payee_raw": "Description",
        "external_id": "Reference",
    }
    rows = csv_importer.parse_rows(content, mapping)
    assert len(rows) == 2
    assert rows[0].transaction_date == date(2025, 1, 15)
    assert rows[0].amount == Decimal("-84.23")
    assert rows[0].payee_raw == "WHOLEFDS #123"
    assert rows[0].external_id == "TXN-1"
    assert rows[1].amount == Decimal("2500.00")


def test_parse_rows_with_debit_credit_split_columns() -> None:
    content = b"Date,Debit,Credit\n2025-01-15,84.23,\n2025-01-16,,2500.00\n"
    mapping = {"transaction_date": "Date", "debit_amount": "Debit", "credit_amount": "Credit"}
    rows = csv_importer.parse_rows(content, mapping)
    assert rows[0].amount == Decimal("-84.23")
    assert rows[1].amount == Decimal("2500.00")


def test_parse_rows_requires_transaction_date_mapping() -> None:
    content = b"Amount\n1.00\n"
    with pytest.raises(ValueError, match="transaction_date"):
        csv_importer.parse_rows(content, {"amount": "Amount"})


def test_parse_rows_requires_amount_or_split_columns() -> None:
    content = b"Date\n2025-01-15\n"
    with pytest.raises(ValueError, match="amount"):
        csv_importer.parse_rows(content, {"transaction_date": "Date"})


def test_parse_rows_parses_optional_post_date() -> None:
    content = b"Date,Amount,Posted\n2025-01-15,-10.00,2025-01-17\n"
    mapping = {"transaction_date": "Date", "amount": "Amount", "post_date": "Posted"}
    rows = csv_importer.parse_rows(content, mapping)
    assert rows[0].post_date == date(2025, 1, 17)
