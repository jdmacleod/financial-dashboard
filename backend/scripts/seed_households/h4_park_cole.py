"""Household 4 — Park-Cole (East Nashville, TN). ~$154,500 net worth.

Members: Zoe Park (primary, b. 1998-05-12) and Marcus Cole (partner, b. 1997-09-03).
Late-20s dual-income renters. Aggressive debt payoff (avalanche) with 3 simultaneous
loans. Named savings goal brokerage (House Fund). Aspirational FIRE by 45.
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

# Honda Accord pays off after 19 full $812 payments + 1 final payment.
# Full payments: Jan 2024 – Jul 2025 (months 1-19)
# Final payment: Aug 2025 (month 20). Balance going into Aug 2025 ≈ $250.28.
_HONDA_FINAL_MONTH = date(2025, 8, 1)
_HONDA_FINAL_PAYMENT = D("251.72")  # balance + one month interest

# Zoe Student Loan payment increases after Honda payoff.
# From Sep 2025: $675 → $775/mo (cascaded $500 extra).
_ZOE_STUDENT_INCREASE_MONTH = date(2025, 9, 1)

# Third paycheck months (same each year for simplicity).
_ZOE_THIRD_PAYCHECK_MONTHS = {3, 8, 11}   # March, August, November
_MARCUS_THIRD_PAYCHECK_MONTHS = {1, 6, 11}  # January, June, November


async def seed(session: AsyncSession, rng: random.Random) -> dict:
    # ── Household ─────────────────────────────────────────────────────────────
    hh = make_household("Park-Cole Household")
    session.add(hh)
    hid = hh.id

    # ── Members ───────────────────────────────────────────────────────────────
    zoe = make_member(hid, "Zoe Park", "primary", date_of_birth=date(1998, 5, 12))
    marcus = make_member(hid, "Marcus Cole", "partner", date_of_birth=date(1997, 9, 3))
    session.add_all([zoe, marcus])

    # ── Users ─────────────────────────────────────────────────────────────────
    session.add(make_user(zoe.id, "zoe@park-cole.local"))
    session.add(make_user(marcus.id, "marcus@park-cole.local"))
    await session.flush()

    # ── Categories ────────────────────────────────────────────────────────────
    cat = await seed_categories(session, hid)

    # ── Accounts ──────────────────────────────────────────────────────────────
    def acc(atype, name, inst, last4, *, owner=None, in_nw=True):
        a = make_account(hid, atype, name, inst, last4, owner_member_id=owner,
                         include_in_net_worth=in_nw)
        session.add(a)
        return a

    # Transaction-tracked accounts
    checking    = acc("checking",           "Joint Checking",          "Ally Bank",              "4492")
    emerg       = acc("savings",            "Emergency Fund",          "Ally Bank",              "5513")
    chase_cc    = acc("credit_card",        "Freedom Unlimited",       "Chase",                  "3280")
    apple_cc    = acc("credit_card",        "Apple Card",              "Goldman Sachs",          "4381", owner=zoe.id)
    zoe_sl      = acc("student_loan",       "Federal Student Loan",    "MOHELA",                 "5492", owner=zoe.id)
    marcus_sl   = acc("student_loan",       "Federal Student Loan",    "MOHELA",                 "6503", owner=marcus.id)
    honda       = acc("auto_loan",          "Honda Accord Auto Loan",  "Tennessee CU",           "7614", owner=marcus.id)

    # Snapshot-tracked accounts (balance from build_snapshots; no running-balance needed)
    house_fund  = acc("investment_brokerage", "House Fund",            "Fidelity",               "6624")
    zoe_401k    = acc("retirement_401k",    "Roth 401(k)",             "Guideline",              "7735", owner=zoe.id)
    marcus_401k = acc("retirement_401k",    "401(k)",                  "Fidelity (HCA)",         "8846", owner=marcus.id)
    zoe_roth    = acc("retirement_roth_ira","Roth IRA",                "Fidelity",               "9957", owner=zoe.id)
    marcus_roth = acc("retirement_roth_ira","Roth IRA",                "Vanguard",               "1068", owner=marcus.id)
    zoe_hsa     = acc("hsa",               "HSA",                     "HealthEquity",            "2179", owner=zoe.id)

    await session.flush()

    # ── Investment account snapshots ──────────────────────────────────────────
    oct24 = last_day_of(2024, 10)
    dips = {oct24: -0.035}

    # Zoe Roth 401(k): $390/mo from Guideline payroll; 8.5% annual return
    z401k_contribs = {last_day_of(y, m): D("390.00")
                      for ms in all_months() if ms < date(2026, 6, 1)
                      for y, m in [(ms.year, ms.month)]}
    session.add_all(build_snapshots(zoe_401k.id, D("14200.00"), z401k_contribs, 0.085, dips))

    # Marcus 401(k): $440/mo employee + $293/mo employer match = $733/mo; 8.5%
    m401k_contribs = {last_day_of(y, m): D("733.00")
                      for ms in all_months() if ms < date(2026, 6, 1)
                      for y, m in [(ms.year, ms.month)]}
    session.add_all(build_snapshots(marcus_401k.id, D("32400.00"), m401k_contribs, 0.085, dips))

    # Zoe Roth IRA: $583/mo Jan-Oct, $0 Nov-Dec; 8.5%
    zroth_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms >= date(2026, 6, 1):
            break
        y, m = ms.year, ms.month
        zroth_contribs[last_day_of(y, m)] = D("583.00") if m <= 10 else D("0.00")
    session.add_all(build_snapshots(zoe_roth.id, D("7800.00"), zroth_contribs, 0.085, dips))

    # Marcus Roth IRA: $583/mo Jan-Oct, $0 Nov-Dec; 8.5%
    mroth_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms >= date(2026, 6, 1):
            break
        y, m = ms.year, ms.month
        mroth_contribs[last_day_of(y, m)] = D("583.00") if m <= 10 else D("0.00")
    session.add_all(build_snapshots(marcus_roth.id, D("5200.00"), mroth_contribs, 0.085, dips))

    # Zoe HSA: $358/mo all year; 8.5%
    hsa_contribs = {last_day_of(y, m): D("358.00")
                    for ms in all_months() if ms < date(2026, 6, 1)
                    for y, m in [(ms.year, ms.month)]}
    session.add_all(build_snapshots(zoe_hsa.id, D("2200.00"), hsa_contribs, 0.085, dips))

    # House Fund brokerage: $2,000/mo; 6.5% (conservative 60/40 allocation)
    hf_contribs = {last_day_of(y, m): D("2000.00")
                   for ms in all_months() if ms < date(2026, 6, 1)
                   for y, m in [(ms.year, ms.month)]}
    session.add_all(build_snapshots(house_fund.id, D("42000.00"), hf_contribs, 0.065, dips))

    # ── Transaction generation ────────────────────────────────────────────────
    all_txns: list = []
    running: dict[uuid.UUID, D] = {
        checking.id:    D("0"),
        emerg.id:       D("0"),
        chase_cc.id:    D("0"),
        apple_cc.id:    D("0"),
        zoe_sl.id:      D("0"),
        marcus_sl.id:   D("0"),
        honda.id:       D("0"),
    }

    def add(*txs):
        for t in txs:
            all_txns.append(t)
            if t.account_id in running:
                running[t.account_id] += t.amount

    honda_active = True  # becomes False after payoff

    for month_start in all_months():
        y, m = month_start.year, month_start.month
        if month_start > DATE_END:
            break

        # ── Income: biweekly paychecks ────────────────────────────────────────
        # Zoe: 7th and 21st of each month ($2,210/check)
        for day in (7, 21):
            add(tx(checking.id, clamp_day(y, m, day), D("2210.00"),
                   "DataOps Inc. Payroll", cat["salary"]))
        if m in _ZOE_THIRD_PAYCHECK_MONTHS:
            add(tx(checking.id, clamp_day(y, m, 14), D("2210.00"),
                   "DataOps Inc. Payroll", cat["salary"]))

        # Marcus: 1st and 15th of each month ($2,870/check)
        for day in (1, 15):
            add(tx(checking.id, clamp_day(y, m, day), D("2870.00"),
                   "HCA Healthcare Payroll", cat["salary"]))
        if m in _MARCUS_THIRD_PAYCHECK_MONTHS:
            add(tx(checking.id, clamp_day(y, m, 8), D("2870.00"),
                   "HCA Healthcare Payroll", cat["salary"]))

        # Annual federal tax refund in April
        if m == 4:
            add(tx(checking.id, clamp_day(y, m, 15), D("1650.00"),
                   "IRS TREAS 310", cat["tax_refund"]))

        # ── Fixed checking outflows ────────────────────────────────────────────

        # Rent
        add(tx(checking.id, clamp_day(y, m, 1), -D("1875.00"),
               "4th Ave Partners", cat["rent"]))

        # Renters insurance (monthly installment)
        add(tx(checking.id, clamp_day(y, m, 5), -D("22.00"),
               "State Farm Renters", cat["renters_insurance"]))

        # Internet
        add(tx(checking.id, clamp_day(y, m, 10), -D("68.00"),
               "Comcast Xfinity", cat["internet"]))

        # Cell phone (T-Mobile 2 lines)
        add(tx(checking.id, clamp_day(y, m, 10), -D("95.00"),
               "T-Mobile", cat["cell_phone"]))

        # Auto insurance (Marcus only has the Honda)
        add(tx(checking.id, clamp_day(y, m, 12), -D("124.00"),
               "Progressive Auto Insurance", cat["auto_insurance"]))

        # House Fund auto-invest: checking → house_fund brokerage
        d, c = transfer(checking.id, house_fund.id, clamp_day(y, m, 1),
                        D("2000.00"), "Fidelity House Fund Auto-Invest",
                        cat["brokerage_contribution"])
        add(d, c)

        # Monthly savings transfer: checking → emergency fund
        d, c = transfer(checking.id, emerg.id, clamp_day(y, m, 25),
                        D("600.00"), "Ally Bank Savings Transfer",
                        cat["savings_transfer"])
        add(d, c)

        # ── Loan payments ─────────────────────────────────────────────────────

        # Honda Accord: $812/mo until payoff, then final small payment, then done
        if honda_active:
            if month_start < _HONDA_FINAL_MONTH:
                d, c = transfer(checking.id, honda.id, clamp_day(y, m, 15),
                                D("812.00"), "Tennessee CU Auto Loan",
                                cat["loan_payment"])
                add(d, c)
            elif month_start == _HONDA_FINAL_MONTH:
                d, c = transfer(checking.id, honda.id, clamp_day(y, m, 15),
                                _HONDA_FINAL_PAYMENT, "Tennessee CU Auto Loan — Final",
                                cat["loan_payment"])
                add(d, c)
                honda_active = False

        # Zoe Student Loan: $675/mo → $775/mo after Honda payoff
        zoe_sl_payment = D("775.00") if month_start >= _ZOE_STUDENT_INCREASE_MONTH else D("675.00")
        d, c = transfer(checking.id, zoe_sl.id, clamp_day(y, m, 20),
                        zoe_sl_payment, "MOHELA — Zoe Student Loan",
                        cat["loan_payment"])
        add(d, c)

        # Marcus Student Loan: $182/mo minimum (cascade won't reach within data window)
        d, c = transfer(checking.id, marcus_sl.id, clamp_day(y, m, 20),
                        D("182.00"), "MOHELA — Marcus Student Loan",
                        cat["loan_payment"])
        add(d, c)

        # ── IRA contributions Jan–Oct each year ───────────────────────────────
        if m <= 10:
            d, c = transfer(checking.id, zoe_roth.id, clamp_day(y, m, 11),
                            D("583.00"), "Fidelity — Roth IRA",
                            cat["ira_contribution"])
            add(d, c)
            d, c = transfer(checking.id, marcus_roth.id, clamp_day(y, m, 12),
                            D("583.00"), "Vanguard — Roth IRA",
                            cat["ira_contribution"])
            add(d, c)

        # ── Chase Freedom variable spending ───────────────────────────────────
        chase_txns: list = []

        def cv(slug, merchants, min_t, max_t, min_n, max_n, **kw):
            txns = gen_variable(chase_cc.id, y, m, cat[slug], merchants,
                                D(str(min_t)), D(str(max_t)), min_n, max_n, rng, **kw)
            chase_txns.extend(txns)

        cv("groceries",
           ["Kroger", "Whole Foods", "Trader Joe's", "Costco"],
           480, 580, 5, 8, avoid_sunday=True)
        cv("restaurants",
           ["Butcher & Bee", "Biscuit Love", "Rolf & Daughters", "Husk Nashville",
            "Adele's Nashville", "Lockeland Table"],
           260, 380, 3, 6)
        cv("food_delivery", ["DoorDash", "Uber Eats"], 40, 85, 2, 4)
        cv("gas_fuel", ["Circle K", "Mapco", "Shell"], 95, 145, 3, 5)
        cv("events_tickets",
           ["Ryman Auditorium", "Bridgestone Arena", "Live Nation Nashville",
            "Broadway Honky-Tonk"],
           60, 180, 0, 3)
        cv("subscriptions",
           ["Amazon Prime", "NYT", "Xbox Game Pass"], 32, 32, 1, 1)

        # Fixed on Chase Freedom
        chase_txns.append(tx(chase_cc.id, clamp_day(y, m, 8), -D("124.00"),
                             "Progressive Auto Insurance", cat["auto_insurance"], memo="chase_skip"))

        # Remove the auto insurance duplicate (we charged it to checking above)
        # Actually per spec: auto_insurance ($124.00) is from Checking. Chase gets other spend.
        # Remove the chase auto_insurance line just added:
        chase_txns.pop()  # remove the erroneous auto insurance we just added

        if rng.random() < 0.6:
            cv("car_maintenance", ["Jiffy Lube", "Midas", "Firestone"], 60, 220, 0, 1)
        if rng.random() < 0.35:
            cv("home_goods", ["IKEA", "Target Home"], 80, 250, 0, 1)

        # ── Apple Card variable spending ───────────────────────────────────────
        apple_txns: list = []

        def av(slug, merchants, min_t, max_t, min_n, max_n, **kw):
            txns = gen_variable(apple_cc.id, y, m, cat[slug], merchants,
                                D(str(min_t)), D(str(max_t)), min_n, max_n, rng, **kw)
            apple_txns.extend(txns)

        av("coffee",
           ["Frothy Monkey", "Steadfast Coffee", "Crema Coffee", "Starbucks"],
           55, 80, 4, 8)
        av("streaming",
           ["Netflix", "Hulu", "Spotify"], 42, 42, 1, 1)
        av("clothing",
           ["Target", "Shein", "ThredUp", "ASOS"], 65, 150, 1, 3)
        av("personal_care",
           ["Ulta", "CVS Beauty", "Walgreens", "Local Barbershop"], 55, 100, 1, 3)
        av("pharmacy", ["Walgreens", "CVS Pharmacy"], 20, 55, 1, 2)
        if rng.random() < 0.5:
            av("hobbies", ["Disc Golf Warehouse", "REI", "ThredUp"], 30, 90, 0, 2)

        # Seasonal Apple Card charges
        if m == 8:
            av("electronics", ["Best Buy", "Apple Store", "Amazon"], 800, 1200, 1, 1)
        elif rng.random() < 0.2:
            av("electronics", ["Amazon", "Best Buy"], 30, 150, 0, 1)

        # ── Seasonal / annual (checking direct) ───────────────────────────────
        if m == 2:
            cv("travel", ["Airbnb", "VRBO", "Gas Station"], 350, 600, 1, 3)
        if m == 6:
            cv("travel", ["Southwest Airlines", "Marriott Phoenix"], 900, 1400, 2, 4)
        if m == 10:
            cv("travel", ["Gas Station Road Trip", "Local Hotel"], 550, 850, 1, 3)
        if m == 12:
            cv("gifts_given", ["Amazon", "Target", "Local Nashville Shops"], 400, 700, 2, 5)
        if m == 4:
            chase_txns.append(tx(chase_cc.id, clamp_day(y, m, 20), -D("65.00"),
                                 "TurboTax", cat["tax_prep"]))
        if m == 1:
            apple_txns.append(tx(apple_cc.id, clamp_day(y, m, 15), -D("200.00"),
                                 "IKEA Nashville", cat["home_goods"]))
        if m == 5:
            av("fitness", ["ClassPass", "Planet Fitness"], 58, 58, 1, 1)
        else:
            av("fitness", ["ClassPass", "Planet Fitness"], 58, 58, 1, 1)

        add(*chase_txns)
        add(*apple_txns)

        # ── CC payments (checking → each CC) ─────────────────────────────────
        chase_spend = abs(sum(t.amount for t in chase_txns if t.account_id == chase_cc.id
                              and t.amount < 0))
        if chase_spend > 0:
            d, c = transfer(checking.id, chase_cc.id, clamp_day(y, m, 27),
                            chase_spend, "Chase Freedom Statement Payment",
                            cat["cc_payment"])
            add(d, c)

        apple_spend = abs(sum(t.amount for t in apple_txns if t.account_id == apple_cc.id
                              and t.amount < 0))
        if apple_spend > 0:
            d, c = transfer(checking.id, apple_cc.id, clamp_day(y, m, 27),
                            apple_spend, "Apple Card Statement Payment",
                            cat["cc_payment"])
            add(d, c)

    # ── Opening balance transactions ───────────────────────────────────────────
    # Target = desired Jun 2026 balance (post-transaction).
    # Opening balance = target - running[acc_id].
    targets: dict[uuid.UUID, D] = {
        checking.id:   D("9400.00"),
        emerg.id:      D("35000.00"),
        chase_cc.id:   D("-2400.00"),
        apple_cc.id:   D("-1100.00"),
        zoe_sl.id:     D("-16421.00"),   # estimated Jun 2026 remaining balance
        marcus_sl.id:  D("-19011.00"),   # estimated Jun 2026 remaining balance
        honda.id:      D("0.00"),        # paid off Aug 2025
    }
    for acc_id, target in targets.items():
        needed = target - running[acc_id]
        session.add(opening_balance_tx(acc_id, needed, cat.get("between_accounts")))

    # Deactivate the Honda account after payoff
    honda.is_active = False

    session.add_all(all_txns)

    # ── FIRE scenario ─────────────────────────────────────────────────────────
    fire = make_fire_scenario(
        hid,
        zoe.id,
        "Financial Independence by 45",
        D("120000.00"),
        D("0.0750"),
        D("0.0300"),
        45,
        [
            {
                "id": str(uuid.uuid4()),
                "label": "Zoe — DataOps Product Designer",
                "type": "salary",
                "amount_annual": 78000.00,
                "start_year": 2024,
                "end_year": 2044,
                "growth_rate_annual": 0.04,
                "is_pre_retirement": True,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Marcus — HCA Healthcare Analyst",
                "type": "salary",
                "amount_annual": 88000.00,
                "start_year": 2024,
                "end_year": 2042,
                "growth_rate_annual": 0.035,
                "is_pre_retirement": True,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Zoe Social Security (age 67)",
                "type": "social_security",
                "amount_annual": 34000.00,
                "start_year": 2064,
                "end_year": None,
                "growth_rate_annual": 0.025,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Marcus Social Security (age 67)",
                "type": "social_security",
                "amount_annual": 38000.00,
                "start_year": 2064,
                "end_year": None,
                "growth_rate_annual": 0.025,
                "is_pre_retirement": False,
            },
        ],
    )
    session.add(fire)

    # ── Debt records ──────────────────────────────────────────────────────────
    session.add(make_debt(
        honda.id, D("18500.00"), D("14800.00"),
        D("0.0690"), D("312.00"), 60, date(2022, 3, 1),
    ))
    session.add(make_debt(
        zoe_sl.id, D("42000.00"), D("34000.00"),
        D("0.0550"), D("275.00"), 120, date(2021, 8, 1),
    ))
    session.add(make_debt(
        marcus_sl.id, D("28000.00"), D("22000.00"),
        D("0.0480"), D("182.00"), 120, date(2019, 6, 1),
    ))

    # ── Budgets ───────────────────────────────────────────────────────────────
    budget_rows = [
        # Housing
        ("rent",              D("1875.00"), date(2024, 1, 1)),
        ("renters_insurance", D("22.00"),   date(2024, 1, 1)),
        # Food & Dining
        ("groceries",         D("520.00"),  date(2024, 1, 1)),
        ("groceries",         D("560.00"),  date(2025, 6, 1)),   # food inflation
        ("restaurants",       D("300.00"),  date(2024, 1, 1)),
        ("restaurants",       D("340.00"),  date(2025, 1, 1)),   # lifestyle creep
        ("coffee",            D("65.00"),   date(2024, 1, 1)),
        ("food_delivery",     D("60.00"),   date(2024, 1, 1)),
        # Transportation
        ("gas_fuel",          D("120.00"),  date(2024, 1, 1)),
        ("auto_insurance",    D("124.00"),  date(2024, 1, 1)),
        # Utilities
        ("internet",          D("68.00"),   date(2024, 1, 1)),
        ("cell_phone",        D("95.00"),   date(2024, 1, 1)),
        ("streaming",         D("42.00"),   date(2024, 1, 1)),
        # Personal & Entertainment
        ("fitness",           D("58.00"),   date(2024, 1, 1)),
        ("clothing",          D("90.00"),   date(2024, 1, 1)),
        ("personal_care",     D("75.00"),   date(2024, 1, 1)),
        ("subscriptions",     D("32.00"),   date(2024, 1, 1)),
        ("events_tickets",    D("100.00"),  date(2024, 1, 1)),
        ("pharmacy",          D("40.00"),   date(2024, 1, 1)),
        ("travel",            D("150.00"),  date(2024, 1, 1)),
        ("gifts_given",       D("60.00"),   date(2024, 1, 1)),
    ]
    for slug, amount, eff_from in budget_rows:
        session.add(make_budget(hid, cat[slug], amount, eff_from))

    # ── Summary ───────────────────────────────────────────────────────────────
    snapshot_nw = (
        D("22400.00")   # Zoe Roth 401k (current)
        + D("46800.00") # Marcus 401k (current)
        + D("12200.00") # Zoe Roth IRA (current)
        + D("9400.00")  # Marcus Roth IRA (current)
        + D("5200.00")  # Zoe HSA (current)
        + D("88400.00") # House Fund (current)
    )
    tx_nw = sum(targets.values())

    return {
        "num": 4,
        "name": "Park-Cole",
        "location": "Nashville TN",
        "members": 2,
        "accounts": 13,
        "transactions": len(all_txns),
        "properties": 0,
        "net_worth": float(snapshot_nw + tx_nw),
        "fire_scenarios": 1,
        "debt_records": 3,
    }
