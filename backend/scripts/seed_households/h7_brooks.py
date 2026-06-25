"""Household 7 — Brooks (Atlanta, GA). ~$11,000 net worth.

Member: Aaliyah Brooks (primary, b. 1999-03-14). Single, 27, software engineer
~2-3 years into her career. The dataset's early-accumulation opener: a high
income-for-age earner building from a low net-worth base. Debt elimination is the
hero surface — a carried credit card, a personal loan, and a student loan,
deliberately sized so the avalanche and snowball payoff orders DIFFER (the
"Avalanche saves $X" callout renders). Roth-heavy (low bracket now), long FIRE
runway, first-home savings goal. Daily spend rides the debit/checking side because
she is in debt-payoff mode and not adding to the card.

See the CEO casting plan: H7 is "land the future-affluent client early." Net worth
is intentionally low (top income-for-age, low NW-for-age). Set a higher student
loan to drive net worth negative for rendering tests (see the coverage matrix note).
"""

from __future__ import annotations

import random
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from seed_households._util import (
    DATE_END,
    all_months,
    build_snapshots,
    clamp_day,
    gen_variable,
    last_day_of,
    make_account,
    make_budget,
    make_debt,
    make_fire_scenario,
    make_household,
    make_member,
    make_user,
    opening_balance_tx,
    transfer,
    tx,
)
from seed_households.shared_categories import seed_categories

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

D = Decimal

# Third-paycheck months (biweekly pay lands a 3rd check in these months).
_THIRD_PAYCHECK_MONTHS = {5, 10}


