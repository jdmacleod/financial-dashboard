import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot, audit
from app.core.encryption import decrypt, encrypt
from app.core.visibility import VisibilityContext
from app.db.models.capital_commitment import CapitalCommitment
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.schemas.capital_commitment import (
    CapitalCommitmentCreate,
    CapitalCommitmentResponse,
    CapitalCommitmentUpdate,
)


@dataclass
class CapitalCallInput:
    capital_commitment_id: uuid.UUID
    funding_account_id: uuid.UUID  # account the call is drawn from
    call_amount: Decimal
    call_date: date
    category_id: uuid.UUID | None = None


class PrivateFundService:
    """Records private-fund capital calls against an outstanding commitment.

    A capital call increases `called_to_date` and posts a `capital_call`
    transfer out of the funding account, atomically through the @audit method
    (spec Phase A AC #7). The audit snapshot excludes the encrypted
    `fund_name_enc` column (AC #6/#8).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.account_repo = AccountRepository(session)

    @staticmethod
    def to_response(c: CapitalCommitment) -> CapitalCommitmentResponse:
        return CapitalCommitmentResponse(
            id=c.id,
            household_id=c.household_id,
            fund_name=decrypt(c.fund_name_enc),
            committed_amount=c.committed_amount,
            called_to_date=c.called_to_date,
            nav_account_id=c.nav_account_id,
            vintage_year=c.vintage_year,
            created_at=c.created_at,
        )

    async def list_commitments(self, ctx: VisibilityContext) -> list[CapitalCommitmentResponse]:
        """Capital commitments for the household, with fund_name decrypted."""
        result = await self.session.execute(
            select(CapitalCommitment)
            .where(CapitalCommitment.household_id == ctx.household_id)
            .order_by(CapitalCommitment.vintage_year)
        )
        return [self.to_response(c) for c in result.scalars().all()]

    @audit("capital_commitment.created", "capital_commitment")
    async def create(
        self, ctx: VisibilityContext, data: CapitalCommitmentCreate
    ) -> CapitalCommitment:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        # NAV account must be visible to this context.
        await self.account_repo.get_by_id(ctx, data.nav_account_id)
        commitment = CapitalCommitment(
            household_id=ctx.household_id,
            fund_name_enc=encrypt(data.fund_name),
            committed_amount=data.committed_amount,
            called_to_date=data.called_to_date,
            nav_account_id=data.nav_account_id,
            vintage_year=data.vintage_year,
            created_at=datetime.now(UTC),
        )
        self.session.add(commitment)
        await self.session.flush()
        await self.session.refresh(commitment)
        return commitment

    @audit("capital_commitment.updated", "capital_commitment")
    async def update(
        self, ctx: VisibilityContext, commitment_id: uuid.UUID, data: CapitalCommitmentUpdate
    ) -> CapitalCommitment:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        commitment = await self._get_commitment(ctx, commitment_id)
        # Encrypted fund_name_enc excluded from the audit snapshot (CLAUDE.md #4).
        self._prev_snapshot = _snapshot(commitment, exclude=AUDIT_EXCLUDED_FIELDS)
        if data.fund_name is not None:
            commitment.fund_name_enc = encrypt(data.fund_name)
        if data.committed_amount is not None:
            commitment.committed_amount = data.committed_amount
        if data.called_to_date is not None:
            commitment.called_to_date = data.called_to_date
        if data.nav_account_id is not None:
            await self.account_repo.get_by_id(ctx, data.nav_account_id)
            commitment.nav_account_id = data.nav_account_id
        if data.vintage_year is not None:
            commitment.vintage_year = data.vintage_year
        await self.session.flush()
        await self.session.refresh(commitment)
        return commitment

    async def delete(self, ctx: VisibilityContext, commitment_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        commitment = await self._get_commitment(ctx, commitment_id)
        prev = _snapshot(commitment, exclude=AUDIT_EXCLUDED_FIELDS)
        await self.session.delete(commitment)
        await self.session.flush()
        await self.audit_repo.write(
            ctx=ctx,
            action="capital_commitment.deleted",
            entity_type="capital_commitment",
            entity_id=commitment_id,
            previous_value=prev,
        )

    async def _get_commitment(
        self, ctx: VisibilityContext, commitment_id: uuid.UUID
    ) -> CapitalCommitment:
        result = await self.session.execute(
            select(CapitalCommitment).where(
                CapitalCommitment.id == commitment_id,
                CapitalCommitment.household_id == ctx.household_id,
            )
        )
        commitment = result.scalar_one_or_none()
        if commitment is None:
            raise HTTPException(status_code=404, detail="Capital commitment not found")
        return commitment

    @audit("private_fund.capital_call", "capital_commitment")
    async def record_capital_call(
        self, ctx: VisibilityContext, data: CapitalCallInput
    ) -> CapitalCommitment:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await self.account_repo.get_by_id(ctx, data.funding_account_id)
        commitment = await self._get_commitment(ctx, data.capital_commitment_id)

        # Snapshot before mutation so @audit records the called_to_date diff
        # (encrypted fund_name_enc excluded by AUDIT_EXCLUDED_FIELDS).
        self._prev_snapshot = _snapshot(commitment, exclude=AUDIT_EXCLUDED_FIELDS)

        now = datetime.now(UTC)
        commitment.called_to_date = commitment.called_to_date + data.call_amount

        self.session.add(
            Transaction(
                account_id=data.funding_account_id,
                transaction_date=data.call_date,
                amount=-data.call_amount,
                payee_normalized="Capital call",
                memo="Private-fund capital call",
                category_id=data.category_id,
                is_transfer=True,
                tags=["capital_call"],
                source="manual",
                is_reviewed=True,
                created_at=now,
                updated_at=now,
            )
        )
        await self.session.flush()
        await self.session.refresh(commitment)
        return commitment
