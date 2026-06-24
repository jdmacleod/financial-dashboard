import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot
from app.core.encryption import decrypt, encrypt
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.property_valuation import PropertyValuation
from app.db.models.real_estate import RealEstateProperty
from app.repositories.account import AccountRepository
from app.repositories.real_estate import RealEstateRepository
from app.schemas.real_estate import (
    PropertyCreate,
    PropertyEquityResponse,
    PropertyResponse,
    PropertyUpdate,
    ValuationCreate,
)


def _assert_writable(ctx: VisibilityContext, account: Account) -> None:
    if not ctx.can_write:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if not ctx.is_primary and account.owner_member_id not in (None, ctx.member_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partners may only manage properties on their own or joint accounts",
        )


class RealEstateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)
        self.property_repo = RealEstateRepository(session)
        self.audit_repo = AuditRepository(session)

    async def _to_response(
        self, property_: RealEstateProperty, account: Account
    ) -> PropertyResponse:
        latest = await self.property_repo.latest_valuation(property_.id)
        return PropertyResponse(
            id=property_.id,
            account_id=property_.account_id,
            nickname=account.nickname,
            address=decrypt(property_.address_enc),
            purchase_date=property_.purchase_date,
            purchase_price=property_.purchase_price,
            linked_mortgage_account_id=property_.linked_mortgage_account_id,
            ownership_entity_id=property_.ownership_entity_id,
            property_type=property_.property_type,
            current_estimated_value=latest.estimated_value if latest else None,
            current_value_as_of=latest.valuation_date if latest else None,
            created_at=property_.created_at,
            updated_at=property_.updated_at,
        )

    async def list_all(self, ctx: VisibilityContext) -> list[PropertyResponse]:
        accounts = await self.account_repo.get_visible(ctx)
        re_accounts = [a for a in accounts if a.account_type == "real_estate"]
        if not re_accounts:
            return []
        account_map = {a.id: a for a in re_accounts}
        properties = await self.property_repo.list_for_accounts(list(account_map.keys()))
        return [await self._to_response(p, account_map[p.account_id]) for p in properties]

    async def get(self, ctx: VisibilityContext, property_id: uuid.UUID) -> PropertyResponse:
        property_ = await self.property_repo.get_by_id(property_id)
        if property_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        account = await self.account_repo.get_by_id(ctx, property_.account_id)
        return await self._to_response(property_, account)

    async def get_by_account(
        self, ctx: VisibilityContext, account_id: uuid.UUID
    ) -> PropertyResponse:
        account = await self.account_repo.get_by_id(ctx, account_id)
        property_ = await self.property_repo.get_by_account_id(account_id)
        if property_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        return await self._to_response(property_, account)

    async def create(self, ctx: VisibilityContext, data: PropertyCreate) -> PropertyResponse:
        account = await self.account_repo.get_by_id(ctx, data.account_id)
        _assert_writable(ctx, account)
        if account.account_type != "real_estate":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Property records may only be linked to real_estate accounts",
            )
        if await self.property_repo.get_by_account_id(data.account_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This account already has a property record",
            )

        now = datetime.now(UTC)
        property_ = RealEstateProperty(
            account_id=data.account_id,
            address_enc=encrypt(data.address),
            purchase_date=data.purchase_date,
            purchase_price=data.purchase_price,
            linked_mortgage_account_id=data.linked_mortgage_account_id,
            property_type=data.property_type,
            created_at=now,
            updated_at=now,
        )
        self.session.add(property_)
        try:
            await self.session.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This account already has a property record",
            ) from None
        await self.session.refresh(property_)

        await self.audit_repo.write(
            ctx=ctx,
            action="property.created",
            entity_type="property",
            entity_id=property_.id,
            new_value=_snapshot(property_, exclude=AUDIT_EXCLUDED_FIELDS),
        )
        return await self._to_response(property_, account)

    async def update(
        self, ctx: VisibilityContext, property_id: uuid.UUID, data: PropertyUpdate
    ) -> PropertyResponse:
        property_ = await self.property_repo.get_by_id(property_id)
        if property_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        account = await self.account_repo.get_by_id(ctx, property_.account_id)
        _assert_writable(ctx, account)

        prev = _snapshot(property_, exclude=AUDIT_EXCLUDED_FIELDS)

        for field_name in data.model_fields_set:
            value = getattr(data, field_name)
            # property_type is NOT NULL in DB — guard against explicit null
            if field_name == "property_type" and value is None:
                continue
            if field_name == "address":
                property_.address_enc = encrypt(value) if value else property_.address_enc
            else:
                setattr(property_, field_name, value)

        property_.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(property_)

        curr = _snapshot(property_, exclude=AUDIT_EXCLUDED_FIELDS)
        changed_keys = {k for k in set(prev) | set(curr) if prev.get(k) != curr.get(k)}
        await self.audit_repo.write(
            ctx=ctx,
            action="property.updated",
            entity_type="property",
            entity_id=property_.id,
            previous_value={k: prev.get(k) for k in changed_keys},
            new_value={k: curr.get(k) for k in changed_keys},
        )
        return await self._to_response(property_, account)

    async def get_equity(
        self, ctx: VisibilityContext, property_id: uuid.UUID
    ) -> PropertyEquityResponse:
        property_ = await self.property_repo.get_by_id(property_id)
        if property_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        await self.account_repo.get_by_id(ctx, property_.account_id)  # RBAC

        latest = await self.property_repo.latest_valuation(property_.id)
        if latest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No valuation available"
            )

        mortgage_balance = None
        mortgage_balance_as_of = None
        mortgage_balance_visible = True
        equity = None

        if property_.linked_mortgage_account_id is not None:
            try:
                await self.account_repo.get_by_id(ctx, property_.linked_mortgage_account_id)
                snap = await self.account_repo.latest_snapshot(property_.linked_mortgage_account_id)
                if snap is not None:
                    raw_balance, mortgage_balance_as_of = snap
                    mortgage_balance = abs(raw_balance)
                    equity = latest.estimated_value - mortgage_balance
            except HTTPException as exc:
                if exc.status_code == 404:
                    mortgage_balance_visible = False
                else:
                    raise
        else:
            equity = latest.estimated_value

        return PropertyEquityResponse(
            property_value=latest.estimated_value,
            valuation_date=latest.valuation_date,
            valuation_source=latest.source,
            mortgage_balance=mortgage_balance,
            mortgage_balance_as_of=mortgage_balance_as_of,
            mortgage_balance_visible=mortgage_balance_visible,
            equity=equity,
        )

    async def list_valuations(
        self, ctx: VisibilityContext, property_id: uuid.UUID
    ) -> list[PropertyValuation]:
        property_ = await self.property_repo.get_by_id(property_id)
        if property_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        await self.account_repo.get_by_id(ctx, property_.account_id)
        return await self.property_repo.list_valuations(property_id)

    async def add_valuation(
        self, ctx: VisibilityContext, property_id: uuid.UUID, data: ValuationCreate
    ) -> PropertyValuation:
        property_ = await self.property_repo.get_by_id(property_id)
        if property_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        account = await self.account_repo.get_by_id(ctx, property_.account_id)
        _assert_writable(ctx, account)

        valuation = PropertyValuation(
            real_estate_property_id=property_id,
            valuation_date=data.valuation_date,
            estimated_value=data.estimated_value,
            source=data.source,
            created_at=datetime.now(UTC),
        )
        self.session.add(valuation)
        await self.session.flush()
        await self.session.refresh(valuation)

        await self.audit_repo.write(
            ctx=ctx,
            action="property.valuation_added",
            entity_type="property",
            entity_id=property_id,
            new_value=_snapshot(valuation),
        )
        return valuation
