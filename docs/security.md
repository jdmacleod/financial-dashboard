# Security Architecture

This document explains how HearthLedger handles authentication, authorization, encryption, and auditing.

---

## Authentication

### JWT + refresh token flow

HearthLedger uses short-lived JWTs for API authorization combined with HttpOnly refresh tokens for session persistence.

**Access token:**

- Signed with `SECRET_KEY` (HS256)
- Contains `sub` (user ID), `member_id`, `role`, `type: "access"`
- Expires in `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30 minutes)
- Sent by the client in every request: `Authorization: Bearer <token>`

**Refresh token:**

- Signed with `SECRET_KEY`, longer-lived
- Contains `type: "refresh"` and a `jti` (JWT ID)
- Stored in an `HttpOnly; SameSite=Lax` cookie: inaccessible to JavaScript
- Expires in `REFRESH_TOKEN_EXPIRE_DAYS` (default: 30 days)
- Rotated on every use: `POST /auth/refresh` issues a new access token AND a new refresh token, invalidating the old one

**Token refresh flow:**

```
Client                   Server
  |  POST /auth/login      |
  |----------------------> |  Verifies password, creates tokens
  |  access_token (body)   |
  |  refresh_token (cookie)|
  | <--------------------- |

  ... 30 minutes pass ...

  |  POST /auth/refresh    |
  |  [cookie sent auto]    |
  | ---------------------->|  Verifies refresh token, rotates it
  |  new access_token      |
  |  new refresh_token     |
  | <--------------------- |
```

### Brute-force protection

Failed login attempts are tracked per email address. After `MAX_LOGIN_ATTEMPTS` failures (default: 5) within a window, the account is locked for `LOCKOUT_MINUTES` minutes (default: 15). The API returns `423 Locked` during the lockout period.

### Reauth tokens

Some operations require re-authentication even with a valid access token. Export requests, for example, require a `X-Reauth-Token` header.

A reauth token is obtained via `POST /auth/reauth` (requires the user's current password). It is a short-lived JWT with `type: "reauth"`, typically valid for a few minutes and single-use for the operation it authorizes.

This prevents an unattended browser session from exporting or downloading sensitive data.

### Password hashing

Passwords are hashed with bcrypt (via `passlib[bcrypt]`). The work factor is configured by passlib's defaults. Plaintext passwords are never stored or logged.

### Client-side cache isolation

The frontend caches API responses (account balances, the household name, reports) in a React Query cache to avoid refetching on every navigation. Because those cached entries are not keyed by user, the cache is cleared whenever the signed-in identity changes, so one account never renders another account's cached data. This happens two ways: explicitly on sign-out (`useAuth.logout` / `clearAuth`), and automatically whenever the access token swaps to a different `sub` (`lib/sessionCache`, hooked into `setAccessToken`). The automatic path closes the gap for any code path that swaps the token without routing through sign-out. A background token refresh issues a new token for the _same_ identity and intentionally leaves the cache in place. This is a browser-side defense-in-depth measure: server-side authorization (the `VisibilityContext` and `AccountRepository.get_visible`) is the real enforcement boundary and is checked on every request regardless.

---

## Role-Based Access Control

Each household member has a role:

| Role        | Description                                     |
| ----------- | ----------------------------------------------- |
| `primary`   | Full access: only one per household             |
| `partner`   | Standard member with limited admin capabilities |
| `dependent` | Read-only access to explicitly granted accounts |

### What each role can do

| Action                        | primary | partner               | dependent    |
| ----------------------------- | ------- | --------------------- | ------------ |
| Create/update/delete accounts | ✅      | Own accounts only     | ❌           |
| View accounts                 | ✅      | Own + granted         | Granted only |
| Import transactions           | ✅      | ✅                    | ❌           |
| Create/edit transactions      | ✅      | ✅ (visible accounts) | ❌           |
| Create/edit budgets           | ✅      | ✅                    | ❌           |
| View reports                  | ✅      | ✅ (visible accounts) | ❌           |
| Export data                   | ✅      | ✅                    | ❌           |
| Manage members                | ✅      | ❌                    | ❌           |
| Manage access grants          | ✅      | ❌                    | ❌           |
| Trigger/download backups      | ✅      | ❌                    | ❌           |
| View audit log                | ✅      | ❌                    | ❌           |
| Change valuation provider     | ✅      | ❌                    | ❌           |

### The VisibilityContext

Every authenticated request resolves a `VisibilityContext` dataclass from the JWT:

```python
@dataclass(frozen=True)
class VisibilityContext:
    user_id: UUID
    member_id: UUID | None
    role: str           # 'primary' | 'partner' | 'dependent'
    household_id: UUID
    ip_address: str | None
