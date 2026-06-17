from datetime import date
from decimal import Decimal
from pathlib import Path

from app.importers import ofx_importer

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_parse_maps_all_ofx_fields() -> None:
    content = (FIXTURES / "sample.ofx").read_bytes()
    rows = ofx_importer.parse(content)
    assert len(rows) == 1
    row = rows[0]
    assert row.transaction_date == date(2025, 1, 17)
    assert row.post_date == date(2025, 1, 18)
    assert row.amount == Decimal("-45.10")
    assert row.payee_raw == "AMAZON.COM"
    assert row.memo == "ONLINE PURCHASE"
    assert row.external_id == "OFXTXN0001"
