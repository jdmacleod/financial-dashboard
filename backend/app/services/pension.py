import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot
from app.core.encryption import decrypt, encrypt
from app.core.visibility import VisibilityContext
from app.db.models.pension import PensionAccount, PensionEstimateHistory
from app.repositories.account import AccountRepository
from app.repositories.pension import PensionRepository
from app.schemas.pension import (
    PensionAccountCreate,
    PensionAccountResponse,
    PensionAccountUpdate,
)

# PensionAccount fields that drive present value. A change to any of these
# appends a PensionEstimateHistory row so past net-worth points keep their
# original valuation.
_PV_FIELDS = (
    "monthly_benefit_estimate",
    "cola_adjustment_rate",
    "survivor_benefit_percent",
    "eligibility_date",
)


def _to_response(pension: PensionAccount) -> PensionAccountResponse:
    return PensionAccountResponse(
        id=pension.id,
        account_id=pension.account_id,
        member_id=pension.member_id,
        plan_name=decrypt(pension.plan_name_enc) if pension.plan_name_enc else None,
        administrator=decrypt(pension.administrator_enc) if pension.administrator_enc else None,
        monthly_benefit_estimate=pension.monthly_benefit_estimate,
        eligibility_age=pension.eligibility_age,
        eligibility_date=pension.eligibility_date,
        cola_adjustment_rate=pension.cola_adjustment_rate,
        is_vested=pension.is_vested,
        vesting_date=pension.vesting_date,
        survivor_benefit_percent=pension.survivor_benefit_percent,
        notes=decrypt(pension.notes_enc) if pension.notes_enc else None,
        created_at=pension.created_at,
        updated_at=pension.updated_at,
    )


class PensionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)
        self.pension_repo = PensionRepository(session)
        self.audit_repo = AuditRepository(session)

    async def _record_estimate(self, pension: PensionAccount, effective_date: date) -> None:
        """Append (or update, if one already exists for ``effective_date``) a
        present-value snapshot for this pension."""
        row = await self.pension_repo.get_estimate_on(pension.id, effective_date)
        if row is None:
            row = PensionEstimateHistory(
                pension_account_id=pension.id,
                effective_date=effective_date,
                created_at=datetime.now(UTC),
            )
            self.session.add(row)
        row.monthly_benefit_estimate = pension.monthly_benefit_estimate
        row.cola_adjustment_rate = pension.cola_adjustment_rate
        row.survivor_benefit_percent = pension.survivor_benefit_percent
        row.eligibility_date = pension.eligibility_date
        await self.session.flush()

    async def get(self, ctx: VisibilityContext, account_id: uuid.UUID) -> PensionAccountResponse:
        await self.account_repo.get_by_id(
            ctx, account_id
        )  # enforces RBAC (raises 404 if not visible)
        pension = await self.pension_repo.get_by_account_id(account_id)
        if pension is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pension record not found"
            )
        return _to_response(pension)

    async def create(
        self, ctx: VisibilityContext, account_id: uuid.UUID, data: PensionAccountCreate
    ) -> PensionAccount:
        account = await self.account_repo.get_by_id(ctx, account_id)
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if account.account_type != "pension":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pension records may only be linked to pension accounts",
            )
        if await self.pension_repo.get_by_account_id(account_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This account already has a pension record",
            )

        now = datetime.now(UTC)
        pension = PensionAccount(
            account_id=account_id,
            member_id=data.member_id,
            plan_name_enc=encrypt(data.plan_name) if data.plan_name else None,
            administrator_enc=encrypt(data.administrator) if data.administrator else None,
            monthly_benefit_estimate=data.monthly_benefit_estimate,
            eligibility_age=data.eligibility_age,
            eligibility_date=data.eligibility_date,
            cola_adjustment_rate=data.cola_adjustment_rate,
            is_vested=data.is_vested,
            vesting_date=data.vesting_date,
            survivor_benefit_percent=data.survivor_benefit_percent,
            notes_enc=encrypt(data.notes) if data.notes else None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(pension)
        try:
            await self.session.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This account already has a pension record",
            ) from None
        await self.session.refresh(pension)

        # Seed the estimate history so net-worth points before any later edit
        # use this original estimate.
        await self._record_estimate(pension, datetime.now(UTC).date())

        await self.audit_repo.write(
            ctx=ctx,
            action="pension.created",
            entity_type="pension",
            entity_id=pension.id,
            new_value=_snapshot(pension, exclude=AUDIT_EXCLUDED_FIELDS),
        )
        return pension

    async def update(
        self, ctx: VisibilityContext, account_id: uuid.UUID, data: PensionAccountUpdate
    ) -> PensionAccount:
        await self.account_repo.get_by_id(ctx, account_id)  # RBAC check
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        pension = await self.pension_repo.get_by_account_id(account_id)
        if pension is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pension record not found"
            )

        prev = _snapshot(pension, exclude=AUDIT_EXCLUDED_FIELDS)

        # model_fields_set semantics: only update fields present in request body
        for field_name in data.model_fields_set:
            value = getattr(data, field_name)
            # cola_adjustment_rate and is_vested are NOT NULL in DB — guard against explicit null
            if field_name in ("cola_adjustment_rate", "is_vested") and value is None:
                continue
            if field_name == "plan_name":
                pension.plan_name_enc = encrypt(value) if value else None
            elif field_name == "administrator":
                pension.administrator_enc = encrypt(value) if value else None
            elif field_name == "notes":
                pension.notes_enc = encrypt(value) if value else None
            else:
                setattr(pension, field_name, value)

        pension.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(pension)

        curr = _snapshot(pension, exclude=AUDIT_EXCLUDED_FIELDS)
        changed_keys = {k for k in set(prev) | set(curr) if prev.get(k) != curr.get(k)}

        # Record a new estimate snapshot only when a present-value input changed,
        # so historical net-worth points keep their original valuation.
        if any(prev.get(f) != curr.get(f) for f in _PV_FIELDS):
            await self._record_estimate(pension, datetime.now(UTC).date())

        await self.audit_repo.write(
            ctx=ctx,
            action="pension.updated",
            entity_type="pension",
            entity_id=pension.id,
            previous_value={k: prev.get(k) for k in changed_keys},
            new_value={k: curr.get(k) for k in changed_keys},
        )
        return pension
