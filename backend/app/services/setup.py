from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

SYSTEM_HOUSEHOLD_ID = "00000000-0000-0000-0000-000000000000"


class SetupService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_setup_done(self) -> bool:
        result = await self.session.execute(
            select(Household).where(Household.id != SYSTEM_HOUSEHOLD_ID).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def run(
        self,
        household_name: str,
        member_name: str,
        email: str,
        password: str,
    ) -> tuple[str, str]:
        if await self.is_setup_done():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Setup already completed",
            )

        now = datetime.now(timezone.utc)

        household = Household(name=household_name, settings={}, created_at=now)
        self.session.add(household)
        await self.session.flush()

        # Copy system categories to new household
        result = await self.session.execute(
            select(Category).where(Category.household_id == SYSTEM_HOUSEHOLD_ID)
        )
        system_categories = result.scalars().all()
        for cat in system_categories:
            new_cat = Category(
                household_id=household.id,
                name=cat.name,
                color_hex=cat.color_hex,
                icon=cat.icon,
                is_income=cat.is_income,
                is_system=cat.is_system,
                created_at=now,
            )
            self.session.add(new_cat)

        member = HouseholdMember(
            household_id=household.id,
            display_name=member_name,
            role="primary",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(member)
        await self.session.flush()

        user = User(
            member_id=member.id,
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            failed_login_attempts=0,
            last_password_change=now,
            created_at=now,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        await self.session.refresh(member)

        access_token = create_access_token(str(user.id), str(member.id), "primary")
        await self.session.commit()
        return access_token, member_name
