import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import settings
from app.core.security import create_access_token
from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User


def _ctx(role: str) -> VisibilityContext:
    return VisibilityContext(
        user_id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        role=role,
        household_id=uuid.uuid4(),
    )


@pytest.mark.parametrize(
    ("role", "is_primary", "can_export_executor", "can_write"),
    [
        ("primary", True, True, True),
        ("partner", False, False, True),
        ("dependent", False, False, False),
    ],
)
def test_visibility_context_properties(
    role: str, is_primary: bool, can_export_executor: bool, can_write: bool
) -> None:
    ctx = _ctx(role)
    assert ctx.is_primary is is_primary
    assert ctx.can_export_executor is can_export_executor
    assert ctx.can_write is can_write


def _fake_request() -> Request:
    return Request({"type": "http", "client": ("127.0.0.1", 12345), "headers": []})


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_get_visibility_ctx_happy_path(
    db_session: AsyncSession,
    primary_user: User,
    primary_member: HouseholdMember,
    household: Household,
) -> None:
    token = create_access_token(str(primary_user.id), str(primary_member.id), "primary")
    ctx = await get_visibility_ctx(_fake_request(), _bearer(token), db_session)
    assert ctx.user_id == primary_user.id
    assert ctx.member_id == primary_member.id
    assert ctx.role == "primary"
    assert ctx.household_id == household.id
    assert ctx.ip_address == "127.0.0.1"


async def test_get_visibility_ctx_garbled_token_401(db_session: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_visibility_ctx(_fake_request(), _bearer("not-a-real-token"), db_session)
    assert exc_info.value.status_code == 401


async def test_get_visibility_ctx_wrong_token_type_401(
    db_session: AsyncSession, primary_user: User
) -> None:
    from app.core.security import create_refresh_token

    token = create_refresh_token(str(primary_user.id))
    with pytest.raises(HTTPException) as exc_info:
        await get_visibility_ctx(_fake_request(), _bearer(token), db_session)
    assert exc_info.value.status_code == 401


async def test_get_visibility_ctx_no_household_403(
    db_session: AsyncSession, make_user: Any
) -> None:
    orphan_user = await make_user(None, "orphan@example.com")
    token = create_access_token(str(orphan_user.id), None, "partner")
    with pytest.raises(HTTPException) as exc_info:
        await get_visibility_ctx(_fake_request(), _bearer(token), db_session)
    assert exc_info.value.status_code == 403


async def test_get_visibility_ctx_missing_role_defaults_to_partner(
    db_session: AsyncSession, primary_user: User, primary_member: HouseholdMember
) -> None:
    payload = {
        "sub": str(primary_user.id),
        "member_id": str(primary_member.id),
        "type": "access",
        "exp": datetime.now(UTC).timestamp() + 60,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    ctx = await get_visibility_ctx(_fake_request(), _bearer(token), db_session)
    assert ctx.role == "partner"
