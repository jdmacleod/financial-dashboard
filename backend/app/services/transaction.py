import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.transaction import BulkCategorizeRequest, TransactionCreate, TransactionUpdate


def _assert_writable(ctx: VisibilityContext, account: Account) -> None:
    if not ctx.can_write:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if not ctx.is_primary and account.owner_member_id not in (None, ctx.member_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partners may only manage transactions on their own or joint accounts",
        )


class TransactionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)
        self.transaction_repo = TransactionRepository(session)
        self.audit_repo = AuditRepository(session)

    async def list_for_account(
        self,
        ctx: VisibilityContext,
        account_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        category_id: uuid.UUID | None = None,
        is_reviewed: bool | None = None,
        is_transfer: bool | None = None,
        real_estate_property_id: uuid.UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Transaction], int]:
        await self.account_repo.get_by_id(ctx, account_id)
        return await self.transaction_repo.list_for_account(
            account_id,
            from_date=from_date,
            to_date=to_date,
            category_id=category_id,
            is_reviewed=is_reviewed,
            is_transfer=is_transfer,
            real_estate_property_id=real_estate_property_id,
            search=search,
            page=page,
            page_size=page_size,
        )

    async def _get_visible_or_404(
        self, ctx: VisibilityContext, transaction_id: uuid.UUID
    ) -> tuple[Transaction, Account]:
        transaction = await self.transaction_repo.get_by_id(transaction_id)
        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
            )
        account = await self.account_repo.get_by_id(ctx, transaction.account_id)
        return transaction, account

    async def get(self, ctx: VisibilityContext, transaction_id: uuid.UUID) -> Transaction:
        transaction, _ = await self._get_visible_or_404(ctx, transaction_id)
        return transaction

    async def create(
        self, ctx: VisibilityContext, account_id: uuid.UUID, data: TransactionCreate
    ) -> Transaction:
        account = await self.account_repo.get_by_id(ctx, account_id)
        _assert_writable(ctx, account)

        # Fill an unset category from a matching rule (fill-empty only — an
        # explicit category from the caller is never overridden).
        category_id = data.category_id
        if category_id is None:
            from app.services.categorization import CategorizationService

            category_id = await CategorizationService(self.session).match(
                ctx.household_id, data.payee_normalized
            )

        now = datetime.now(UTC)
        transaction = Transaction(
            account_id=account_id,
            real_estate_property_id=data.real_estate_property_id,
            transaction_date=data.transaction_date,
            amount=data.amount,
            payee_normalized=data.payee_normalized,
            memo=data.memo,
            category_id=category_id,
            is_transfer=data.is_transfer,
            tags=[],
            source="manual",
            created_at=now,
            updated_at=now,
        )
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction)

        await self.audit_repo.write(
            ctx=ctx,
            action="transaction.created",
            entity_type="transaction",
            entity_id=transaction.id,
            new_value=_snapshot(transaction),
        )
        return transaction

    async def update(
        self, ctx: VisibilityContext, transaction_id: uuid.UUID, data: TransactionUpdate
    ) -> Transaction:
        transaction, account = await self._get_visible_or_404(ctx, transaction_id)
        _assert_writable(ctx, account)

        prev = _snapshot(transaction)
        category_changed = (
            data.category_id is not None and data.category_id != transaction.category_id
        )

        if data.transaction_date is not None:
            transaction.transaction_date = data.transaction_date
        if data.amount is not None:
            transaction.amount = data.amount
        if data.payee_normalized is not None:
            transaction.payee_normalized = data.payee_normalized
        if "memo" in data.model_fields_set:
            transaction.memo = data.memo
        if data.category_id is not None:
            transaction.category_id = data.category_id
            transaction.is_reviewed = True
        if data.is_transfer is not None:
            transaction.is_transfer = data.is_transfer
        if data.real_estate_property_id is not None:
            transaction.real_estate_property_id = data.real_estate_property_id
        if data.is_reviewed is not None:
            transaction.is_reviewed = data.is_reviewed

        transaction.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(transaction)

        curr = _snapshot(transaction)
        changed_keys = {k for k in set(prev) | set(curr) if prev.get(k) != curr.get(k)}
        action = "transaction.category_changed" if category_changed else "transaction.updated"
        await self.audit_repo.write(
            ctx=ctx,
            action=action,
            entity_type="transaction",
            entity_id=transaction.id,
            previous_value={k: prev.get(k) for k in changed_keys},
            new_value={k: curr.get(k) for k in changed_keys},
        )
        return transaction

    async def delete(self, ctx: VisibilityContext, transaction_id: uuid.UUID) -> None:
        transaction, account = await self._get_visible_or_404(ctx, transaction_id)
        _assert_writable(ctx, account)

        prev = _snapshot(transaction)
        await self.session.delete(transaction)
        await self.session.flush()

        await self.audit_repo.write(
            ctx=ctx,
            action="transaction.deleted",
            entity_type="transaction",
            entity_id=transaction_id,
            previous_value=prev,
        )

    async def bulk_categorize(
        self, ctx: VisibilityContext, account_id: uuid.UUID, data: BulkCategorizeRequest
    ) -> list[Transaction]:
        account = await self.account_repo.get_by_id(ctx, account_id)
        _assert_writable(ctx, account)

        updated: list[Transaction] = []
        now = datetime.now(UTC)
        for transaction_id in data.transaction_ids:
            transaction = await self.transaction_repo.get_by_id(transaction_id)
            if transaction is None or transaction.account_id != account_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
                )
            prev_category_id = transaction.category_id
            transaction.category_id = data.category_id
            transaction.is_reviewed = True
            transaction.updated_at = now
            await self.session.flush()

            await self.audit_repo.write(
                ctx=ctx,
                action="transaction.category_changed",
                entity_type="transaction",
                entity_id=transaction.id,
                previous_value={"category_id": str(prev_category_id) if prev_category_id else None},
                new_value={"category_id": str(data.category_id)},
            )
            updated.append(transaction)
        return updated
