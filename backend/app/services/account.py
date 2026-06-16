import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.encryption import decrypt, encrypt
from app.core.visibility import VisibilityContext
from app.db.models.access_grant import AccountAccessGrant
from app.db.models.account import Account
from app.db.models.snapshot import AccountSnapshot
from app.repositories.account import AccountRepository
from app.schemas.account import AccessGrantCreate, AccountCreate, AccountUpdate, AccountResponse


def _decrypt_opt(val: bytes | None) -> str | None:
    return decrypt(val) if val else None


def _account_to_response(account: Account, balance: Decimal | None, balance_date: date | None) -> AccountResponse:
    institution_name = _decrypt_opt(account.institution_name_enc)
    account_number = _decrypt_opt(account.account_number_enc)
    last4 = account_number[-4:] if account_number and len(account_number) >= 4 else account_number

    return AccountResponse(
        id=account.id,
        nickname=account.nickname,
        account_type=account.account_type,
        owner_member_id=account.owner_member_id,
        institution_name=institution_name,
        account_number_last4=last4,
        include_in_net_worth=account.include_in_net_worth,
        is_active=account.is_active,
        current_balance=balance,
        balance_as_of=balance_date,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


class AccountService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.account_repo = AccountRepository(session)
        self.audit_repo = AuditRepository(session)

    async def _latest_snapshot(self, account_id: uuid.UUID) -> AccountSnapshot | None:
        result = await self.session.execute(
            select(AccountSnapshot)
            .where(AccountSnapshot.account_id == account_id)
            .order_by(AccountSnapshot.snapshot_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list(self, ctx: VisibilityContext) -> list[AccountResponse]:
        accounts = await self.account_repo.get_visible(ctx, is_active=True)
        responses = []
        for account in accounts:
            snap = await self._latest_snapshot(account.id)
            responses.append(_account_to_response(
                account,
                snap.balance if snap else None,
                snap.snapshot_date if snap else None,
            ))
        return responses

    async def get(self, ctx: VisibilityContext, account_id: uuid.UUID) -> AccountResponse:
        account = await self.account_repo.get_by_id(ctx, account_id)
        snap = await self._latest_snapshot(account.id)
        return _account_to_response(
            account,
            snap.balance if snap else None,
            snap.snapshot_date if snap else None,
        )

    @audit("account.created", "account")
    async def create(self, ctx: VisibilityContext, data: AccountCreate) -> Account:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        now = datetime.now(timezone.utc)
        account = Account(
            household_id=ctx.household_id,
            owner_member_id=data.owner_member_id,
            account_type=data.account_type,
            nickname=data.nickname,
            institution_name_enc=encrypt(data.institution_name) if data.institution_name else None,
            account_number_enc=encrypt(data.account_number) if data.account_number else None,
            routing_number_enc=encrypt(data.routing_number) if data.routing_number else None,
            include_in_net_worth=data.include_in_net_worth,
            is_active=True,
            notes_enc=encrypt(data.notes) if data.notes else None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(account)
        await self.session.flush()
        await self.session.refresh(account)
        return account

    @audit("account.updated", "account")
    async def update(self, ctx: VisibilityContext, account_id: uuid.UUID, data: AccountUpdate) -> Account:
        account = await self.account_repo.get_by_id(ctx, account_id)
        if not ctx.is_primary and account.owner_member_id != ctx.member_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        self._prev_snapshot = _snapshot(account)

        if data.nickname is not None:
            account.nickname = data.nickname
        if data.owner_member_id is not None:
            account.owner_member_id = data.owner_member_id
        if data.institution_name is not None:
            account.institution_name_enc = encrypt(data.institution_name)
        if data.account_number is not None:
            account.account_number_enc = encrypt(data.account_number)
        if data.routing_number is not None:
            account.routing_number_enc = encrypt(data.routing_number)
        if data.include_in_net_worth is not None:
            account.include_in_net_worth = data.include_in_net_worth
        if data.notes is not None:
            account.notes_enc = encrypt(data.notes)

        account.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(account)
        return account

    @audit("account.deactivated", "account")
    async def deactivate(self, ctx: VisibilityContext, account_id: uuid.UUID) -> Account:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        account = await self.account_repo.get_by_id(ctx, account_id)
        self._prev_snapshot = _snapshot(account)
        account.is_active = False
        account.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(account)
        return account

    async def list_grants(self, ctx: VisibilityContext, account_id: uuid.UUID) -> list[AccountAccessGrant]:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await self.account_repo.get_by_id(ctx, account_id)
        result = await self.session.execute(
            select(AccountAccessGrant).where(
                AccountAccessGrant.account_id == account_id,
                AccountAccessGrant.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def create_grant(
        self, ctx: VisibilityContext, account_id: uuid.UUID, data: AccessGrantCreate
    ) -> AccountAccessGrant:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        account = await self.account_repo.get_by_id(ctx, account_id)
        if not account.owner_member_id:
            raise HTTPException(status_code=400, detail="Cannot grant access to a joint account")
        if account.owner_member_id == data.grantee_member_id:
            raise HTTPException(status_code=400, detail="Cannot grant access to the account owner")

        now = datetime.now(timezone.utc)
        grant = AccountAccessGrant(
            account_id=account_id,
            owner_member_id=account.owner_member_id,
            grantee_member_id=data.grantee_member_id,
            granted_by_user_id=ctx.user_id,
            access_level="read",
            is_active=True,
            created_at=now,
        )
        self.session.add(grant)
        await self.session.flush()
        await self.session.refresh(grant)

        await self.audit_repo.write(
            ctx=ctx,
            action="member.access_grant_created",
            entity_type="member",
            entity_id=data.grantee_member_id,
            new_value={"account_id": str(account_id), "grantee_member_id": str(data.grantee_member_id)},
        )
        return grant

    async def revoke_grant(self, ctx: VisibilityContext, account_id: uuid.UUID, grant_id: uuid.UUID) -> None:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        result = await self.session.execute(
            select(AccountAccessGrant).where(
                AccountAccessGrant.id == grant_id,
                AccountAccessGrant.account_id == account_id,
                AccountAccessGrant.is_active.is_(True),
            )
        )
        grant = result.scalar_one_or_none()
        if not grant:
            raise HTTPException(status_code=404, detail="Grant not found")

        grant.is_active = False
        grant.revoked_at = datetime.now(timezone.utc)
        await self.session.flush()

        await self.audit_repo.write(
            ctx=ctx,
            action="member.access_grant_revoked",
            entity_type="member",
            entity_id=grant.grantee_member_id,
            previous_value={"account_id": str(account_id), "grantee_member_id": str(grant.grantee_member_id)},
        )
