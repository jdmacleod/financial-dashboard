# Phase 1 — Auth, Members, Accounts, and Audit Log

Implements the complete authentication system, member and user management,
account CRUD with visibility rules, access grants, and the audit log
infrastructure. Every subsequent phase depends on these foundations.

---

## Deliverables

- [ ] Login / logout / token refresh endpoints
- [ ] JWT middleware resolving `VisibilityContext` on every authenticated request
- [ ] Account lockout after `MAX_LOGIN_ATTEMPTS` failed attempts
- [ ] Executor re-auth endpoint
- [ ] Household read endpoint (single household per installation)
- [ ] Member CRUD (primary role only for create/update/delete)
- [ ] User CRUD (create user account linked to member)
- [ ] Account CRUD — all queries through `AccountRepository.get_visible(ctx)`
- [ ] Account access grant / revoke (primary role only)
- [ ] `AuditRepository` (append-only) + `@audit` decorator
- [ ] All Phase 1 service methods emit audit events
- [ ] `POST /api/v1/setup` one-time setup endpoint (creates household + first primary user)
- [ ] Frontend: login page, member list, account list

---

## Backend

### `app/core/security.py`

```python
from datetime import datetime, timedelta, timezone
from typing import Literal
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str, member_id: str | None, role: str) -> str:
    payload = {
        "sub": user_id,
        "member_id": member_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def create_reauth_token(user_id: str) -> str:
    """Short-lived token (10 min) gating executor-level exports."""
    payload = {
        "sub": user_id,
        "type": "reauth",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def decode_token(token: str, expected_type: Literal["access", "refresh", "reauth"]) -> dict:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise JWTError("Wrong token type")
    return payload
```

### `app/core/encryption.py`

```python
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

_key = base64.b64decode(settings.secret_encryption_key)

def encrypt(plaintext: str) -> bytes:
    nonce = os.urandom(12)
    ct = AESGCM(_key).encrypt(nonce, plaintext.encode(), None)
    return nonce + ct  # prepend nonce; stored as BYTEA

def decrypt(ciphertext: bytes) -> str:
    nonce, ct = ciphertext[:12], ciphertext[12:]
    return AESGCM(_key).decrypt(nonce, ct, None).decode()
```

### `app/core/visibility.py`

```python
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class VisibilityContext:
    user_id: UUID
    member_id: UUID | None
    role: str              # 'primary' | 'partner' | 'dependent'
    household_id: UUID
    ip_address: str | None = None

    @property
    def is_primary(self) -> bool:
        return self.role == "primary"

    @property
    def can_export_executor(self) -> bool:
        return self.role == "primary"

    @property
    def can_write(self) -> bool:
        return self.role in ("primary", "partner")
```

FastAPI dependency — resolves `VisibilityContext` from Bearer token:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.security import decode_token
from app.db.base import get_session

bearer = HTTPBearer()

async def get_visibility_ctx(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session = Depends(get_session),
) -> VisibilityContext:
    try:
        payload = decode_token(credentials.credentials, "access")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = UUID(payload["sub"])
    member_id = UUID(payload["member_id"]) if payload.get("member_id") else None
    role = payload.get("role", "partner")

    # Fetch household_id for this user (cached from DB; household is single per install)
    household_id = await _get_household_id(session, user_id)
    if not household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return VisibilityContext(
        user_id=user_id,
        member_id=member_id,
        role=role,
        household_id=household_id,
    )
```

### `app/core/audit.py`

#### `AuditRepository`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit_log import AuditLog
from app.core.visibility import VisibilityContext
import uuid

class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def write(
        self,
        ctx: VisibilityContext,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        previous_value: dict | None = None,
        new_value: dict | None = None,
    ) -> None:
        row = AuditLog(
            household_id=ctx.household_id,
            user_id=ctx.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_value=previous_value,
            new_value=new_value,
            ip_address=ctx.ip_address,
        )
        self.session.add(row)
        await self.session.flush()  # within the outer transaction
```

#### `@audit` decorator

