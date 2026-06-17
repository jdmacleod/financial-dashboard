import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.transaction import (
    BulkCategorizeRequest,
    PaginatedTransactions,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.transaction import TransactionService

router = APIRouter()


@router.get("/accounts/{account_id}/transactions", response_model=PaginatedTransactions)
async def list_transactions(
    account_id: uuid.UUID,
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    is_reviewed: bool | None = Query(None),
    is_transfer: bool | None = Query(None),
    real_estate_property_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PaginatedTransactions:
    svc = TransactionService(session)
    items, total = await svc.list_for_account(
        ctx,
        account_id,
        from_date=from_,
        to_date=to,
        category_id=category_id,
        is_reviewed=is_reviewed,
        is_transfer=is_transfer,
        real_estate_property_id=real_estate_property_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedTransactions(
        items=[TransactionResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/accounts/{account_id}/transactions", response_model=TransactionResponse, status_code=201
)
async def create_transaction(
    account_id: uuid.UUID,
    data: TransactionCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    svc = TransactionService(session)
    transaction = await svc.create(ctx, account_id, data)
    await session.commit()
    await session.refresh(transaction)
    return TransactionResponse.model_validate(transaction)


@router.patch(
    "/accounts/{account_id}/transactions/bulk-categorize",
    response_model=list[TransactionResponse],
)
async def bulk_categorize(
    account_id: uuid.UUID,
    data: BulkCategorizeRequest,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[TransactionResponse]:
    svc = TransactionService(session)
    transactions = await svc.bulk_categorize(ctx, account_id, data)
    await session.commit()
    return [TransactionResponse.model_validate(t) for t in transactions]


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    svc = TransactionService(session)
    transaction = await svc.get(ctx, transaction_id)
    return TransactionResponse.model_validate(transaction)


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    data: TransactionUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    svc = TransactionService(session)
    transaction = await svc.update(ctx, transaction_id, data)
    await session.commit()
    await session.refresh(transaction)
    return TransactionResponse.model_validate(transaction)


@router.delete("/transactions/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = TransactionService(session)
    await svc.delete(ctx, transaction_id)
    await session.commit()
