import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.import_job import ImportJob
from app.db.models.transaction import Transaction
from app.importers import csv_importer, ofx_importer
from app.services.dedupe import build_dedupe_index

TRANSFER_WINDOW_DAYS = 3


async def _find_transfer_candidate(
    session: AsyncSession, household_id: uuid.UUID, transaction: Transaction
) -> Transaction | None:
    window_start = transaction.transaction_date - timedelta(days=TRANSFER_WINDOW_DAYS)
    window_end = transaction.transaction_date + timedelta(days=TRANSFER_WINDOW_DAYS)
    result = await session.execute(
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


async def _transfer_category_id(session: AsyncSession, household_id: uuid.UUID) -> uuid.UUID | None:
    result = await session.execute(
        select(Category.id).where(
            Category.household_id == household_id,
            Category.name == "Transfer",
            Category.is_system.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def _pair_transfer(
    session: AsyncSession, household_id: uuid.UUID, a: Transaction, b: Transaction
) -> None:
    pair_id = uuid.uuid4()
    category_id = await _transfer_category_id(session, household_id)
    for txn in (a, b):
        txn.is_transfer = True
        txn.transfer_pair_id = pair_id
        if category_id is not None:
            txn.category_id = category_id
        txn.updated_at = datetime.now(UTC)


async def run_import_job(
    ctx: dict[str, Any],
    job_id: str,
    content: bytes,
    fmt: str,
    mapping: dict[str, str] | None,
    household_id: str,
) -> None:
    session_factory = ctx["db"]
    async with session_factory() as session:
        result = await session.execute(select(ImportJob).where(ImportJob.id == uuid.UUID(job_id)))
        job = result.scalar_one()
        job.status = "processing"
        job.updated_at = datetime.now(UTC)
        await session.commit()

        try:
            rows = (
                csv_importer.parse_rows(content, mapping or {})
                if fmt == "csv"
                else ofx_importer.parse(content)
            )

            imported: list[Transaction] = []
            records_skipped = 0
            now = datetime.now(UTC)
            # Prefetch existing rows once (committed + staged) instead of a
            # per-row duplicate query — kills the N+1 (eng review, Perf Issue 7).
            dedupe = await build_dedupe_index(
                session, job.account_id, [r.transaction_date for r in rows]
            )
            for row in rows:
                if dedupe.is_duplicate(
                    row.transaction_date, row.amount, row.payee_raw, row.external_id
                ):
                    records_skipped += 1
                    continue
                transaction = Transaction(
                    account_id=job.account_id,
                    transaction_date=row.transaction_date,
                    post_date=row.post_date,
                    amount=row.amount,
                    payee_raw=row.payee_raw,
                    payee_normalized=row.payee_raw,
                    memo=row.memo,
                    tags=[],
                    source=fmt,
                    import_job_id=job.id,
                    external_id=row.external_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(transaction)
                await session.flush()
                imported.append(transaction)
                # Intra-batch dedupe: later rows see this one too.
                dedupe.remember(row.transaction_date, row.amount, row.payee_raw, row.external_id)

            household_uuid = uuid.UUID(household_id)
            for transaction in imported:
                candidate = await _find_transfer_candidate(session, household_uuid, transaction)
                if candidate is not None:
                    await _pair_transfer(session, household_uuid, transaction, candidate)
                    await session.flush()

            job.status = "complete"
            job.records_found = len(rows)
            job.records_imported = len(imported)
            job.records_skipped = records_skipped
            job.updated_at = datetime.now(UTC)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            job.status = "failed"
            job.error_message = str(exc)
            job.updated_at = datetime.now(UTC)
            await session.commit()
