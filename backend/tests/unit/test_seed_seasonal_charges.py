"""Guards that seasonal credit-card charges (vacation travel, December gifts)
actually land on the ledger for the Okonkwo-Rivera (H2) and Whitfield-Torres
(H3) demo households.

Regression: both households built their card transactions into a local list,
called ``add(*card_txns)`` to record them, and only *then* ran the seasonal
``*_var`` calls (travel in summer/spring, gifts in December). Those seasonal
charges extended the already-recorded list, so they were summed into the
monthly statement payment but never written to ``all_txns`` — invisible on the
Spending report while still draining the budget. The fix moves the record step
to after the seasonal calls. This test fails on the old ordering (zero travel /
gifts transactions) and passes once they reach the ledger.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest
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


@pytest.mark.parametrize(
    ("household_num", "household_name"),
    [(2, "Okonkwo-Rivera Household"), (3, "Whitfield-Torres Household")],
)
async def test_seasonal_card_charges_reach_the_ledger(
    db_session: AsyncSession, household_num: int, household_name: str
) -> None:
    await seed_demo_data._SEEDERS[household_num](db_session, random.Random(42 + household_num))
    await db_session.flush()

    household = (
        await db_session.execute(select(Household).where(Household.name == household_name))
    ).scalar_one()
    account_ids = select(Account.id).where(Account.household_id == household.id)

    for slug in ("travel", "gifts_given"):
        count = (
            await db_session.execute(
                select(func.count(Transaction.id))
                .join(Category, Transaction.category_id == Category.id)
                .where(Transaction.account_id.in_(account_ids), Category.slug == slug)
            )
        ).scalar_one()
        assert count > 0, (
            f"{household_name} has no '{slug}' transactions — seasonal card charges "
            f"orphaned again? (recorded before the seasonal *_var calls)"
        )