async def seed(session: AsyncSession, rng: random.Random) -> dict:
    # ── Household ─────────────────────────────────────────────────────────────
    hh = make_household("Brooks Household")
    session.add(hh)
    hid = hh.id

    # ── Member + user (single) ────────────────────────────────────────────────
    aaliyah = make_member(hid, "Aaliyah Brooks", "primary", date_of_birth=date(1999, 3, 14))
    session.add(aaliyah)
    session.add(make_user(aaliyah.id, "aaliyah@brooks.local"))
    await session.flush()

    # ── Categories ────────────────────────────────────────────────────────────
    cat = await seed_categories(session, hid)

    # ── Accounts ──────────────────────────────────────────────────────────────
    def acc(atype, name, inst, last4, *, owner=None, in_nw=True, revolving=False):
        a = make_account(
            hid,
            atype,
            name,
            inst,
            last4,
            owner_member_id=owner,
            include_in_net_worth=in_nw,
            is_revolving=revolving,
        )
        session.add(a)
        return a

    # Transaction-tracked
    checking = acc("checking", "Everyday Checking", "Capital One", "2287", owner=aaliyah.id)
    emerg = acc("savings", "Emergency Fund", "Ally Bank", "6691", owner=aaliyah.id)
    card = acc("credit_card", "Sapphire Card", "Chase", "4417", owner=aaliyah.id, revolving=True)
    personal = acc("personal_loan", "Personal Loan", "SoFi", "8830", owner=aaliyah.id)
    student = acc("student_loan", "Federal Student Loan", "MOHELA", "5521", owner=aaliyah.id)

    # Snapshot-tracked (value comes from build_snapshots)
    brokerage = acc("investment_brokerage", "Brokerage", "Fidelity", "7702", owner=aaliyah.id)
    roth_401k = acc("retirement_401k", "Roth 401(k)", "Fidelity", "9913", owner=aaliyah.id)
    roth_ira = acc("retirement_roth_ira", "Roth IRA", "Fidelity", "3354", owner=aaliyah.id)
    hsa = acc("hsa", "HSA", "HealthEquity", "1102", owner=aaliyah.id)

    await session.flush()

    # ── Investment account snapshots ──────────────────────────────────────────
    # One market dip (Oct 2024) so the net-worth series is non-monotonic.
    dips = {last_day_of(2024, 10): -0.035}

    def monthly(amount: str) -> dict[date, D]:
        return {
            last_day_of(y, m): D(amount)
            for ms in all_months()
            if ms < date(2026, 6, 1)
            for y, m in [(ms.year, ms.month)]
        }

    def jan_oct(amount: str) -> dict[date, D]:
        out: dict[date, D] = {}
        for ms in all_months():
            if ms >= date(2026, 6, 1):
                break
            out[last_day_of(ms.year, ms.month)] = D(amount) if ms.month <= 10 else D("0.00")
        return out

    # Roth 401(k): $550/mo employee + match, payroll-deducted; 8.5%
    session.add_all(build_snapshots(roth_401k.id, D("6000.00"), monthly("550.00"), 0.085, dips))
    # Roth IRA: $400/mo Jan-Oct (funded from checking); 8.5%
    session.add_all(build_snapshots(roth_ira.id, D("3000.00"), jan_oct("400.00"), 0.085, dips))
    # Taxable brokerage: $100/mo; conservative 6.5%
    session.add_all(build_snapshots(brokerage.id, D("1500.00"), monthly("100.00"), 0.065, dips))
    # HSA invested (triple-tax, young HDHP saver): $200/mo payroll; 8.5%
    session.add_all(build_snapshots(hsa.id, D("1500.00"), monthly("200.00"), 0.085, dips))

    # ── Transaction generation ────────────────────────────────────────────────
    all_txns: list = []
    running: dict[uuid.UUID, D] = {
        checking.id: D("0"),
        emerg.id: D("0"),
        card.id: D("0"),
        personal.id: D("0"),
        student.id: D("0"),
    }

    def add(*txs):
        for t in txs:
            all_txns.append(t)
            if t.account_id in running:
                running[t.account_id] += t.amount

    for month_start in all_months():
        y, m = month_start.year, month_start.month
        if month_start > DATE_END:
            break

        # ── Income: biweekly net paycheck (~$150k gross -> ~$4,000 net/check) ──
        for day in (6, 20):
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, day),
                    D("4000.00"),
                    "Mailchimp Payroll",
                    cat["salary"],
                )
            )
        if m in _THIRD_PAYCHECK_MONTHS:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 13),
                    D("4000.00"),
                    "Mailchimp Payroll",
                    cat["salary"],
                )
            )

        # Annual federal tax refund in April
        if m == 4:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 16),
                    D("1200.00"),
                    "IRS TREAS 310",
                    cat["tax_refund"],
                )
            )

        # ── Fixed checking outflows ───────────────────────────────────────────
        add(tx(checking.id, clamp_day(y, m, 1), -D("1650.00"), "The Dagny Midtown", cat["rent"]))
        add(
            tx(
                checking.id,
                clamp_day(y, m, 5),
                -D("18.00"),
                "Lemonade Renters",
                cat["renters_insurance"],
            )
        )
        add(tx(checking.id, clamp_day(y, m, 9), -D("70.00"), "Google Fiber", cat["internet"]))
        add(tx(checking.id, clamp_day(y, m, 9), -D("80.00"), "Mint Mobile", cat["cell_phone"]))

        # ── Loan minimum payments (checking -> each debt) ─────────────────────
        for loan_id, amt, payee in (
            (card.id, D("270.00"), "Chase Sapphire Payment"),
            (personal.id, D("130.00"), "SoFi Personal Loan Payment"),
            (student.id, D("420.00"), "MOHELA Student Loan Payment"),
        ):
            d, c = transfer(
                checking.id, loan_id, clamp_day(y, m, 18), amt, payee, cat["loan_payment"]
            )
            add(d, c)

        # ── Savings + investing transfers ─────────────────────────────────────
        d, c = transfer(
            checking.id,
            emerg.id,
            clamp_day(y, m, 24),
            D("400.00"),
            "Ally Savings Transfer",
            cat["savings_transfer"],
        )
        add(d, c)
        d, c = transfer(
            checking.id,
            brokerage.id,
            clamp_day(y, m, 2),
            D("100.00"),
            "Fidelity Auto-Invest",
            cat["brokerage_contribution"],
        )
        add(d, c)
        if m <= 10:
            d, c = transfer(
                checking.id,
                roth_ira.id,
                clamp_day(y, m, 11),
                D("400.00"),
                "Fidelity Roth IRA",
                cat["ira_contribution"],
            )
            add(d, c)

        # ── Variable spending (debit/checking — not adding to the card) ───────
        spend: list = []

        def cv(slug, merchants, min_t, max_t, min_n, max_n, **kw):
            spend.extend(
                gen_variable(
                    checking.id,
                    y,
                    m,
                    cat[slug],
                    merchants,
                    D(str(min_t)),
                    D(str(max_t)),
                    min_n,
                    max_n,
                    rng,
                    **kw,
                )
            )

        cv(
            "groceries",
            ["Publix", "Kroger", "Trader Joe's", "Sprouts"],
            260,
            340,
            4,
            7,
            avoid_sunday=True,
        )
        cv(
            "restaurants",
            ["Busy Bee Cafe", "Slutty Vegan", "Fox Bros BBQ", "Ponce City Market"],
            140,
            220,
            3,
            6,
        )
        cv("coffee", ["Brash Coffee", "Chrome Yellow", "Starbucks"], 40, 70, 4, 8)
        cv("gas_fuel", ["QuikTrip", "Shell", "RaceTrac"], 70, 110, 2, 4)
        cv("personal_care", ["Sephora", "CVS", "Local Barber"], 35, 75, 1, 2)
        cv("pharmacy", ["CVS Pharmacy", "Walgreens"], 18, 45, 0, 2)
        cv("clothing", ["Target", "ASOS", "Nike Atlanta"], 50, 120, 0, 2)
        cv("hobbies", ["Steam", "REI", "Ponce City Market"], 30, 80, 0, 2)
        add(tx(checking.id, clamp_day(y, m, 10), -D("11.00"), "Spotify", cat["streaming"]))
        add(
            tx(
                checking.id,
                clamp_day(y, m, 14),
                -D("32.00"),
                "Amazon Prime + iCloud",
                cat["subscriptions"],
            )
        )
        add(
            tx(checking.id, clamp_day(y, m, 3), -D("39.00"), "Orangetheory Midtown", cat["fitness"])
        )

        # Seasonal travel + gifts
        if m == 7:
            cv("travel", ["Delta Air Lines", "Airbnb Savannah"], 600, 950, 1, 3)
        if m == 12:
            cv("gifts_given", ["Amazon", "Ponce City Market"], 250, 450, 2, 4)

        add(*spend)

    # ── Opening balances (set Jun-2026 transaction balances) ──────────────────
    targets: dict[uuid.UUID, D] = {
        checking.id: D("3800.00"),
        emerg.id: D("9500.00"),
        card.id: D("-9000.00"),
        personal.id: D("-4000.00"),
        student.id: D("-40000.00"),
    }
    for acc_id, target in targets.items():
        session.add(
            opening_balance_tx(acc_id, target - running[acc_id], cat.get("between_accounts"))
        )

    session.add_all(all_txns)

    # ── FIRE scenario (long runway, single earner, FI by 50) ──────────────────
    fire = make_fire_scenario(
        hid,
        aaliyah.id,
        "Financial Independence by 50",
        D("70000.00"),
        D("0.0750"),
        D("0.0300"),
        50,
        [
            {
                "id": str(uuid.uuid4()),
                "label": "Aaliyah — Software Engineer",
                "type": "salary",
                "amount_annual": 150000.00,
                "start_year": 2024,
                "end_year": 2049,
                "growth_rate_annual": 0.05,
                "is_pre_retirement": True,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Aaliyah Social Security (age 67)",
                "type": "social_security",
                "amount_annual": 36000.00,
                "start_year": 2066,
                "end_year": None,
                "growth_rate_annual": 0.025,
                "is_pre_retirement": False,
            },
        ],
    )
    session.add(fire)

    # ── Debt records (engineered so avalanche != snowball) ────────────────────
    # Avalanche (by rate): card 21% -> personal 11% -> student 6%.
    # Snowball (by balance): personal $4k -> card $9k -> student $40k.
    # First target differs -> avalanche pays less interest -> "Avalanche saves $X".
    session.add(
        make_debt(
            card.id, D("12000.00"), D("9000.00"), D("0.2100"), D("270.00"), 60, date(2023, 6, 1)
        )
    )
    session.add(
        make_debt(
            personal.id, D("6000.00"), D("4000.00"), D("0.1100"), D("130.00"), 36, date(2024, 1, 1)
        )
    )
    session.add(
        make_debt(
            student.id,
            D("48000.00"),
            D("40000.00"),
            D("0.0600"),
            D("420.00"),
            120,
            date(2019, 9, 1),
        )
    )

    # ── Budgets ───────────────────────────────────────────────────────────────
    budget_rows = [
        ("rent", D("1650.00"), date(2024, 1, 1)),
        ("renters_insurance", D("18.00"), date(2024, 1, 1)),
        ("groceries", D("300.00"), date(2024, 1, 1)),
        ("restaurants", D("180.00"), date(2024, 1, 1)),
        ("coffee", D("55.00"), date(2024, 1, 1)),
        ("gas_fuel", D("90.00"), date(2024, 1, 1)),
        ("internet", D("70.00"), date(2024, 1, 1)),
        ("cell_phone", D("80.00"), date(2024, 1, 1)),
        ("streaming", D("11.00"), date(2024, 1, 1)),
        ("subscriptions", D("32.00"), date(2024, 1, 1)),
        ("fitness", D("39.00"), date(2024, 1, 1)),
        ("personal_care", D("55.00"), date(2024, 1, 1)),
        ("pharmacy", D("30.00"), date(2024, 1, 1)),
        ("clothing", D("85.00"), date(2024, 1, 1)),
        ("hobbies", D("55.00"), date(2024, 1, 1)),
        ("travel", D("130.00"), date(2024, 1, 1)),
        ("gifts_given", D("60.00"), date(2024, 1, 1)),
    ]
    for slug, amount, eff_from in budget_rows:
        session.add(make_budget(hid, cat[slug], amount, eff_from))

    # ── Summary ───────────────────────────────────────────────────────────────
    # ReportService-computed net worth as of 2026-06-21 (end of seed window).
    # Liabilities are valued from the amortizing transaction balances (card $9k +
    # personal $4k + student $40k = $53k), not the loans' original principal.
    return {
        "num": 7,
        "name": "Brooks",
        "location": "Atlanta GA",
        "members": 1,
        "accounts": 9,
        "transactions": len(all_txns),
        "properties": 0,
        "net_worth": 12_184.37,  # reconciled to ReportService.current_net_worth (2026-06-21)
        "fire_scenarios": 1,
        "debt_records": 3,
    }
