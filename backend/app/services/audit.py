import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.audit_log import AuditLog
from app.db.models.member import HouseholdMember
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.repositories.account import AccountRepository
from app.schemas.audit import AuditLogEntryResponse, PaginatedAuditLog


class AuditLogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)

    async def list_entries(
        self,
        ctx: VisibilityContext,
        *,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        member_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedAuditLog:
        await self._authorize(ctx, entity_type, entity_id)

        query = select(AuditLog).where(AuditLog.household_id == ctx.household_id)
        if entity_type is not None:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if member_id is not None:
            user_subq = select(User.id).where(User.member_id == member_id).scalar_subquery()
            query = query.where(AuditLog.user_id == user_subq)
        if from_date is not None:
            query = query.where(AuditLog.created_at >= from_date)
        if to_date is not None:
            query = query.where(AuditLog.created_at <= to_date)
        if entity_type == "auth" and not ctx.is_primary:
            query = query.where(AuditLog.user_id == ctx.user_id)

        total = (
            await self.session.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()

        is_record_history = entity_type is not None and entity_id is not None
        order = AuditLog.created_at.asc() if is_record_history else AuditLog.created_at.desc()
        rows = (
            (
                await self.session.execute(
                    query.order_by(order).offset((page - 1) * page_size).limit(page_size)
                )
            )
            .scalars()
            .all()
        )

        items = await self._enrich_batch(rows)
        return PaginatedAuditLog(items=items, page=page, page_size=page_size, total=total)

    async def _authorize(
        self, ctx: VisibilityContext, entity_type: str | None, entity_id: uuid.UUID | None
    ) -> None:
        if entity_type == "auth":
            return
        if entity_type is not None and entity_id is not None:
            await self._authorize_entity(ctx, entity_type, entity_id)
            return
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    async def _authorize_entity(
        self, ctx: VisibilityContext, entity_type: str, entity_id: uuid.UUID
    ) -> None:
        if ctx.is_primary:
            return
        if entity_type == "transaction":
            transaction = await self.session.get(Transaction, entity_id)
            if transaction is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            await self.account_repo.get_by_id(ctx, transaction.account_id)
        elif entity_type == "account":
            await self.account_repo.get_by_id(ctx, entity_id)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    async def _enrich_batch(self, rows: Sequence[AuditLog]) -> list[AuditLogEntryResponse]:
        if not rows:
            return []

        # Batch user → member display_name lookups
        user_ids = {row.user_id for row in rows if row.user_id is not None}
        display_names: dict[uuid.UUID, str] = {}
        if user_ids:
            result = await self.session.execute(
                select(User.id, HouseholdMember.display_name)
                .join(HouseholdMember, User.member_id == HouseholdMember.id)
                .where(User.id.in_(user_ids))
            )
            display_names = {uid: name for uid, name in result.all()}  # noqa: C416

        # Batch entity context lookups grouped by type
        txn_ids = {
            row.entity_id for row in rows if row.entity_type == "transaction" and row.entity_id
        }
        acct_ids = {row.entity_id for row in rows if row.entity_type == "account" and row.entity_id}
        mem_ids = {row.entity_id for row in rows if row.entity_type == "member" and row.entity_id}

        txn_payees: dict[uuid.UUID, str] = {}
        acct_nicks: dict[uuid.UUID, str] = {}
        member_names: dict[uuid.UUID, str] = {}

        if txn_ids:
            result = await self.session.execute(
                select(Transaction.id, Transaction.payee_normalized, Transaction.payee_raw).where(
                    Transaction.id.in_(txn_ids)
                )
            )
            txn_payees = {tid: (pn or pr or "") for tid, pn, pr in result.all()}

        if acct_ids:
            result = await self.session.execute(
                select(Account.id, Account.nickname).where(Account.id.in_(acct_ids))
            )
            acct_nicks = {aid: nick for aid, nick in result.all()}  # noqa: C416

        if mem_ids:
            result = await self.session.execute(
                select(HouseholdMember.id, HouseholdMember.display_name).where(
                    HouseholdMember.id.in_(mem_ids)
                )
            )
            member_names = {mid: name for mid, name in result.all()}  # noqa: C416

        items = []
        for row in rows:
            context: dict[str, Any] = {}
            if row.entity_id is not None:
                if row.entity_type == "transaction" and row.entity_id in txn_payees:
                    context["payee"] = txn_payees[row.entity_id]
                elif row.entity_type == "member" and row.entity_id in member_names:
                    context["member_name"] = member_names[row.entity_id]
                elif row.entity_type == "account" and row.entity_id in acct_nicks:
                    context["nickname"] = acct_nicks[row.entity_id]

            items.append(
                AuditLogEntryResponse(
                    id=row.id,
                    action=row.action,
                    entity_type=row.entity_type,
                    entity_id=row.entity_id,
                    previous_value=row.previous_value,
                    new_value=row.new_value,
                    user_id=row.user_id,
                    user_display_name=display_names.get(row.user_id) if row.user_id else None,
                    context=context,
                    ip_address=str(row.ip_address) if row.ip_address is not None else None,
                    created_at=row.created_at,
                )
            )
        return items
