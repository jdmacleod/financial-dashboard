import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.account import (
    AccessGrantCreate,
    AccessGrantResponse,
    AccountCreate,
    AccountResponse,
    AccountUpdate,
)
from app.services.account import AccountService

router = APIRouter()


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    return await svc.list(ctx)


@router.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(
    data: AccountCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    account = await svc.create(ctx, data)
    await session.commit()
    await session.refresh(account)
    return await svc.get(ctx, account.id)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    return await svc.get(ctx, account_id)


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    data: AccountUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    account = await svc.update(ctx, account_id, data)
    await session.commit()
    await session.refresh(account)
    return await svc.get(ctx, account.id)


@router.delete("/accounts/{account_id}", status_code=204)
async def deactivate_account(
    account_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    await svc.deactivate(ctx, account_id)
    await session.commit()


@router.get("/accounts/{account_id}/grants", response_model=list[AccessGrantResponse])
async def list_grants(
    account_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    return await svc.list_grants(ctx, account_id)


@router.post("/accounts/{account_id}/grants", response_model=AccessGrantResponse, status_code=201)
async def create_grant(
    account_id: uuid.UUID,
    data: AccessGrantCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    grant = await svc.create_grant(ctx, account_id, data)
    await session.commit()
    await session.refresh(grant)
    return grant


@router.delete("/accounts/{account_id}/grants/{grant_id}", status_code=204)
async def revoke_grant(
    account_id: uuid.UUID,
    grant_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = AccountService(session)
    await svc.revoke_grant(ctx, account_id, grant_id)
    await session.commit()
