import uuid
from collections.abc import Callable, Coroutine
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from typing import Any, TypeVar

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext

ENCRYPTED_FIELDS = frozenset(
    {
        "institution_name_enc",
        "account_number_enc",
        "routing_number_enc",
        "address_enc",
        "notes_enc",
        "plan_name_enc",
        "administrator_enc",
        "name_enc",
        "fund_name_enc",
    }
)

# Auth secrets are not AES-encrypted PII, but must never land in the audit
# log either — same rationale as ENCRYPTED_FIELDS (CLAUDE.md rule #4).
AUTH_SECRET_FIELDS = frozenset({"hashed_password", "refresh_token_hash"})

AUDIT_EXCLUDED_FIELDS = ENCRYPTED_FIELDS | AUTH_SECRET_FIELDS

_F = TypeVar("_F", bound=Callable[..., Coroutine[Any, Any, Any]])


def _snapshot(obj: Any, exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    if obj is None:
        return {}
    result: dict[str, Any] = {}
    mapper = sa_inspect(obj).mapper
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        # Read through the mapped attribute key, which can differ from the DB
        # column name (e.g. InsurancePolicy.policy_metadata maps to column
        # "metadata"). Using col.name directly would collide with SQLAlchemy's
        # declarative `metadata` attribute. Keep col.name as the snapshot key
        # for stable audit output.
        attr = mapper.get_property_by_column(col).key
        val = getattr(obj, attr)
        if isinstance(val, uuid.UUID):
            val = str(val)
        elif isinstance(val, datetime | date):
            val = val.isoformat()
        elif isinstance(val, Decimal):
            val = str(val)
        result[col.name] = val
    return result


def _diff(prev: dict[str, Any], curr: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    changed = {k for k in set(prev) | set(curr) if prev.get(k) != curr.get(k)}
    return {k: prev.get(k) for k in changed}, {k: curr.get(k) for k in changed}


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def write(
        self,
        ctx: VisibilityContext,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        previous_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
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
        new_value: dict[str, Any] | None = None,
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


def audit(action: str, entity_type: str) -> Callable[[_F], _F]:
    def decorator(fn: _F) -> _F:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            self = args[0]
            ctx: VisibilityContext = args[1]
            result = await fn(*args, **kwargs)

            prev: dict[str, Any] | None = getattr(self, "_prev_snapshot", None)
            self.__dict__.pop("_prev_snapshot", None)

            entity_id: uuid.UUID | None = getattr(result, "id", None)
            curr = _snapshot(result, exclude=AUDIT_EXCLUDED_FIELDS) if result is not None else None

            diff_prev: dict[str, Any] | None
            diff_curr: dict[str, Any] | None
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

        return wrapper  # type: ignore[return-value]

    return decorator
