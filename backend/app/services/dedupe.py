"""Shared transaction de-duplication, batch-prefetched.

Extracted so both the ingest staging path (T3) and the file-upload worker (T4/T5)
dedupe identically. The old worker ran one or two SELECTs PER ROW
(``_is_duplicate``); a 200-row statement was ~200 queries, and adding a staging
check would double it (eng review, Perf Issue 7). Instead we prefetch the
account's candidate rows ONCE over the batch's date window — bounded so a
long-history account never pulls its whole ledger into memory — and match in
memory.

A row is a duplicate when an existing row (committed OR already-staged) shares its
``external_id``, or — when there is no external_id — shares date + amount and a
fuzzy-equal payee.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.staging_transaction import StagingTransaction
from app.db.models.transaction import Transaction

FUZZY_MATCH_THRESHOLD = 0.8
# Pad the prefetch window so a transaction whose post/booking date drifted a few
# days still matches an existing row.
_WINDOW_PAD_DAYS = 3


@dataclass(frozen=True)
class _Candidate:
    transaction_date: date
    amount: Decimal
    payee_raw: str | None


@dataclass
class DedupeIndex:
    external_ids: set[str] = field(default_factory=set)
    by_date_amount: dict[tuple[date, Decimal], list[_Candidate]] = field(default_factory=dict)

    def _add(
        self,
        transaction_date: date,
        amount: Decimal,
        payee_raw: str | None,
        external_id: str | None,
    ) -> None:
        if external_id:
            self.external_ids.add(external_id)
        key = (transaction_date, amount)
        self.by_date_amount.setdefault(key, []).append(
            _Candidate(transaction_date, amount, payee_raw)
        )

    def is_duplicate(
        self,
        transaction_date: date,
        amount: Decimal,
        payee_raw: str | None,
        external_id: str | None,
    ) -> bool:
        if external_id and external_id in self.external_ids:
            return True
        for cand in self.by_date_amount.get((transaction_date, amount), ()):
            ratio = SequenceMatcher(None, cand.payee_raw or "", payee_raw or "").ratio()
            if ratio > FUZZY_MATCH_THRESHOLD:
                return True
        return False

    def remember(
        self,
        transaction_date: date,
        amount: Decimal,
        payee_raw: str | None,
        external_id: str | None,
    ) -> None:
        """Record a row just accepted in this batch so later rows in the SAME
        batch dedupe against it too (intra-batch duplicates)."""
        self._add(transaction_date, amount, payee_raw, external_id)


async def build_dedupe_index(
    session: AsyncSession,
    account_id: UUID,
    dates: list[date],
) -> DedupeIndex:
    """Prefetch committed + staged rows for ``account_id`` over the date window
    spanned by ``dates`` (padded), into a single in-memory index."""
    index = DedupeIndex()
    if not dates:
        return index
    start = min(dates) - timedelta(days=_WINDOW_PAD_DAYS)
    end = max(dates) + timedelta(days=_WINDOW_PAD_DAYS)

    committed = await session.execute(
        select(
            Transaction.transaction_date,
            Transaction.amount,
            Transaction.payee_raw,
            Transaction.external_id,
        ).where(
            Transaction.account_id == account_id,
            Transaction.transaction_date.between(start, end),
        )
    )
    for row in committed:
        index._add(row[0], row[1], row[2], row[3])

    staged = await session.execute(
        select(
            StagingTransaction.transaction_date,
            StagingTransaction.amount,
            StagingTransaction.payee_raw,
            StagingTransaction.external_id,
        ).where(
            StagingTransaction.account_id == account_id,
            StagingTransaction.transaction_date.between(start, end),
        )
    )
    for row in staged:
        index._add(row[0], row[1], row[2], row[3])

    return index
