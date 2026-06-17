import uuid
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_account(
        self,
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
        q = select(Transaction).where(Transaction.account_id == account_id)
        q = self._apply_filters(
            q,
            from_date=from_date,
            to_date=to_date,
            category_id=category_id,
            is_reviewed=is_reviewed,
            is_transfer=is_transfer,
            real_estate_property_id=real_estate_property_id,
            search=search,
        )

        count_q = select(func.count()).select_from(q.order_by(None).subquery())
        total = (await self.session.execute(count_q)).scalar_one()

        q = q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total

    def _apply_filters(
        self,
        q: Select[tuple[Transaction]],
        *,
        from_date: date | None,
        to_date: date | None,
        category_id: uuid.UUID | None,
        is_reviewed: bool | None,
        is_transfer: bool | None,
        real_estate_property_id: uuid.UUID | None,
        search: str | None,
    ) -> Select[tuple[Transaction]]:
        if from_date is not None:
            q = q.where(Transaction.transaction_date >= from_date)
        if to_date is not None:
            q = q.where(Transaction.transaction_date <= to_date)
        if category_id is not None:
            q = q.where(Transaction.category_id == category_id)
        if is_reviewed is not None:
            q = q.where(Transaction.is_reviewed == is_reviewed)
        if is_transfer is not None:
            q = q.where(Transaction.is_transfer == is_transfer)
        if real_estate_property_id is not None:
            q = q.where(Transaction.real_estate_property_id == real_estate_property_id)
        if search:
            q = q.where(Transaction.payee_normalized.ilike(f"%{search}%"))
        return q

    async def get_by_id(self, transaction_id: uuid.UUID) -> Transaction | None:
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()
