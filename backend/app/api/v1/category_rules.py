import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.category_rule import (
    BackfillResponse,
    CategoryRuleCreate,
    CategoryRuleResponse,
    CategoryRuleUpdate,
    RuleSuggestion,
)
from app.services.categorization import CategorizationService

router = APIRouter()


@router.get("/category-rules", response_model=list[CategoryRuleResponse])
async def list_rules(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[CategoryRuleResponse]:
    rules = await CategorizationService(session).list_rules(ctx)
    return [CategoryRuleResponse.model_validate(r) for r in rules]


@router.get("/category-rules/suggestions", response_model=list[RuleSuggestion])
async def suggest_rules(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[RuleSuggestion]:
    """Candidate rules mined from how you've categorized transactions so far."""
    return await CategorizationService(session).suggest_from_history(ctx)


@router.post(
    "/category-rules", response_model=CategoryRuleResponse, status_code=status.HTTP_201_CREATED
)
async def create_rule(
    body: CategoryRuleCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> CategoryRuleResponse:
    rule = await CategorizationService(session).create(ctx, body)
    return CategoryRuleResponse.model_validate(rule)


@router.post("/category-rules/backfill", response_model=BackfillResponse)
async def backfill_rules(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> BackfillResponse:
    """Apply active rules to existing uncategorized transactions (fill-empty)."""
    updated = await CategorizationService(session).backfill_uncategorized(ctx)
    return BackfillResponse(updated=updated)


@router.patch("/category-rules/{rule_id}", response_model=CategoryRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    body: CategoryRuleUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> CategoryRuleResponse:
    rule = await CategorizationService(session).update(ctx, rule_id, body)
    return CategoryRuleResponse.model_validate(rule)


@router.delete("/category-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    await CategorizationService(session).delete(ctx, rule_id)
