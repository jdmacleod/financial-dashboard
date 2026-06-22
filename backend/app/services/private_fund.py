import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.capital_commitment import CapitalCommitment
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository


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
