"""Guards the agreement between each demo household's hardcoded summary
``net_worth`` and the value ``ReportService`` actually computes from the seeded
data.

The summary figures in ``scripts/seed_households/h*.py`` are hand-computed
claims ("ReportService-computed net worth as of 2026-06-21"). Nothing else
asserts they stay true, so a future edit to debt balances, snapshots, or the
liability-valuation logic could silently drift a household's real net worth away
from its advertised summary. This test seeds each household into the test DB and
recomputes net worth the same way the app does, failing if any household drifts
more than a dollar (summaries are rounded to whole dollars).
"""

from __future__ import annotations

import random
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.services.report import ReportService

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import seed_demo_data  # noqa: E402

# The hardcoded summaries are computed for the default end of the seed window.
# Keep this in lockstep with seed_households._util.DATE_END's default.
_AS_OF = date(2026, 6, 21)

# Rounding allowance: summaries are whole dollars, computed values carry cents.
_TOLERANCE = 1.0


@pytest.mark.parametrize("household_num", sorted(seed_demo_data._SEEDERS))
async def test_seed_summary_net_worth_matches_computed(
    db_session: AsyncSession, household_num: int
) -> None:
    # Seed exactly one household with the same deterministic RNG the seed CLI
    # uses (random.Random(42 + num)), into the rolled-back test transaction.
    rng = random.Random(42 + household_num)
    summary = await seed_demo_data._SEEDERS[household_num](db_session, rng)
    await db_session.flush()

    # Resolve the household by its declared name. Scoping by name matters: the
    # baseline migration seeds a 'SYSTEM_TEMPLATE' household, so "the only
    # household" / "any primary member" lookups are ambiguous.
    expected_name = seed_demo_data._HOUSEHOLD_NAMES[household_num]
    household = (
        await db_session.execute(select(Household).where(Household.name == expected_name))
    ).scalar_one_or_none()
    assert household is not None, (
        f"seeded household name drifted from _HOUSEHOLD_NAMES[{household_num}] ({expected_name!r})"
    )

    member = (
        (
            await db_session.execute(
                select(HouseholdMember).where(
                    HouseholdMember.household_id == household.id,
                    HouseholdMember.role == "primary",
                    HouseholdMember.is_active.is_(True),
                )
            )
        )
        .scalars()
        .first()
    )
    assert member is not None, f"{expected_name}: no active primary member seeded"
    user = (
        (await db_session.execute(select(User).where(User.member_id == member.id)))
        .scalars()
        .first()
    )
    assert user is not None, f"{expected_name}: primary member has no user"

    ctx = VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role="primary",
        household_id=household.id,
    )
    svc = ReportService(db_session)
    point = await svc.current_net_worth(ctx, _AS_OF)

    computed = float(point.net_worth)
    expected = float(summary["net_worth"])
    assert abs(computed - expected) <= _TOLERANCE, (
        f"{expected_name}: summary net_worth ${expected:,.0f} disagrees with "
        f"computed ${computed:,.2f} (diff ${computed - expected:,.2f}). "
        f"Update the summary in the seed module or fix the data/computation."
    )
