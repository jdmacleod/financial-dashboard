#!/usr/bin/env python3
"""
HearthLedger admin password reset.

The recovery path when a user loses their password and has no way back in:
there is no current password to supply (rules out the in-app change-password
form) and, if the locked-out user is the sole primary, no authenticated session
to drive the provisioning flow. The operator runs this from the host shell.

Usage:
    docker-compose exec backend python scripts/reset_password.py user@example.com
    docker-compose exec backend python scripts/reset_password.py user@example.com --yes

It mints a server-generated temporary password, forces the user to set their own
on next login (must_change_password), clears any lockout, and invalidates active
sessions. The temporary password is printed once; relay it to the user out of
band. By default it shows the matched user and asks for confirmation so a
mistyped email can't silently reset the wrong account; --yes skips the prompt
for scripted use.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running from the project root: python scripts/reset_password.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.services.auth import AuthService


async def main(email: str, assume_yes: bool) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"No user found with email {email!r}.", file=sys.stderr)
            return 1

        member: HouseholdMember | None = None
        if user.member_id:
            member_result = await session.execute(
                select(HouseholdMember).where(HouseholdMember.id == user.member_id)
            )
            member = member_result.scalar_one_or_none()
        member_desc = f"{member.display_name} ({member.role})" if member else "(no linked member)"

        print("Matched user:")
        print(f"  email:   {user.email}")
        print(f"  member:  {member_desc}")

        if not assume_yes:
            reply = input("Reset this user's password? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("Aborted. No changes made.")
                return 0

        service = AuthService(session)
        temporary_password = await service.admin_reset_password(email)

    print()
    print(f"Temporary password: {temporary_password}")
    print("  -> the user must set a new password on first login.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset a HearthLedger user's password from the host shell.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  reset (with confirmation):  user@example.com
  reset (no prompt):          user@example.com --yes
""",
    )
    parser.add_argument("email", help="Email of the user whose password to reset.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt (for scripted use).",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.email, args.yes)))