```

This context is passed to every service method. **All account queries go through `AccountRepository.get_visible(ctx)`**: no route handler queries the accounts table directly. This is a hard architectural rule enforced by convention and code review.

### Access grants

The primary member can grant a partner or dependent member read access to specific accounts owned by another member. Grants are stored in the `access_grants` table and are checked at query time by `AccountRepository`.

---

## Field-Level Encryption

Certain fields contain PII (personally identifiable information) and are stored encrypted in the database.

**Encrypted fields:**

- `accounts.institution_name_enc`
- `accounts.account_number_enc`
- `accounts.routing_number_enc`
- `accounts.notes_enc`
- `real_estate_properties.address_enc`

**Algorithm:** AES-256-GCM (authenticated encryption). Implementation: `cryptography` library.

**Key management:** The encryption key (`SECRET_ENCRYPTION_KEY`) is a 32-byte key encoded as base64, stored only in `.env`. It is never committed to the repository, never stored in the database, and never logged.

**At rest:** Encrypted values are stored as `BYTEA` columns. The format is: `nonce (12 bytes) + ciphertext + auth_tag (16 bytes)`, concatenated.

**At read time:** The application decrypts values when constructing API responses. Encrypted values are never exposed in their raw (encrypted) form in API responses.

**Audit log exclusion:** Encrypted field values are **never** written to `audit_log.previous_value` or `audit_log.new_value`: not even in encrypted form. Audit entries for account mutations omit these fields entirely.

---

## Audit Log

HearthLedger maintains an append-only audit log of all data mutations.

### What is logged

Every service method that mutates data is decorated with `@audit`. The decorator fires after a successful database commit and writes a row to `audit_log` with:

- `actor_member_id`: who made the change
- `entity_type` / `entity_id`: what was changed
- `action`: `create`, `update`, or `delete`
- `previous_value` / `new_value`: JSON snapshots of changed fields
- `ip_address`: the requester's IP address
- `created_at`: TIMESTAMPTZ

### Append-only enforcement

The `audit_log` table is protected at the PostgreSQL permission level. The application's database role (`hearthledger_app`) has only `SELECT` and `INSERT` on this table: no `UPDATE`, `DELETE`, or `TRUNCATE`. This is enforced in the baseline Alembic migration and cannot be overridden through the application.

### Viewing the log

The primary member can view the audit log under **Settings → Activity** in the UI, or via `GET /api/v1/audit-log`.

---

## Backup Encryption

Backup files (PostgreSQL dump files created by `pg_dump`) are encrypted before being written to disk using the same AES-256-GCM key as field encryption (`SECRET_ENCRYPTION_KEY`).

The encrypt-then-store approach means:

- Backup files at rest on the host filesystem are ciphertext only
- Downloading a backup via the API serves the encrypted file
- Restoring requires decrypting the file first, which requires `SECRET_ENCRYPTION_KEY`

---

## Network Security

**Port exposure:** Only port 80 (nginx) is exposed to the host. PostgreSQL (5432) and Redis (6379) are internal to the Docker bridge network (`hearthledger_net`) and cannot be reached from outside the container network.

**CORS:** The `ALLOWED_ORIGINS` environment variable restricts cross-origin requests. In production this should be locked to `http://localhost` (or the actual hostname if you expose HearthLedger over a local network).

**HTTPS:** The current configuration serves over HTTP on port 80. For access over a home network, add a TLS-terminating reverse proxy (e.g. Caddy, Traefik) in front of nginx. Never expose the application to the public internet over plain HTTP.

---

## Secrets management

All secrets live in `.env`:

| Variable                | Purpose                                   |
| ----------------------- | ----------------------------------------- |
| `DB_PASSWORD`           | PostgreSQL password                       |
| `SECRET_KEY`            | JWT signing key                           |
| `SECRET_ENCRYPTION_KEY` | AES-256-GCM field + backup encryption key |

**`.env` is gitignored** and must never be committed. The `.env.example` file contains only placeholder values and documents the required variables.

**Rotation:**

- Rotating `SECRET_KEY` invalidates all existing JWTs (all users are logged out).
- Rotating `SECRET_ENCRYPTION_KEY` requires re-encrypting all encrypted database fields and all existing backup files: there is no automated migration for this; plan carefully.
