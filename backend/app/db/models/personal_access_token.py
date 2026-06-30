import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# v1 ships a single capability. Kept as a column (not a bare constant) so the
# scope split (read-only / full) is an additive change later, not a rewrite.
PAT_CAPABILITIES = ("import-write",)


class PersonalAccessToken(Base):
    """A programmatic API credential for the offline ingest CLI.

    Auth model (see core/security.py): the wire token is hl_pat_<prefix>.<secret>.
    Only ``token_hash`` (SHA-256 of the secret) is stored; ``prefix`` is the
    non-secret indexed lookup key. Verification is a fast constant-time compare,
    NOT bcrypt — a PAT is high-entropy and checked on every request.

    Revocation is enforced LIVE on every request: the auth layer re-reads
    ``revoked_at`` / ``expires_at`` and the owning user's ``is_active`` rather
    than trusting a cached context, so revoking a token takes effect immediately.
    Minting is primary-only (enforced in PATService).
    """

    __tablename__ = "personal_access_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # The user who minted the token; their role/member are resolved live at auth
    # time, so a demotion or deactivation revokes the token's authority too.
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    capability: Mapped[str] = mapped_column(String(32), nullable=False, default="import-write")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
