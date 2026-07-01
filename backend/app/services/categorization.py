import re
import uuid
from collections import Counter
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.category import Category
from app.db.models.category_rule import CategoryRule
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.schemas.category_rule import CategoryRuleCreate, CategoryRuleUpdate, RuleSuggestion

# A payee must recur at least this many times with a single dominant category
# before we bother suggesting a rule for it.
_MIN_SUGGESTION_OCCURRENCES = 3


def _normalize(text: str) -> str:
    return text.strip().upper()


def _rule_matches(rule: CategoryRule, payee: str) -> bool:
    """Does this rule's pattern match the payee? exact/contains are
    case-insensitive on the normalized text; regex is searched against the raw
    payee (case-insensitive). An invalid regex never matches (validated on
    create, but guarded here too so a bad row can't raise mid-categorization)."""
    if rule.match_type == "exact":
        return _normalize(payee) == _normalize(rule.pattern)
    if rule.match_type == "contains":
        return _normalize(rule.pattern) in _normalize(payee)
    if rule.match_type == "regex":
        try:
            return re.search(rule.pattern, payee, re.IGNORECASE) is not None
        except re.error:
            return False
    return False


class CategorizationService:
    """Deterministic payee -> category rules: the memory layer.

    ``match`` is the hot path (called from promote + manual create). CRUD is
    audited. ``suggest_from_history`` mines existing categorizations into
    candidate rules the user confirms; ``backfill_uncategorized`` applies active
    rules to existing uncategorized transactions on demand (fill-empty only).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.account_repo = AccountRepository(session)

    # --- matching (hot path) ---------------------------------------------
    async def _active_rules(self, household_id: uuid.UUID) -> list[CategoryRule]:
        result = await self.session.execute(
            select(CategoryRule)
            .where(
                CategoryRule.household_id == household_id,
                CategoryRule.is_active.is_(True),
            )
            # Highest priority first; older rule wins ties for determinism.
            .order_by(CategoryRule.priority.desc(), CategoryRule.created_at.asc())
        )
        return list(result.scalars().all())

    async def match(self, household_id: uuid.UUID, payee: str | None) -> uuid.UUID | None:
        """Return the category of the highest-priority active rule matching the
        payee, or None. Caller only applies this to fill an EMPTY category."""
        if not payee:
            return None
        for rule in await self._active_rules(household_id):
            if _rule_matches(rule, payee):
                return rule.category_id
        return None

    # --- CRUD (audited) ---------------------------------------------------
    async def _get_or_404(self, ctx: VisibilityContext, rule_id: uuid.UUID) -> CategoryRule:
        result = await self.session.execute(
            select(CategoryRule).where(
                CategoryRule.id == rule_id, CategoryRule.household_id == ctx.household_id
            )
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
        return rule

    async def _assert_category(self, ctx: VisibilityContext, category_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(Category.id).where(
                Category.id == category_id, Category.household_id == ctx.household_id
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category")

    async def list_rules(self, ctx: VisibilityContext) -> list[CategoryRule]:
        result = await self.session.execute(
            select(CategoryRule)
            .where(CategoryRule.household_id == ctx.household_id)
            .order_by(CategoryRule.priority.desc(), CategoryRule.created_at.asc())
        )
        return list(result.scalars().all())

    @audit("category_rule.created", "category_rule")
    async def create(self, ctx: VisibilityContext, data: CategoryRuleCreate) -> CategoryRule:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if data.match_type == "regex":
            _validate_regex(data.pattern)
        await self._assert_category(ctx, data.category_id)
        now = datetime.now(UTC)
        rule = CategoryRule(
            household_id=ctx.household_id,
            pattern=data.pattern,
            match_type=data.match_type,
            category_id=data.category_id,
            priority=data.priority,
            is_active=data.is_active,
            created_at=now,
            updated_at=now,
        )
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    @audit("category_rule.updated", "category_rule")
    async def update(
        self, ctx: VisibilityContext, rule_id: uuid.UUID, data: CategoryRuleUpdate
    ) -> CategoryRule:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        rule = await self._get_or_404(ctx, rule_id)
        self._prev_snapshot = _snapshot(rule)
        if data.match_type == "regex" and data.pattern is not None:
            _validate_regex(data.pattern)
        elif data.match_type == "regex" and data.pattern is None:
            _validate_regex(rule.pattern)
        if data.category_id is not None:
            await self._assert_category(ctx, data.category_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        rule.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def delete(self, ctx: VisibilityContext, rule_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        rule = await self._get_or_404(ctx, rule_id)
        prev = _snapshot(rule)
        await self.session.delete(rule)
        await self.session.flush()
        await self.audit_repo.write(
            ctx=ctx,
            action="category_rule.deleted",
            entity_type="category_rule",
            entity_id=rule_id,
            previous_value=prev,
            new_value=None,
        )

    # --- suggest + backfill ----------------------------------------------
    async def suggest_from_history(self, ctx: VisibilityContext) -> list[RuleSuggestion]:
        """Mine reviewed, categorized transactions into candidate 'contains'
        rules: for each payee, the dominant category, if it recurs enough and no
        active rule already covers that payee. Suggestions only — never created."""
        accounts = await self.account_repo.get_visible(ctx)
        account_ids = [a.id for a in accounts]
        if not account_ids:
            return []

        # Manual entries carry payee_normalized; imports carry payee_raw (and
        # promote copies it into payee_normalized). Coalesce so both are mined.
        payee_col = func.coalesce(Transaction.payee_normalized, Transaction.payee_raw)
        result = await self.session.execute(
            select(payee_col, Transaction.category_id).where(
                Transaction.account_id.in_(account_ids),
                Transaction.category_id.is_not(None),
                or_(
                    Transaction.payee_normalized.is_not(None),
                    Transaction.payee_raw.is_not(None),
                ),
                Transaction.is_transfer.is_(False),
            )
        )
        by_payee: dict[str, Counter[uuid.UUID]] = {}
        for payee, category_id in result.all():
            key = _normalize(payee)
            by_payee.setdefault(key, Counter())[category_id] += 1

        existing = await self._active_rules(ctx.household_id)
        cat_names = {
            c.id: c.name
            for c in (
                await self.session.execute(
                    select(Category).where(Category.household_id == ctx.household_id)
                )
            ).scalars()
        }

        suggestions: list[RuleSuggestion] = []
        for payee_key, counts in by_payee.items():
            category_id, occurrences = counts.most_common(1)[0]
            if occurrences < _MIN_SUGGESTION_OCCURRENCES:
                continue
            # Skip payees an active rule already covers.
            if any(_rule_matches(r, payee_key) for r in existing):
                continue
            suggestions.append(
                RuleSuggestion(
                    pattern=payee_key,
                    match_type="contains",
                    category_id=category_id,
                    category_name=cat_names.get(category_id, "Unknown"),
                    occurrences=occurrences,
                )
            )
        suggestions.sort(key=lambda s: s.occurrences, reverse=True)
        return suggestions

    async def backfill_uncategorized(self, ctx: VisibilityContext) -> int:
        """Apply active rules to existing uncategorized transactions (fill-empty
        only). Each newly-categorized transaction is audited. Returns the count."""
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        accounts = await self.account_repo.get_visible(ctx)
        account_ids = [a.id for a in accounts]
        if not account_ids:
            return 0

        rules = await self._active_rules(ctx.household_id)
        if not rules:
            return 0

        result = await self.session.execute(
            select(Transaction).where(
                Transaction.account_id.in_(account_ids),
                Transaction.category_id.is_(None),
                Transaction.is_transfer.is_(False),
            )
        )
        updated = 0
        now = datetime.now(UTC)
        for txn in result.scalars():
            payee = txn.payee_normalized or txn.payee_raw or ""
            match = next((r.category_id for r in rules if _rule_matches(r, payee)), None)
            if match is None:
                continue
            prev = _snapshot(txn, exclude=frozenset())
            txn.category_id = match
            txn.updated_at = now
            await self.session.flush()
            await self.audit_repo.write(
                ctx=ctx,
                action="transaction.categorized_by_rule",
                entity_type="transaction",
                entity_id=txn.id,
                previous_value={"category_id": prev["category_id"]},
                new_value={"category_id": str(match)},
            )
            updated += 1
        await self.session.commit()
        return updated


def _validate_regex(pattern: str) -> None:
    try:
        re.compile(pattern)
    except re.error as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid regex: {exc}"
        ) from exc
