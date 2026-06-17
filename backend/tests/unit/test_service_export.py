from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_reauth_token
from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.export_job import ExportCreate
from app.services.export_service import ExportService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeArqPool:
    """In-process ArqRedis stand-in that also supports get/set for reauth KV."""

    def __init__(self) -> None:
        self.enqueued: list[tuple[Any, ...]] = []
        self._kv: dict[str, str] = {}

    async def enqueue_job(self, *args: Any, **kwargs: Any) -> None:
        self.enqueued.append(args)

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> None:
        self._kv[key] = str(value) if isinstance(value, bytes) else value

    async def get(self, key: str) -> bytes | None:
        val = self._kv.get(key)
        return val.encode() if val is not None else None


def _primary_ctx(household: Household, member: HouseholdMember, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role="primary",
        household_id=household.id,
        ip_address="127.0.0.1",
    )


def _partner_ctx(household: Household, member: HouseholdMember, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role="partner",
        household_id=household.id,
        ip_address="127.0.0.1",
    )


_FROM = date(2025, 1, 1)
_TO = date(2025, 12, 31)


def _ec(export_type: str) -> ExportCreate:
    """Build an ExportCreate for testing with fixed date range."""
    return ExportCreate(
        export_type=export_type,  # type: ignore[arg-type]
        from_date=_FROM,
        to_date=_TO,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_summary_export_no_reauth_needed(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Summary exports (pdf_summary, excel_summary) require no reauth token."""
    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    job = await svc.create(ctx, _ec("pdf_summary"))

    assert job.export_type == "pdf_summary"
    assert job.anonymized is True
    assert job.status == "pending"
    assert len(pool.enqueued) == 1
    assert pool.enqueued[0] == ("run_export_job", str(job.id))


@pytest.mark.asyncio
async def test_create_executor_export_no_reauth_raises_403(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Executor export without reauth token must raise 403."""
    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(ctx, _ec("pdf_executor"))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_executor_export_partner_raises_403(
    db_session: AsyncSession,
    household: Household,
    make_member: Any,
    make_user: Any,
) -> None:
    """Partner role must not create executor exports."""
    partner_member = await make_member(role="partner", display_name="Partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    ctx = _partner_ctx(household, partner_member, partner_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    reauth = create_reauth_token(str(partner_user.id))
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            ctx,
            _ec("pdf_executor"),
            reauth_token=reauth,
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_executor_export_with_valid_reauth(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Valid primary + valid reauth token creates and enqueues the job."""
    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    reauth = create_reauth_token(str(primary_user.id))
    job = await svc.create(
        ctx,
        _ec("pdf_executor"),
        reauth_token=reauth,
    )

    assert job.export_type == "pdf_executor"
    assert job.anonymized is False
    assert job.status == "pending"
    assert len(pool.enqueued) == 1


@pytest.mark.asyncio
async def test_get_export_job_wrong_household_raises_404(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    """Job from another household must not be visible."""
    from app.db.models.household import Household as HouseholdModel
    from tests.conftest import now

    other_household = HouseholdModel(name="Other", settings={}, created_at=now())
    db_session.add(other_household)
    await db_session.flush()

    other_member = await make_member(role="primary", display_name="Other Primary")
    other_user = await make_user(other_member, "other@example.com")

    other_ctx = VisibilityContext(
        user_id=other_user.id,
        member_id=other_member.id,
        role="primary",
        household_id=other_household.id,
    )

    pool = FakeArqPool()
    svc_creator = ExportService(db_session, pool)  # type: ignore[arg-type]
    job = await svc_creator.create(
        other_ctx,
        _ec("pdf_summary"),
    )

    # Now try to fetch it as the primary user in the *original* household
    primary_ctx = _primary_ctx(household, primary_member, primary_user)
    svc_reader = ExportService(db_session, pool)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc_info:
        await svc_reader.get(primary_ctx, job.id)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_list_exports_returns_household_jobs(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """list() returns only jobs belonging to this household."""
    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    await svc.create(ctx, _ec("pdf_summary"))
    await svc.create(ctx, _ec("excel_summary"))

    jobs = await svc.list(ctx)
    assert len(jobs) == 2
    assert all(j.household_id == household.id for j in jobs)


@pytest.mark.asyncio
async def test_reauth_token_single_use_enforcement(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """The same reauth token may only be used once for an executor export."""
    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    reauth = create_reauth_token(str(primary_user.id))

    # First use should succeed
    job1 = await svc.create(
        ctx,
        _ec("pdf_executor"),
        reauth_token=reauth,
    )
    assert job1.status == "pending"

    # Second use of the same token must be rejected
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            ctx,
            _ec("excel_executor"),
            reauth_token=reauth,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_export_dependent_role_raises_403(
    db_session: AsyncSession,
    household: Household,
    make_member: Any,
    make_user: Any,
) -> None:
    """Dependent role (can_write=False) cannot create any export."""
    dep_member = await make_member(role="dependent", display_name="Dependent")
    dep_user = await make_user(dep_member, "dependent@example.com")
    ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(ctx, _ec("pdf_summary"))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_executor_export_invalid_reauth_raises_403(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """An expired or tampered reauth token must be rejected with 403."""
    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            ctx,
            _ec("pdf_executor"),
            reauth_token="not.a.valid.jwt",
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_export_job_success(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """get() returns the job when the household matches."""
    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    job = await svc.create(ctx, _ec("excel_summary"))
    fetched = await svc.get(ctx, job.id)

    assert fetched.id == job.id
    assert fetched.household_id == household.id


@pytest.mark.asyncio
async def test_get_file_path_pending_job_raises_404(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """get_file_path() raises 404 when the job is still pending."""
    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    job = await svc.create(ctx, _ec("pdf_summary"))

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_file_path(ctx, job.id)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_file_path_complete_job_returns_path(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """get_file_path() returns the full path when job is complete."""
    from datetime import UTC, datetime

    ctx = _primary_ctx(household, primary_member, primary_user)
    pool = FakeArqPool()
    svc = ExportService(db_session, pool)  # type: ignore[arg-type]

    job = await svc.create(ctx, _ec("pdf_summary"))

    # Simulate worker completion
    job.status = "complete"
    job.filename = "hearthledger_pdf_summary_test.pdf"
    job.completed_at = datetime.now(UTC)
    await db_session.flush()

    file_path = await svc.get_file_path(ctx, job.id)

    assert file_path.endswith("hearthledger_pdf_summary_test.pdf")
