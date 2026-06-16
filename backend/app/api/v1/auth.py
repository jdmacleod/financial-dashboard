from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    ReauthRequest,
    ReauthResponse,
    TokenResponse,
)
from app.services.auth import AuthService

router = APIRouter()

_COOKIE = "refresh_token"
_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=False, max_age=60 * 60 * 24 * 30)


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    ip = request.client.host if request.client else None
    svc = AuthService(session)
    access_token, refresh_token = await svc.login(data.email, data.password, ip)
    response.set_cookie(_COOKIE, refresh_token, **_COOKIE_OPTS)
    return TokenResponse(access_token=access_token)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    from fastapi import HTTPException, status

    token = request.cookies.get(_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    svc = AuthService(session)
    new_access, new_refresh = await svc.refresh(token)
    response.set_cookie(_COOKIE, new_refresh, **_COOKIE_OPTS)
    return TokenResponse(access_token=new_access)


@router.post("/auth/logout", status_code=204)
async def logout(
    response: Response,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AuthService(session)
    await svc.logout(ctx.user_id, ctx.household_id, ctx.ip_address)
    response.delete_cookie(_COOKIE)


@router.post("/auth/reauth", response_model=ReauthResponse)
async def reauth(
    data: ReauthRequest,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AuthService(session)
    token = await svc.reauth(ctx.user_id, data.password, ctx.household_id, ctx.ip_address)
    return ReauthResponse(reauth_token=token)


@router.post("/auth/change-password", status_code=204)
async def change_password(
    data: ChangePasswordRequest,
    response: Response,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AuthService(session)
    await svc.change_password(
        ctx.user_id, data.current_password, data.new_password, ctx.household_id, ctx.ip_address
    )
    response.delete_cookie(_COOKIE)
