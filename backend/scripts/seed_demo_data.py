#!/usr/bin/env python3
"""
HearthLedger demo data seeder.

Usage:
    python scripts/seed_demo_data.py --household 1
    python scripts/seed_demo_data.py --household all
    python scripts/seed_demo_data.py --household 5 --action delete
    python scripts/seed_demo_data.py --household 5 --action reset
    python scripts/seed_demo_data.py --action inspect
    python scripts/seed_demo_data.py --household 5 --action inspect

Actions:
    seed    (default) Additive seed — skips already-seeded households.
    delete  Delete the household and all its data (CASCADE). Prompts for
            confirmation unless --yes is passed.
    reset   Delete then immediately reseed. Atomic per household — if the
            reseed fails, the delete is rolled back. Prompts unless --yes.
    inspect Read-only summary of current DB state. --household defaults to all.

The --household all mode is for demo/test environments only.
Production installs should seed a single household.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from pathlib import Path

# Allow running from project root: python scripts/seed_demo_data.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed_households import (
    h1_chen_nakamura,
    h2_okonkwo_rivera,
    h3_whitfield_torres,
    h4_park_cole,
    h5_langford,
    h6_castellano,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal

_SEEDERS = {
    1: h1_chen_nakamura.seed,
    2: h2_okonkwo_rivera.seed,
    3: h3_whitfield_torres.seed,
    4: h4_park_cole.seed,
    5: h5_langford.seed,
    6: h6_castellano.seed,
}

_HOUSEHOLD_NAMES = {
    1: "Chen-Nakamura Household",
    2: "Okonkwo-Rivera Household",
    3: "Whitfield-Torres Household",
    4: "Park-Cole Household",
    5: "Langford Household",
    6: "Castellano Household",
}


def _banner() -> None:
    print("=" * 60)
    print(" HearthLedger Demo Data Seeder")
    print("=" * 60)


def _print_summary(results: list[dict], elapsed: float) -> None:
    print("\n=== HearthLedger Demo Data Summary ===\n")
    total_txns = 0
    for r in results:
        print(f"Household {r['num']}: {r['name']} ({r['location']})")
        print(
            f"  Members: {r['members']} | Accounts: {r['accounts']} "
            f"| Transactions: ~{r['transactions']:,} | Properties: {r['properties']}"
        )
        print(f"  Computed Net Worth: ${r['net_worth']:,.0f}")
        print(f"  FIRE scenarios: {r['fire_scenarios']} | Debt records: {r['debt_records']}")
        print()
        total_txns += r["transactions"]
    print(f"Total transactions generated: ~{total_txns:,}")
    print(f"Run time: {elapsed:.1f}s")


async def _seed_one(
    session: AsyncSession,
    household_num: int,
    rng: random.Random,
) -> dict:
    seeder = _SEEDERS[household_num]
    print(f"  → Seeding household {household_num}...", flush=True)
    result = await seeder(session, rng)
    print(f"    {result['name']}: {result['transactions']:,} transactions generated.")
    return result


async def _household_exists(session: AsyncSession, name: str) -> bool:
    result = await session.execute(
        text("SELECT 1 FROM households WHERE name = :name LIMIT 1"), {"name": name}
    )
    return result.scalar_one_or_none() is not None


async def _delete_household(session: AsyncSession, name: str) -> bool:
    """Delete a household by name. Returns True if found and deleted, False if not found.

    ON DELETE CASCADE propagates to all child tables including audit_log.
    Runs under the DB owner role — the app role cannot delete from audit_log,
    but the seed script can. This is an accepted exception for dev tooling only.
    """
    result = await session.execute(
        text("DELETE FROM households WHERE name = :name RETURNING id"),
        {"name": name},
    )
    return result.scalar_one_or_none() is not None


async def _inspect_household(session: AsyncSession, name: str) -> dict | None:
    """Return member/account/transaction counts for a household, or None if not seeded."""
    row = await session.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM household_members WHERE household_id = h.id) AS members,
                (SELECT COUNT(*) FROM accounts      WHERE household_id = h.id) AS accounts,
                (SELECT COUNT(*) FROM transactions  WHERE household_id = h.id) AS transactions
            FROM households h
            WHERE h.name = :name
        """),
        {"name": name},
    )
    r = row.mappings().one_or_none()
    if r is None:
        return None
    return {
        "name": name,
        "members": r["members"],
        "accounts": r["accounts"],
        "transactions": r["transactions"],
    }


def _confirm(prompt: str, yes: bool) -> bool:
    if yes:
        return True
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer == "y"