Applied to service methods that mutate data. Captures changed fields
only (not full row snapshots). Fires after the DB commit succeeds.
Never writes encrypted field values.

```python
ENCRYPTED_FIELDS = frozenset({
    "institution_name_enc",
    "account_number_enc",
    "routing_number_enc",
    "address_enc",
    "notes_enc",
})

def audit(action: str, entity_type: str):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(self, ctx: VisibilityContext, *args, **kwargs):
            result = await fn(self, ctx, *args, **kwargs)
            entity_id = getattr(result, "id", None)

            prev = getattr(wrapper, "_prev_snapshot", None)
            curr = _snapshot(result, exclude=ENCRYPTED_FIELDS)
            diff_prev, diff_curr = _diff(prev, curr) if prev else (None, curr)

            await self.audit_repo.write(
                ctx=ctx,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                previous_value=diff_prev,
                new_value=diff_curr,
            )
            return result
        return wrapper
    return decorator
```

For update methods, the service must capture the pre-update snapshot before
calling the ORM update and store it on the instance as `_prev_snapshot`.
See `AccountService.update()` for the canonical pattern.

### `app/repositories/account.py`

```python
class AccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_visible(
        self, ctx: VisibilityContext, **filters
    ) -> list[Account]:
        """
        THE canonical account query method.
        All code paths that need accounts must call this.
        Never query Account directly outside this class.
        """
        q = select(Account).where(Account.household_id == ctx.household_id)

        if not ctx.is_primary:
            q = q.where(
                or_(
                    Account.owner_member_id.is_(None),        # joint
                    Account.owner_member_id == ctx.member_id, # own
                    Account.id.in_(                           # granted
                        select(AccountAccessGrant.account_id)
                        .where(
                            AccountAccessGrant.grantee_member_id == ctx.member_id,
                            AccountAccessGrant.is_active.is_(True),
                        )
                    ),
                )
            )

        # Apply caller-supplied filters (account_type, is_active, etc.)
        for attr, value in filters.items():
            q = q.where(getattr(Account, attr) == value)

        result = await self.session.execute(q)
        return result.scalars().all()

    async def get_by_id(self, ctx: VisibilityContext, account_id: UUID) -> Account:
        accounts = await self.get_visible(ctx, id=account_id)
        if not accounts:
            raise HTTPException(status_code=404, detail="Account not found")
        return accounts[0]
```

### API endpoints — Phase 1

#### Setup (one-time, unauthenticated)

```
POST /api/v1/setup
```
Creates the single household, seeds categories, creates the first primary
member and user. Returns 409 if setup has already been completed.
Disables itself after first successful call (check households table count).

#### Auth

```
POST /api/v1/auth/login
  body: {email, password}
  response: {access_token, token_type: "bearer"}
  side effect: sets refresh_token httpOnly cookie

POST /api/v1/auth/refresh
  reads refresh_token cookie
  response: {access_token, token_type: "bearer"}
  side effect: rotates refresh token (new cookie)

POST /api/v1/auth/logout
  clears cookie, nulls refresh_token_hash in DB

POST /api/v1/auth/reauth
  body: {password}
  response: {reauth_token}   # 10-min token; passed as header for executor exports

POST /api/v1/auth/change-password
  body: {current_password, new_password}
```

Auth service enforces:
- Increment `failed_login_attempts` on bad password
- Set `locked_until = now() + LOCKOUT_MINUTES` when attempts >= MAX_LOGIN_ATTEMPTS
- Reject login if `locked_until` is in the future
- Reset `failed_login_attempts = 0` on successful login
- Log all auth events to `audit_log` including IP address

#### Household

```
GET /api/v1/household
  returns the single household (name, settings)

PATCH /api/v1/household
  body: {name?, settings?}
  requires: primary role
```

#### Members

```
GET    /api/v1/members
POST   /api/v1/members          requires: primary
GET    /api/v1/members/{id}
PATCH  /api/v1/members/{id}     requires: primary (or own non-role fields)
DELETE /api/v1/members/{id}     requires: primary; soft-delete (is_active=false)
```

