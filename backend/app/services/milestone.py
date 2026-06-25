"""Age-milestone timeline service.

Surfaces each household member's upcoming (and past) age-triggered financial
events from their date of birth: penalty-free withdrawals (59½), Social Security
(earliest 62 and full retirement age), Medicare (65), and the SECURE 2.0 RMD
start age. All the age math lives in app.services.age; this layer just gathers
members and marks which milestones have been reached.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.member import HouseholdMember
from app.schemas.report import AgeMilestonesReport, MemberMilestones, MilestoneItem
from app.services.age import current_age, milestones


class MilestoneService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def age_milestones(self, ctx: VisibilityContext) -> AgeMilestonesReport:
        today = date.today()
        result = await self.session.execute(
            select(HouseholdMember).where(
                HouseholdMember.household_id == ctx.household_id,
                HouseholdMember.is_active.is_(True),
            )
        )
        members = list(result.scalars().all())

        rows: list[MemberMilestones] = []
        for member in members:
            ms = milestones(member.date_of_birth, member.retirement_target_age)
            items = (
                [
                    MilestoneItem(
                        key=m.key,
                        label=m.label,
                        age_label=m.age_label,
                        date=m.date,
                        year=m.year,
                        reached=m.date <= today,
                    )
                    for m in ms
                ]
                if ms is not None
                else []
            )
            rows.append(
                MemberMilestones(
                    member_id=member.id,
                    display_name=member.display_name,
                    date_of_birth=member.date_of_birth,
                    current_age=current_age(member.date_of_birth),
                    milestones=items,
                    note=(
                        None
                        if ms is not None
                        else "Add a date of birth to see this member's milestones."
                    ),
                )
            )
        return AgeMilestonesReport(members=rows)
