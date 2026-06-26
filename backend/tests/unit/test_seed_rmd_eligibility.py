"""Guards that demo households seed ``accounts.tax_treatment`` so the Required
Distribution report and FIRE RMD projection work on demo data.

Regression: ``make_account`` originally never set ``tax_treatment``, leaving every
seeded account NULL. Both ``RmdService`` and the FIRE RMD path filter on
``tax_treatment == 'pretax'``, so the Langford household — whose primary, Bob
(b. 1952, age 74), owns a Rollover IRA explicitly modeled to take quarterly RMD
withdrawals — produced *zero* Required Distribution rows. The fix seeds
``tax_treatment`` from ``account_type`` (mirroring ``AccountService.create``).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.services.rmd import RmdService

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import seed_demo_data  # noqa: E402


async def _seed_langford(db_session: AsyncSession) -> tuple[Household, HouseholdMember, User]:
    rng = random.Random(42 + 5)  # same deterministic RNG the CLI uses for household 5
    await seed_demo_data._SEEDERS[5](db_session, rng)
    await db_session.flush()
    household = (
        await db_session.execute(select(Household).where(Household.name == "Langford Household"))
    ).scalar_one()
    member = (
        (
            await db_session.execute(
                select(HouseholdMember).where(
                    HouseholdMember.household_id == household.id,
                    HouseholdMember.role == "primary",
                )
            )
        )
        .scalars()
        .first()
    )
    assert member is not None
    user = (
        (await db_session.execute(select(User).where(User.member_id == member.id)))
        .scalars()
        .first()
    )
    assert user is not None
    return household, member, user


async def test_seeded_pretax_iras_are_tagged_pretax(db_session: AsyncSession) -> None:
    household, _, _ = await _seed_langford(db_session)
    accounts = (
        (await db_session.execute(select(Account).where(Account.household_id == household.id)))
        .scalars()
        .all()
    )
    by_type = {a.account_type: a.tax_treatment for a in accounts if "retirement" in a.account_type}
    assert by_type.get("retirement_ira") == "pretax"
    assert by_type.get("retirement_roth_ira") == "roth"


async def test_langford_required_distribution_report_includes_bob(
    db_session: AsyncSession,
) -> None:
    household, member, user = await _seed_langford(db_session)
    ctx = VisibilityContext(
        user_id=user.id, member_id=member.id, role="primary", household_id=household.id
    )

    report = await RmdService(db_session).required_distributions(ctx, 2026)

    # Bob owns a pretax Rollover IRA, so he must appear as a row.
    bob = next((r for r in report.members if r.display_name == "Bob Langford"), None)
    assert bob is not None, "Bob Langford should have a Required Distribution row"
    # Age 74 in 2026, born 1952 -> RMD start age 73 -> RMD has started.
    assert bob.rmd_start_age == 73
    assert bob.has_started is True
    # A real RMD amount is computed from his prior-year-end pretax balance.
    assert bob.pretax_balance is not None and bob.pretax_balance > 0
    assert bob.rmd_amount is not None and bob.rmd_amount > 0
