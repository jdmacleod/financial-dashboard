"""End-to-end round trip (T8): the ingest CLI's parser → staging API (PAT auth)
→ promote → the row counts in the account balance.

The CLI's HTTP client mechanics are unit-tested in the ingest package (MockTransport);
here we drive the REAL API in-process with the parsed rows to prove the seams line
up: parser output is accepted by the staging schema, a PAT authorizes the push,
and promote turns staged rows into balance-affecting transactions.

The PAT issue → use → revoke lifecycle E2E lives in test_pat.py.
"""

import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from app.core import throttle
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers

# Make the standalone ingest package importable without installing it.
_INGEST_DIR = Path(__file__).resolve().parents[3] / "ingest"
if str(_INGEST_DIR) not in sys.path:
    sys.path.insert(0, str(_INGEST_DIR))

from hearthledger_ingest.parsers import parse_csv  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_throttle() -> Any:
    throttle.reset_all()
    yield
    throttle.reset_all()


async def test_cli_parse_to_staging_to_promote_round_trip(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    # 1. Account + PAT, exactly as an operator would set up the CLI.
    account_id = (
        await client.post(
            "/api/v1/accounts",
            json={"account_type": "checking", "nickname": "Ingest E2E"},
            headers=headers,
        )
    ).json()["id"]
    token = (
        await client.post("/api/v1/personal-access-tokens", json={"label": "cli"}, headers=headers)
    ).json()["token"]
    pat_headers = {"Authorization": f"Bearer {token}"}

    # 2. The CLI parses a real exported statement locally (note the PII in a memo).
    csv_bytes = (
        b"Date,Amount,Description,Memo,Reference\n"
        b"2026-01-05,-42.10,Coffee Shop,card 4111111111111111,R1\n"
        b"2026-01-06,-9.99,Music,,R2\n"
    )
    rows = parse_csv(csv_bytes)
    assert len(rows) == 2

    # 3. Push to staging with the PAT (what IngestClient.stage does over HTTP).
    staged = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging",
        json={"rows": rows},
        headers=pat_headers,
    )
    assert staged.status_code == 201, staged.text
    body = staged.json()
    assert body["staged"] == 2
    batch_id = body["batch_id"]

    # Server re-redacted the card number even though the CLI also masked it.
    listed = await client.get(
        f"/api/v1/accounts/{account_id}/import/staging/{batch_id}", headers=headers
    )
    memos = [r["memo"] for r in listed.json() if r["memo"]]
    assert all("4111111111111111" not in m for m in memos)

    # Staged rows do not move the balance yet.
    mid = (await client.get(f"/api/v1/accounts/{account_id}", headers=headers)).json()
    assert Decimal(mid["current_balance"] or "0") == Decimal("0")

    # 4. Promote — now the rows are real transactions and count in the balance.
    promoted = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging/{batch_id}/promote",
        headers=pat_headers,
    )
    assert promoted.status_code == 200
    assert promoted.json()["promoted"] == 2

    after = (await client.get(f"/api/v1/accounts/{account_id}", headers=headers)).json()
    assert Decimal(after["current_balance"]) == Decimal("-52.09")

    # The promoted rows are reviewed and carry the deterministic source.
    txns = (await client.get(f"/api/v1/accounts/{account_id}/transactions", headers=headers)).json()
    items = txns["items"]
    assert len(items) == 2
    assert all(t["source"] == "csv" for t in items)
    assert all(t["is_reviewed"] for t in items)
