import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.db.models.category import Category
from app.services.setup import SYSTEM_HOUSEHOLD_ID, SetupService


async def test_run_creates_household_member_user(db_session: AsyncSession) -> None:
    service = SetupService(db_session)
    token, member_name = await service.run(
        household_name="The MacLeods",
        member_name="Jason",
        email="jason@example.com",
        password="CorrectHorse123!",
    )
    assert isinstance(token, str)
    assert member_name == "Jason"


async def test_run_rejects_second_call(db_session: AsyncSession) -> None:
    service = SetupService(db_session)
    await service.run(
        household_name="The MacLeods",
        member_name="Jason",
        email="jason@example.com",
        password="CorrectHorse123!",
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.run(
            household_name="Another Household",
            member_name="Someone",
            email="someone@example.com",
            password="CorrectHorse123!",
        )
    assert exc_info.value.status_code == 409


async def test_run_writes_exactly_one_setup_completed_audit_row(db_session: AsyncSession) -> None:
    service = SetupService(db_session)
    await service.run(
        household_name="The MacLeods",
        member_name="Jason",
        email="jason@example.com",
        password="CorrectHorse123!",
    )
    rows = (
        (
            await db_session.execute(
                select(AuditLog).where(AuditLog.action == "household.setup_completed")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_run_copies_system_categories_into_new_household(db_session: AsyncSession) -> None:
    system_categories = (
        (
            await db_session.execute(
                select(Category).where(Category.household_id == SYSTEM_HOUSEHOLD_ID)
            )
        )
        .scalars()
        .all()
    )
    assert len(system_categories) > 0

    service = SetupService(db_session)
    await service.run(
        household_name="The MacLeods",
        member_name="Jason",
        email="jason@example.com",
        password="CorrectHorse123!",
    )

    new_household_result = await db_session.execute(
        select(Category.household_id).where(Category.household_id != SYSTEM_HOUSEHOLD_ID).limit(1)
    )
    new_household_id = new_household_result.scalar_one()
    copied = (
        (
            await db_session.execute(
                select(Category).where(Category.household_id == new_household_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(copied) == len(system_categories)
    assert {c.name for c in copied} == {c.name for c in system_categories}