Constraint: the last primary member cannot be deactivated or have their
role downgraded. Enforce in service layer, not just API.

#### Users

```
POST   /api/v1/users            requires: primary (creates login for a member)
PATCH  /api/v1/users/{id}       requires: primary or own account
DELETE /api/v1/users/{id}       requires: primary; deactivates login
```

#### Accounts

```
GET    /api/v1/accounts                   filtered by VisibilityContext
POST   /api/v1/accounts                   requires: primary or partner
GET    /api/v1/accounts/{id}              visibility-checked
PATCH  /api/v1/accounts/{id}             visibility-checked + must be owner or primary
DELETE /api/v1/accounts/{id}             requires: primary; soft-delete
```

Encrypted fields (`institution_name`, `account_number`, `routing_number`, `notes`)
are accepted as plaintext strings in request bodies, encrypted before DB write,
and decrypted before returning in response bodies. The API never exposes the
raw `BYTEA` values.

Response schema for accounts:
```json
{
  "id": "uuid",
  "nickname": "BofA Checking",
  "account_type": "checking",
  "owner_member_id": "uuid-or-null",
  "institution_name": "Bank of America",
  "account_number_last4": "4321",
  "include_in_net_worth": true,
  "is_active": true,
  "current_balance": 12450.00,
  "balance_as_of": "2025-01-14"
}
```

Note: `account_number_last4` is derived at read time (last 4 chars of
decrypted account number). Full account number is never returned in list
views. It is returned in detail view only and only in executor-scoped
export generation.

#### Access grants

```
GET    /api/v1/accounts/{id}/grants        requires: primary
POST   /api/v1/accounts/{id}/grants        requires: primary
DELETE /api/v1/accounts/{id}/grants/{gid}  requires: primary
```

---

## Frontend — Phase 1 pages

### `/login`
Standard login form. Email + password. Shows error on failed attempt.
Shows "Account locked, try again in N minutes" on lockout.
No registration link — accounts are created by a primary member.

### `/setup`
First-run wizard. Shown only when `GET /api/v1/household` returns 404.
Three steps:
1. Household name
2. First primary member name
3. Email + password for first user

### `/members`
Member list. Primary sees all members with role badges. Shows "Add member"
button (primary only). Clicking a member opens a slide-over with edit form.

### `/accounts`
Account list grouped by type (Assets / Liabilities). Shows nickname,
institution name, account_number_last4, current balance, owner badge
(joint vs member name). "Add account" button opens a multi-step modal:
1. Account type selector
2. Nickname + institution + account number fields
3. Owner selector (joint or specific member) — primary only sees all members;
   partner can only create joint or own-member accounts.

---

## Acceptance criteria

1. `POST /api/v1/setup` creates household, seeds 20+ system categories,
   creates first primary member and user. Second call returns 409.
2. `POST /api/v1/auth/login` with correct credentials returns access token
   and sets httpOnly cookie.
3. After `MAX_LOGIN_ATTEMPTS` failed logins, subsequent attempts return 423
   with `locked_until` in the response.
4. A `partner` user calling `GET /api/v1/accounts` does not see accounts
   owned by other members unless a grant exists.
5. A `dependent` user calling `GET /api/v1/accounts` sees only joint accounts.
6. A `partner` user calling `POST /api/v1/members` receives 403.
7. Creating an account via `POST /api/v1/accounts` writes an
   `account.created` row to `audit_log`.
8. The `audit_log` row for account creation contains `nickname` and
   `account_type` but NOT `institution_name_enc` or `account_number_enc`.
9. `docker compose exec db psql -U hearthledger -c
   "DELETE FROM audit_log WHERE id = (SELECT id FROM audit_log LIMIT 1)"`
   returns `ERROR: permission denied`.
10. The last primary member cannot be deactivated (service returns 409).
11. Login page renders and submits correctly. Successful login redirects
    to `/` (dashboard placeholder). Failed login shows inline error.
