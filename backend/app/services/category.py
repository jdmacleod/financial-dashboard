import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.category import Category
from app.db.models.transaction import Transaction
from app.schemas.category import CategoryCreate, CategoryUpdate

UNCATEGORIZED_NAME = "Uncategorized"


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def list_categories(self, ctx: VisibilityContext) -> list[Category]:
        result = await self.session.execute(
            select(Category)
            .where(Category.household_id == ctx.household_id)
            .order_by(Category.is_income.desc(), Category.name)
        )
        return list(result.scalars().all())

    async def _get_or_404(self, ctx: VisibilityContext, category_id: uuid.UUID) -> Category:
        result = await self.session.execute(
            select(Category).where(
                Category.id == category_id, Category.household_id == ctx.household_id
            )
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        return category

    @audit("category.created", "category")
    async def create(self, ctx: VisibilityContext, data: CategoryCreate) -> Category:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        category = Category(
            household_id=ctx.household_id,
            name=data.name,
            parent_category_id=data.parent_category_id,
            color_hex=data.color_hex,
            icon=data.icon,
            is_income=data.is_income,
            is_system=False,
            created_at=datetime.now(UTC),
        )
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    @audit("category.updated", "category")
    async def update(
        self, ctx: VisibilityContext, category_id: uuid.UUID, data: CategoryUpdate
    ) -> Category:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        category = await self._get_or_404(ctx, category_id)
        if category.is_system:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="System categories cannot be modified"
            )
        self._prev_snapshot = _snapshot(category)

        if data.name is not None:
            category.name = data.name
        if data.parent_category_id is not None:
            category.parent_category_id = data.parent_category_id
        if data.color_hex is not None:
            category.color_hex = data.color_hex
        if data.icon is not None:
            category.icon = data.icon

        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete(self, ctx: VisibilityContext, category_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        category = await self._get_or_404(ctx, category_id)
        if category.is_system:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="System categories cannot be deleted"
            )

        result = await self.session.execute(
            select(Category).where(
                Category.household_id == ctx.household_id,
                Category.name == UNCATEGORIZED_NAME,
                Category.is_system.is_(True),
            )
        )
        uncategorized = result.scalar_one_or_none()
        if uncategorized is not None:
            await self.session.execute(
                update(Transaction)
                .where(Transaction.category_id == category_id)
                .values(category_id=uncategorized.id)
            )

        prev = _snapshot(category)
        await self.session.delete(category)
        await self.session.flush()

        await self.audit_repo.write(
            ctx=ctx,
            action="category.deleted",
            entity_type="category",
            entity_id=category_id,
            previous_value=prev,
        )
