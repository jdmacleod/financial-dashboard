"""Guards that the Castellano (H6) household seeds everyday discretionary
spending, not just its large scheduled flows.

Regression: H6 originally modeled only the UHNW retiree's scheduled cash flows
(Social Security, RMD/CRT distributions, Medicare, premiums, gifts, capital
calls) and carried ~282 transactions — roughly a seventh of any other demo
household. The discretionary-spend block (groceries, dining, car service,
healthcare, etc., routed through checking) brings it in line. It is net-worth
neutral: every entry debits checking, which the opening-balance plug reconciles
to its $120K target, so the household stays at exactly $18,290,000 (covered by
``test_seed_net_worth_agreement``).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.transaction import Transaction

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import seed_demo_data  # noqa: E402


async def test_h6_has_everyday_discretionary_spending(db_session: AsyncSession) -> None:
    rng = random.Random(42 + 6)  # same deterministic RNG the CLI uses for household 6
    await seed_demo_data._SEEDERS[6](db_session, rng)
    await db_session.flush()

    household = (
        await db_session.execute(select(Household).where(Household.name == "Castellano Household"))
    ).scalar_one()
    account_ids = select(Account.id).where(Account.household_id == household.id)

    total = (
        await db_session.execute(
            select(func.count(Transaction.id)).where(Transaction.account_id.in_(account_ids))
        )
    ).scalar_one()
    # Was ~282 before discretionary spending was added; the block lands it ~1,400.
    # A floor well above the old level guards against the block being dropped
    # without coupling the test to the exact (RNG-dependent) count.
    assert total >= 1200, f"H6 has only {total} transactions — discretionary spend missing?"

    # And it must be real everyday spending, not just more scheduled flows: assert
    # transactions exist in categories H6 never used before.
    for slug in ("groceries", "restaurants", "transportation"):
        count = (
            await db_session.execute(
                select(func.count(Transaction.id))
                .join(Category, Transaction.category_id == Category.id)
                .where(Transaction.account_id.in_(account_ids), Category.slug == slug)
            )
        ).scalar_one()
        assert count > 0, f"H6 has no '{slug}' transactions"
