import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot, audit
from app.core.encryption import decrypt, encrypt
from app.core.visibility import VisibilityContext
from app.db.models.access_grant import AccountAccessGrant
from app.db.models.account import Account
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.repositories.real_estate import RealEstateRepository
from app.schemas.account import AccessGrantCreate, AccountCreate, AccountResponse, AccountUpdate

# Account types whose balance is the running sum of their transactions.
# Valuation-based types (investments, pension) use AccountSnapshot instead.
_TRANSACTION_BASED_TYPES: frozenset[str] = frozenset(
    {
        "checking",
        "savings",
        "credit_card",
        "mortgage",
        "auto_loan",
        "personal_loan",
        "student_loan",
        "other_asset",
        "other_liability",
    }
)


def _decrypt_opt(val: bytes | None) -> str | None:
    return decrypt(val) if val else None


def _account_to_response(
    account: Account, balance: Decimal | None, balance_date: date | None
) -> AccountResponse:
    institution_name = _decrypt_opt(account.institution_name_enc)
    account_number = _decrypt_opt(account.account_number_enc)
    last4 = account_number[-4:] if account_number and len(account_number) >= 4 else account_number
    notes = _decrypt_opt(account.notes_enc)

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
        notes=notes,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)
        self.audit_repo = AuditRepository(session)
        self.property_repo = RealEstateRepository(session)

    async def _latest_snapshot(self, account_id: uuid.UUID) -> AccountSnapshot | None:
        result = await self.session.execute(
            select(AccountSnapshot)
            .where(AccountSnapshot.account_id == account_id)
            .order_by(AccountSnapshot.snapshot_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _batch_latest_snapshots(
        self, account_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, AccountSnapshot]:
        """Fetch the most-recent snapshot for each account in one query (DISTINCT ON)."""
        if not account_ids:
            return {}
        result = await self.session.execute(
            select(AccountSnapshot)
            .where(AccountSnapshot.account_id.in_(account_ids))
            .distinct(AccountSnapshot.account_id)
            .order_by(AccountSnapshot.account_id, AccountSnapshot.snapshot_date.desc())
        )
        return {snap.account_id: snap for snap in result.scalars().all()}

    async def _batch_transaction_balances(
        self, account_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Decimal]:
        """Compute running balance (SUM of amounts) for transaction-based accounts."""
        if not account_ids:
            return {}
        result = await self.session.execute(
            select(Transaction.account_id, func.sum(Transaction.amount).label("total"))
            .where(Transaction.account_id.in_(account_ids))
            .group_by(Transaction.account_id)
        )
        return {row.account_id: Decimal(str(row.total)) for row in result.all()}

    async def _transaction_balance(self, account_id: uuid.UUID) -> Decimal | None:
        """Compute running balance from transactions for a single account."""
        result = await self.session.execute(
            select(func.sum(Transaction.amount)).where(Transaction.account_id == account_id)
        )
        total = result.scalar_one_or_none()
        return Decimal(str(total)) if total is not None else None

    async def list_accounts(self, ctx: VisibilityContext) -> list[AccountResponse]:
        accounts = await self.account_repo.get_visible(ctx, is_active=True)

        # Pre-fetch real estate valuations in two steps (same pattern as report.py:221-236).
        # batch_latest_valuations_as_of takes property_ids, NOT account_ids.
        today = date.today()
        re_account_ids = [a.id for a in accounts if a.account_type == "real_estate"]
        props = await self.property_repo.list_for_accounts(re_account_ids) if re_account_ids else []
        account_to_prop_id = {p.account_id: p.id for p in props}
        if account_to_prop_id:
            raw = await self.property_repo.batch_latest_valuations_as_of(
                list(account_to_prop_id.values()), today
            )
            re_balances = {
                acc_id: raw.get(prop_id, Decimal("0"))
                for acc_id, prop_id in account_to_prop_id.items()
            }
        else:
            re_balances = {}

        # Transaction-based accounts: balance = SUM of transaction amounts.
        txn_ids = [a.id for a in accounts if a.account_type in _TRANSACTION_BASED_TYPES]
        txn_balances = await self._batch_transaction_balances(txn_ids)

        # Valuation-based non-RE accounts: balance = most-recent snapshot.
        snap_ids = [
            a.id
            for a in accounts
            if a.account_type not in _TRANSACTION_BASED_TYPES and a.account_type != "real_estate"
        ]
        snap_map = await self._batch_latest_snapshots(snap_ids)

        responses = []
        for account in accounts:
            if account.account_type == "real_estate" and account.id in re_balances:
                responses.append(_account_to_response(account, re_balances[account.id], today))
            elif account.account_type in _TRANSACTION_BASED_TYPES:
                bal = txn_balances.get(account.id)
                responses.append(_account_to_response(account, bal, None))
            else:
                snap = snap_map.get(account.id)
                responses.append(
                    _account_to_response(
                        account,
                        snap.balance if snap else None,
                        snap.snapshot_date if snap else None,
                    )
                )
        return responses

    async def get(self, ctx: VisibilityContext, account_id: uuid.UUID) -> AccountResponse:
        account = await self.account_repo.get_by_id(ctx, account_id)
        if account.account_type in _TRANSACTION_BASED_TYPES:
            bal = await self._transaction_balance(account.id)
            return _account_to_response(account, bal, None)
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
        if not ctx.is_primary and data.owner_member_id not in (None, ctx.member_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Partners may only create joint or own-member accounts",
            )
        now = datetime.now(UTC)
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
    async def update(
        self, ctx: VisibilityContext, account_id: uuid.UUID, data: AccountUpdate
    ) -> Account:
        account = await self.account_repo.get_by_id(ctx, account_id)
        if not ctx.is_primary and account.owner_member_id != ctx.member_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if (
            data.owner_member_id is not None
            and not ctx.is_primary
            and data.owner_member_id != ctx.member_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Partners may only assign accounts to themselves or jointly",
            )
        self._prev_snapshot = _snapshot(account, exclude=AUDIT_EXCLUDED_FIELDS)

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

        account.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(account)
        return account

    @audit("account.deactivated", "account")
    async def deactivate(self, ctx: VisibilityContext, account_id: uuid.UUID) -> Account:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        account = await self.account_repo.get_by_id(ctx, account_id)
        self._prev_snapshot = _snapshot(account, exclude=AUDIT_EXCLUDED_FIELDS)
        account.is_active = False
        account.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(account)
        return account

    async def list_grants(
        self, ctx: VisibilityContext, account_id: uuid.UUID
    ) -> list[AccountAccessGrant]:
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

        now = datetime.now(UTC)
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
            new_value={
                "account_id": str(account_id),
                "grantee_member_id": str(data.grantee_member_id),
            },
        )
        return grant

    async def revoke_grant(
        self, ctx: VisibilityContext, account_id: uuid.UUID, grant_id: uuid.UUID
    ) -> None:
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
        grant.revoked_at = datetime.now(UTC)
        await self.session.flush()

        await self.audit_repo.write(
            ctx=ctx,
            action="member.access_grant_revoked",
            entity_type="member",
            entity_id=grant.grantee_member_id,
            previous_value={
                "account_id": str(account_id),
                "grantee_member_id": str(grant.grantee_member_id),
            },
        )
