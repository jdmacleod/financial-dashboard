"""Integration tests for rules-based categorization (R4)."""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core import throttle
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


@pytest.fixture(autouse=True)
def _clear_throttle() -> Any:
    throttle.reset_all()
    yield
    throttle.reset_all()


async def _category(client: AsyncClient, headers: dict[str, str], name: str) -> str:
    resp = await client.post("/api/v1/categories", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _account(client: AsyncClient, headers: dict[str, str]) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": "checking", "nickname": "Rules Checking"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _rule(
    client: AsyncClient,
    headers: dict[str, str],
    pattern: str,
    category_id: str,
    match_type: str = "contains",
    priority: int = 0,
) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/category-rules",
        json={
            "pattern": pattern,
            "match_type": match_type,
            "category_id": category_id,
            "priority": priority,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_rule_crud(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    coffee = await _category(client, headers, "Coffee")
    rule = await _rule(client, headers, "STARBUCKS", coffee)

    listed = await client.get("/api/v1/category-rules", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    upd = await client.patch(
        f"/api/v1/category-rules/{rule['id']}", json={"priority": 5}, headers=headers
    )
    assert upd.status_code == 200
    assert upd.json()["priority"] == 5

    dele = await client.delete(f"/api/v1/category-rules/{rule['id']}", headers=headers)
    assert dele.status_code == 204
    assert (await client.get("/api/v1/category-rules", headers=headers)).json() == []


async def test_invalid_regex_rejected(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    coffee = await _category(client, headers, "Coffee")
    resp = await client.post(
        "/api/v1/category-rules",
        json={"pattern": "([unclosed", "match_type": "regex", "category_id": coffee},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_rule_fills_category_on_manual_create(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    coffee = await _category(client, headers, "Coffee")
    account_id = await _account(client, headers)
    await _rule(client, headers, "STARBUCKS", coffee)

    resp = await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={
            "transaction_date": "2026-07-01",
            "amount": "-5.75",
            "payee_normalized": "STARBUCKS #4821",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["category_id"] == coffee


async def test_explicit_category_is_never_overridden(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    coffee = await _category(client, headers, "Coffee")
    dining = await _category(client, headers, "Dining")
    account_id = await _account(client, headers)
    await _rule(client, headers, "STARBUCKS", coffee)

    # Caller sets Dining explicitly; the STARBUCKS->Coffee rule must not win.
    resp = await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={
            "transaction_date": "2026-07-01",
            "amount": "-5.75",
            "payee_normalized": "STARBUCKS #4821",
            "category_id": dining,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["category_id"] == dining


async def test_rule_applies_on_promote(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    groceries = await _category(client, headers, "Groceries")
    account_id = await _account(client, headers)
    await _rule(client, headers, "WHOLE FOODS", groceries)

    staged = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging",
        json={
            "rows": [
                {
                    "transaction_date": "2026-07-02",
                    "amount": "-88.10",
                    "payee_raw": "WHOLE FOODS #123 SEATTLE",
                    "external_id": "wf1",
                }
            ]
        },
        headers=headers,
    )
    batch_id = staged.json()["batch_id"]
    promoted = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging/{batch_id}/promote", headers=headers
    )
    assert promoted.json()["promoted"] == 1

    txns = (
        await client.get(f"/api/v1/accounts/{account_id}/transactions", headers=headers)
    ).json()["items"]
    assert len(txns) == 1
    assert txns[0]["category_id"] == groceries


async def test_priority_orders_matches(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    coffee = await _category(client, headers, "Coffee")
    treats = await _category(client, headers, "Treats")
    account_id = await _account(client, headers)
    # Both match "STARBUCKS"; higher priority wins.
    await _rule(client, headers, "STARBUCKS", coffee, priority=1)
    await _rule(client, headers, "STARBUCKS", treats, priority=9)

    resp = await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={
            "transaction_date": "2026-07-01",
            "amount": "-6.00",
            "payee_normalized": "STARBUCKS RESERVE",
        },
        headers=headers,
    )
    assert resp.json()["category_id"] == treats


async def test_suggest_from_history_and_backfill(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    dining = await _category(client, headers, "Dining")
    account_id = await _account(client, headers)

    # Seed 3 categorized "CHIPOTLE" transactions → a suggestion candidate.
    for i in range(3):
        await client.post(
            f"/api/v1/accounts/{account_id}/transactions",
            json={
                "transaction_date": f"2026-07-0{i + 1}",
                "amount": "-12.00",
                "payee_normalized": "CHIPOTLE ONLINE",
                "category_id": dining,
            },
            headers=headers,
        )
    # And one uncategorized CHIPOTLE for backfill.
    uncat = await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={
            "transaction_date": "2026-07-05",
            "amount": "-13.00",
            "payee_normalized": "CHIPOTLE ONLINE",
        },
        headers=headers,
    )
    assert uncat.json()["category_id"] is None

    suggestions = await client.get("/api/v1/category-rules/suggestions", headers=headers)
    assert suggestions.status_code == 200
    cand = [s for s in suggestions.json() if "CHIPOTLE" in s["pattern"]]
    assert cand and cand[0]["category_id"] == dining and cand[0]["occurrences"] == 3

    # Create the rule and backfill the uncategorized one.
    await _rule(client, headers, "CHIPOTLE", dining)
    backfill = await client.post("/api/v1/category-rules/backfill", headers=headers)
    assert backfill.status_code == 200
    assert backfill.json()["updated"] == 1

    txns = (
        await client.get(f"/api/v1/accounts/{account_id}/transactions", headers=headers)
    ).json()["items"]
    assert all(t["category_id"] == dining for t in txns)
