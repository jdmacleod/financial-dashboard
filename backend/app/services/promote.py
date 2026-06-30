import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.staging_transaction import StagingTransaction
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository

TRANSFER_WINDOW_DAYS = 3


class PromoteService:
    """Promote reviewed staging rows into real transactions.

    This is the single auditable boundary where ingested data becomes truth.
    The @audit decorator snapshots one entity, so a batch promote writes one
    audit row PER promoted transaction by hand (eng review, outside-voice #3).
    Transfer pairing runs AFTER promote, across the household, and is itself
    audited (outside-voice #4 — the old worker mutated committed rows silently).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.account_repo = AccountRepository(session)

    async def promote_batch(
        self, ctx: VisibilityContext, account_id: uuid.UUID, batch_id: uuid.UUID
    ) -> int:
        await self.account_repo.get_by_id(ctx, account_id)  # visibility / 404

        result = await self.session.execute(
            select(StagingTransaction).where(
                StagingTransaction.account_id == account_id,
                StagingTransaction.batch_id == batch_id,
            )
        )
        staged = list(result.scalars().all())
        now = datetime.now(UTC)
        promoted: list[Transaction] = []

        for s in staged:
            txn = Transaction(
                account_id=s.account_id,
                transaction_date=s.transaction_date,
                post_date=s.post_date,
                amount=s.amount,
                payee_raw=s.payee_raw,
                payee_normalized=s.payee_raw,
                memo=s.memo,
                tags=[],
                source=s.source,
                confidence=s.confidence,
                external_id=s.external_id,
                is_reviewed=True,
                created_at=now,
                updated_at=now,
            )
            self.session.add(txn)
            await self.session.flush()
            await self.audit_repo.write(
                ctx=ctx,
                action="transaction.created",
                entity_type="transaction",
                entity_id=txn.id,
                previous_value=None,
                new_value=_snapshot(txn, exclude=AUDIT_EXCLUDED_FIELDS),
            )
            promoted.append(txn)
            await self.session.delete(s)

        await self.session.flush()

        for txn in promoted:
            candidate = await self._find_transfer_candidate(ctx.household_id, txn)
            if candidate is not None:
                await self._pair_transfer(ctx, txn, candidate)

        await self.session.commit()
        return len(promoted)

    async def _find_transfer_candidate(
        self, household_id: uuid.UUID, transaction: Transaction
    ) -> Transaction | None:
        window_start = transaction.transaction_date - timedelta(days=TRANSFER_WINDOW_DAYS)
        window_end = transaction.transaction_date + timedelta(days=TRANSFER_WINDOW_DAYS)
        result = await self.session.execute(
            select(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Account.household_id == household_id,
                Transaction.account_id != transaction.account_id,
                Transaction.is_transfer.is_(False),
                Transaction.amount == -transaction.amount,
                Transaction.transaction_date.between(window_start, window_end),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _transfer_category_id(self, household_id: uuid.UUID) -> uuid.UUID | None:
        result = await self.session.execute(
            select(Category.id).where(
                Category.household_id == household_id,
                Category.name == "Transfer",
                Category.is_system.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _pair_transfer(self, ctx: VisibilityContext, a: Transaction, b: Transaction) -> None:
        pair_id = uuid.uuid4()
        category_id = await self._transfer_category_id(ctx.household_id)
        now = datetime.now(UTC)
        for txn in (a, b):
            prev = _snapshot(txn, exclude=AUDIT_EXCLUDED_FIELDS)
            txn.is_transfer = True
            txn.transfer_pair_id = pair_id
            if category_id is not None:
                txn.category_id = category_id
            txn.updated_at = now
            await self.session.flush()
            # Audit the mutation of an already-committed row (the old worker did
            # this silently); record only the fields the pairing changed.
            await self.audit_repo.write(
                ctx=ctx,
                action="transaction.transfer_paired",
                entity_type="transaction",
                entity_id=txn.id,
                previous_value={
                    "is_transfer": prev["is_transfer"],
                    "transfer_pair_id": prev["transfer_pair_id"],
                    "category_id": prev["category_id"],
                },
                new_value={
                    "is_transfer": True,
                    "transfer_pair_id": str(pair_id),
                    "category_id": str(category_id) if category_id else None,
                },
            )
