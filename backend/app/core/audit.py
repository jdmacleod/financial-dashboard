import uuid
from datetime import datetime
from decimal import Decimal
from functools import wraps
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext

ENCRYPTED_FIELDS = frozenset(
    {
        "institution_name_enc",
        "account_number_enc",
        "routing_number_enc",
        "address_enc",
        "notes_enc",
    }
)


def _snapshot(obj: Any, exclude: frozenset = frozenset()) -> dict:
    if obj is None:
        return {}
    result = {}
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        val = getattr(obj, col.name)
        if isinstance(val, uuid.UUID):
            val = str(val)
        elif isinstance(val, datetime):
            val = val.isoformat()
        elif isinstance(val, Decimal):
            val = str(val)
        result[col.name] = val
    return result


def _diff(prev: dict, curr: dict) -> tuple[dict, dict]:
    changed = {k for k in set(prev) | set(curr) if prev.get(k) != curr.get(k)}
    return {k: prev.get(k) for k in changed}, {k: curr.get(k) for k in changed}


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def write(
        self,
        ctx: VisibilityContext,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        previous_value: dict | None = None,
        new_value: dict | None = None,
    ) -> None:
        from app.db.models.audit_log import AuditLog

        row = AuditLog(
            household_id=ctx.household_id,
            user_id=ctx.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_value=previous_value,
            new_value=new_value,
            ip_address=ctx.ip_address,
        )
        self.session.add(row)
        await self.session.flush()

    async def write_auth_event(
        self,
        household_id: uuid.UUID,
        user_id: uuid.UUID | None,
        action: str,
        ip_address: str | None = None,
        new_value: dict | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        from app.db.models.audit_log import AuditLog

        row = AuditLog(
            household_id=household_id,
            user_id=user_id,
            action=action,
            entity_type="auth",
            entity_id=entity_id,
            new_value=new_value,
            ip_address=ip_address,
        )
        self.session.add(row)
        await self.session.flush()


def audit(action: str, entity_type: str):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(self, ctx: VisibilityContext, *args, **kwargs):
            result = await fn(self, ctx, *args, **kwargs)

            prev = getattr(self, "_prev_snapshot", None)
            if prev is not None:
                try:
                    del self._prev_snapshot
                except AttributeError:
                    pass

            entity_id = getattr(result, "id", None)
            curr = _snapshot(result, exclude=ENCRYPTED_FIELDS) if result is not None else None

            if prev is not None and curr is not None:
                diff_prev, diff_curr = _diff(prev, curr)
            else:
                diff_prev, diff_curr = None, curr

            await self.audit_repo.write(
                ctx=ctx,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                previous_value=diff_prev,
                new_value=diff_curr,
            )
            return result

        return wrapper

    return decorator
