import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, audit
from app.core.visibility import VisibilityContext
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository


@dataclass
class SblocPostingInput:
    account_id: uuid.UUID  # the revolving sbloc/margin account
    amount: Decimal  # positive magnitude; sign is applied by the method
    posting_date: date
    category_id: uuid.UUID | None = None


class CreditLineService:
    """Posts draws and interest against a revolving credit line (SBLOC / margin).

    Revolving accounts carry a negative balance (a liability). A draw and
    accrued interest both increase the magnitude of that liability, so each is
    posted as a negative-amount transaction; a paydown is the positive inverse.
    Each posting goes through an @audit method (spec Phase A AC #7).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.account_repo = AccountRepository(session)

    async def _post(
        self,
        ctx: VisibilityContext,
        data: SblocPostingInput,
        *,
        is_transfer: bool,
        payee: str,
        memo: str,
        tag: str,
    ) -> Transaction:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await self.account_repo.get_by_id(ctx, data.account_id)

        now = datetime.now(UTC)
        txn = Transaction(
            account_id=data.account_id,
            transaction_date=data.posting_date,
            amount=-abs(data.amount),
            payee_normalized=payee,
            memo=memo,
            category_id=data.category_id,
            is_transfer=is_transfer,
            tags=[tag],
            source="manual",
            is_reviewed=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(txn)
        await self.session.flush()
        await self.session.refresh(txn)
        return txn

    @audit("credit_line.sbloc_draw", "transaction")
    async def record_sbloc_draw(
        self, ctx: VisibilityContext, data: SblocPostingInput
    ) -> Transaction:
        return await self._post(
            ctx,
            data,
            is_transfer=True,
            payee="SBLOC draw",
            memo="Securities-based line of credit draw",
            tag="sbloc_draw",
        )

    @audit("credit_line.sbloc_interest", "transaction")
    async def record_sbloc_interest(
        self, ctx: VisibilityContext, data: SblocPostingInput
    ) -> Transaction:
        return await self._post(
            ctx,
            data,
            is_transfer=False,
            payee="SBLOC interest",
            memo="Securities-based line of credit interest",
            tag="sbloc_interest",
        )
