import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pii import redact_pii
from app.core.visibility import VisibilityContext
from app.db.models.staging_transaction import StagingTransaction
from app.repositories.account import AccountRepository
from app.schemas.staging import (
    ImportStagingRequest,
    ImportStagingResponse,
    StagingRowError,
)
from app.services.dedupe import build_dedupe_index


class StagingService:
    """Accept pre-parsed ingest rows into the staging table, synchronously.

    No ARQ hop (eng review, cross-model tension 1): the CLI already parsed, so
    this is dedupe + bulk insert, fast enough to do in-request. The server
    re-redacts PII (it is the trust boundary, not the CLI) and dedupes against
    committed AND staged rows via one prefetched index.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)

    async def stage(
        self, ctx: VisibilityContext, account_id: uuid.UUID, request: ImportStagingRequest
    ) -> ImportStagingResponse:
        # Visibility + write authority are enforced by the route dependency
        # (require_import_write_ctx); get_by_id additionally confirms the account
        # is visible to this context and 404s otherwise.
        await self.account_repo.get_by_id(ctx, account_id)

        batch_id = request.batch_id or uuid.uuid4()
        now = datetime.now(UTC)
        dedupe = await build_dedupe_index(
            self.session, account_id, [r.transaction_date for r in request.rows]
        )

        staged = 0
        skipped = 0
        errors: list[StagingRowError] = []

        for index, row in enumerate(request.rows):
            payee = redact_pii(row.payee_raw)
            memo = redact_pii(row.memo)

            if dedupe.is_duplicate(row.transaction_date, row.amount, payee, row.external_id):
                skipped += 1
                continue

            try:
                # Per-row savepoint so one bad row can't poison the whole batch.
                async with self.session.begin_nested():
                    self.session.add(
                        StagingTransaction(
                            account_id=account_id,
                            batch_id=batch_id,
                            transaction_date=row.transaction_date,
                            amount=row.amount,
                            payee_raw=payee,
                            memo=memo,
                            external_id=row.external_id,
                            source=row.source,
                            confidence=row.confidence,
                            created_at=now,
                        )
                    )
                    await self.session.flush()
            except IntegrityError:
                # DB-level idempotency backstop: the partial unique index on
                # (account_id, external_id) caught a concurrent-retry duplicate
                # that the in-memory index didn't see. The savepoint rolled it
                # back; count it as a skip, not a failure.
                skipped += 1
                continue
            except Exception as exc:
                errors.append(StagingRowError(index=index, error=str(exc)))
                continue

            staged += 1
            dedupe.remember(row.transaction_date, row.amount, payee, row.external_id)

        await self.session.commit()
        return ImportStagingResponse(
            batch_id=batch_id,
            staged=staged,
            skipped_duplicate=skipped,
            failed=len(errors),
            errors=errors,
        )

    async def list_batch(
        self, ctx: VisibilityContext, account_id: uuid.UUID, batch_id: uuid.UUID
    ) -> list[StagingTransaction]:
        await self.account_repo.get_by_id(ctx, account_id)
        result = await self.session.execute(
            select(StagingTransaction)
            .where(
                StagingTransaction.account_id == account_id,
                StagingTransaction.batch_id == batch_id,
            )
            .order_by(StagingTransaction.transaction_date)
        )
        return list(result.scalars().all())
