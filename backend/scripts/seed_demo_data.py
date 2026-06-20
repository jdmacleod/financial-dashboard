#!/usr/bin/env python3
"""
HearthLedger demo data seeder.

Usage:
    python scripts/seed_demo_data.py --household 1
    python scripts/seed_demo_data.py --household 2
    python scripts/seed_demo_data.py --household 3
    python scripts/seed_demo_data.py --household all

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

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from seed_households import h1_chen_nakamura, h2_okonkwo_rivera, h3_whitfield_torres

_SEEDERS = {
    1: h1_chen_nakamura.seed,
    2: h2_okonkwo_rivera.seed,
    3: h3_whitfield_torres.seed,
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
        print(f"  Members: {r['members']} | Accounts: {r['accounts']} "
              f"| Transactions: ~{r['transactions']:,} | Properties: {r['properties']}")
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


async def main(household_arg: str) -> None:
    _banner()
    t0 = time.perf_counter()

    if household_arg == "all":
        to_seed = [1, 2, 3]
    else:
        n = int(household_arg)
        if n not in _SEEDERS:
            print(f"Error: --household must be 1, 2, 3, or all. Got: {household_arg}")
            sys.exit(1)
        to_seed = [n]

    results: list[dict] = []

    async with AsyncSessionLocal() as session:
        async with session.begin():
            rng = random.Random(42)
            for num in to_seed:
                result = await _seed_one(session, num, rng)
                results.append(result)

    elapsed = time.perf_counter() - t0
    _print_summary(results, elapsed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed HearthLedger with demo household data.")
    parser.add_argument(
        "--household",
        required=True,
        choices=["1", "2", "3", "all"],
        help="Which household(s) to seed",
    )
    args = parser.parse_args()
    asyncio.run(main(args.household))