def _print_inspect_table(rows: list[tuple[int, str, dict | None]]) -> None:
    print("\n=== HearthLedger Demo DB State ===\n")
    header = f"  {'#':<4} {'Name':<25} {'Members':>7} {'Accounts':>8} {'Transactions':>12}  Status"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for num, name, data in rows:
        short = name.replace(" Household", "")
        if data is None:
            print(f"  {num:<4} {short:<25} {'':>7} {'':>8} {'':>12}  NOT SEEDED")
        else:
            print(
                f"  {num:<4} {short:<25} {data['members']:>7,} {data['accounts']:>8,} "
                f"{data['transactions']:>12,}  SEEDED"
            )
    print()


async def main(household_arg: str | None, action: str, yes: bool) -> None:
    _banner()
    t0 = time.perf_counter()

    # For inspect, --household defaults to all.
    if action == "inspect" and household_arg is None:
        household_arg = "all"
    elif household_arg is None:
        print(f"Error: --household is required for --action {action}")
        sys.exit(1)

    if household_arg == "all":
        to_target = sorted(_SEEDERS)
    else:
        n = int(household_arg)
        if (
            n not in _SEEDERS
        ):  # argparse catches this via choices=; guard is for programmatic callers
            print(
                f"Error: --household must be a valid household number or all. Got: {household_arg}"
            )
            sys.exit(1)
        to_target = [n]

    # ── inspect ──────────────────────────────────────────────────────────────
    if action == "inspect":
        rows: list[tuple[int, str, dict | None]] = []
        for num in to_target:
            name = _HOUSEHOLD_NAMES[num]
            async with AsyncSessionLocal() as session:
                data = await _inspect_household(session, name)
            rows.append((num, name, data))
        _print_inspect_table(rows)
        return

    # ── delete ───────────────────────────────────────────────────────────────
    if action == "delete":
        if len(to_target) == 1:
            num = to_target[0]
            prompt = f"Delete Household {num} ({_HOUSEHOLD_NAMES[num]})? This cannot be undone."
        else:
            prompt = f"Delete all {len(_SEEDERS)} demo households? This cannot be undone."

        if not _confirm(prompt, yes):
            print("Aborted.")
            return

        for num in to_target:
            name = _HOUSEHOLD_NAMES[num]
            async with AsyncSessionLocal() as session, session.begin():
                deleted = await _delete_household(session, name)
            if deleted:
                print(f"  → Deleted Household {num} ({name}).")
            else:
                print(f"  → Household {num} ({name}) not found, nothing to delete.")
        return

    # ── reset ─────────────────────────────────────────────────────────────────
    if action == "reset":
        if len(to_target) == 1:
            num = to_target[0]
            prompt = f"Delete and reseed Household {num} ({_HOUSEHOLD_NAMES[num]})?"
        else:
            prompt = f"Delete and reseed all {len(_SEEDERS)} demo households?"

        if not _confirm(prompt, yes):
            print("Aborted.")
            return

        results: list[dict] = []
        for num in to_target:
            name = _HOUSEHOLD_NAMES[num]
            # Delete and reseed in one transaction per household. If reseed fails,
            # the delete is rolled back and the household is restored.
            async with AsyncSessionLocal() as session, session.begin():
                deleted = await _delete_household(session, name)
                if deleted:
                    print(f"  → Deleted Household {num} ({name}), reseeding...", flush=True)
                else:
                    print(f"  → Household {num} ({name}) not found, seeding fresh...", flush=True)
                rng = random.Random(42 + num)
                result = await _seed_one(session, num, rng)
                results.append(result)

        elapsed = time.perf_counter() - t0
        _print_summary(results, elapsed)
        return

    # ── seed (default) ────────────────────────────────────────────────────────
    results = []
    for num in to_target:
        name = _HOUSEHOLD_NAMES[num]
        async with AsyncSessionLocal() as session:
            if await _household_exists(session, name):
                print(f"  → Household {num} ({name}) already exists, skipping.")
                continue
        async with AsyncSessionLocal() as session, session.begin():
            rng = random.Random(42 + num)
            result = await _seed_one(session, num, rng)
            results.append(result)

    elapsed = time.perf_counter() - t0
    _print_summary(results, elapsed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed, delete, reset, or inspect HearthLedger demo household data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  seed household 5:          --household 5
  seed all:                  --household all
  delete household 5:        --household 5 --action delete
  delete all (no prompt):    --household all --action delete --yes
  reset household 5:         --household 5 --action reset
  inspect all households:    --action inspect
  inspect household 5:       --household 5 --action inspect
""",
    )
    parser.add_argument(
        "--household",
        choices=[str(k) for k in sorted(_SEEDERS)] + ["all"],
        default=None,
        help="Which household(s) to target. Required for seed/delete/reset; defaults to 'all' for inspect.",
    )
    parser.add_argument(
        "--action",
        choices=["seed", "delete", "reset", "inspect"],
        default="seed",
        help="Action to perform (default: seed).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt for delete/reset.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.household, args.action, args.yes))
