"""Household 1 — Chen-Nakamura (Round Rock, TX). ~$1.0M net worth."""

from __future__ import annotations

import random
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from seed_households._util import (
    all_months,
    build_snapshots,
    clamp_day,
    gen_variable,
    last_day_of,
    make_account,
    make_advisory_note,
    make_budget,
    make_debt,
    make_equity_grant,
    make_fire_scenario,
    make_household,
    make_insurance_policy,
    make_investment_lot,
    make_member,
    make_property,
    make_user,
    make_valuation,
    make_vesting_event,
    opening_balance_tx,
    snapshot,
    transfer,
    tx,
)
from seed_households.shared_categories import seed_categories

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

D = Decimal


async def seed(session: AsyncSession, rng: random.Random) -> dict:
    # ── Household ─────────────────────────────────────────────────────────────
    hh = make_household("Chen-Nakamura Household")
    session.add(hh)
    hid = hh.id

    # ── Members ───────────────────────────────────────────────────────────────
    wei = make_member(hid, "Wei Chen", "primary", date_of_birth=date(1982, 4, 15))
    priya = make_member(hid, "Priya Nakamura", "partner", date_of_birth=date(1984, 9, 23))
    session.add_all([wei, priya])

    # ── Users ─────────────────────────────────────────────────────────────────
    user_wei = make_user(wei.id, "wei@chen-nakamura.local")
    user_priya = make_user(priya.id, "priya@chen-nakamura.local")
    session.add_all([user_wei, user_priya])
    await session.flush()  # household/member/user rows must be in DB before accounts reference them

    # ── Categories ────────────────────────────────────────────────────────────
    cat = await seed_categories(session, hid)

    # ── Accounts ──────────────────────────────────────────────────────────────
    def acc(atype, name, inst, last4, *, owner=None, in_nw=True):
        a = make_account(
            hid, atype, name, inst, last4, owner_member_id=owner, include_in_net_worth=in_nw
        )
        session.add(a)
        return a

    checking = acc("checking", "Primary Checking", "Dell Credit Union", "4821")
    savings = acc("savings", "High-Yield Savings", "Marcus by Goldman Sachs", "9312")
    wei_401k = acc("retirement_401k", "Dell 401(k)", "Fidelity NetBenefits", "7704", owner=wei.id)
    priya_403b = acc("retirement_403b", "St. David's 403(b)", "Vanguard", "8831", owner=priya.id)
    wei_roth = acc("retirement_roth_ira", "Roth IRA", "Fidelity", "2267", owner=wei.id)
    priya_roth = acc("retirement_roth_ira", "Roth IRA", "Vanguard", "3349", owner=priya.id)
    brokerage = acc("investment_brokerage", "Joint Brokerage", "Fidelity", "5513")
    hsa = acc("hsa", "HSA", "Optum Bank", "6621", owner=wei.id)
    cc_sapphire = acc("credit_card", "Sapphire Preferred", "Chase", "9008")
    rav4_loan = acc(
        "auto_loan", "RAV4 Auto Loan", "Toyota Financial Services", "2205", owner=priya.id
    )
    mortgage = acc("mortgage", "Home Mortgage", "University Federal Credit Union", "7761")
    home_re = acc("real_estate", "1842 Sunrise Ridge Dr", "—", None)

    # ── Real estate ───────────────────────────────────────────────────────────
    prop_home = make_property(
        home_re.id,
        "1842 Sunrise Ridge Dr, Round Rock, TX 78665",
        "primary_residence",
        date(2019, 3, 15),
        D("385000.00"),
        linked_mortgage_id=mortgage.id,
    )
    session.add(prop_home)
    await session.flush()  # real_estate_properties must exist before property_valuations FK check

    for val_date, val_amt in [
        (date(2024, 1, 1), D("598000.00")),
        (date(2024, 4, 1), D("612000.00")),
        (date(2024, 7, 1), D("628000.00")),
        (date(2024, 10, 1), D("641000.00")),
        (date(2025, 1, 1), D("648000.00")),
        (date(2025, 4, 1), D("655000.00")),
        (date(2025, 7, 1), D("658000.00")),
        (date(2025, 10, 1), D("661000.00")),
        (date(2026, 1, 1), D("663000.00")),
        (date(2026, 6, 1), D("665000.00")),
    ]:
        session.add(make_valuation(prop_home.id, val_date, val_amt))

    # ── Account snapshots (investment accounts) ────────────────────────────────
    # Q3 2024 market drawdown that recovers through normal growth by mid-2025, so
    # the net-worth series is non-monotonic (spec C.1).
    dips_market = {
        last_day_of(2024, 7): -0.025,
        last_day_of(2024, 8): -0.035,
        last_day_of(2024, 9): -0.02,
    }

    ira_contribs: dict[date, D] = {}
    for y in (2024, 2025, 2026):
        for mo in range(1, 6):
            ira_contribs[last_day_of(y, mo)] = D("500.00")

    brokerage_contribs: dict[date, D] = {}
    for month_start in all_months():
        y2, m2 = month_start.year, month_start.month
        if month_start < date(2026, 6, 1):
            amt = D("2000.00") if m2 == 6 else D("0.00") if m2 == 12 else D("1000.00")
            brokerage_contribs[last_day_of(y2, m2)] = amt

    hsa_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("358.00")
        for month_start in all_months()
        if month_start < date(2026, 6, 1)
        for y2, m2 in [(month_start.year, month_start.month)]
    }

    # 401k: employee $1,917/mo + employer match $383/mo = $2,300/mo
    k401_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("2300.00")
        for month_start in all_months()
        if month_start < date(2026, 6, 1)
        for y2, m2 in [(month_start.year, month_start.month)]
    }
    # Priya 403b: $1,708/mo
    b403_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("1708.00")
        for month_start in all_months()
        if month_start < date(2026, 6, 1)
        for y2, m2 in [(month_start.year, month_start.month)]
    }

    session.add_all(build_snapshots(wei_401k.id, D("158200.00"), k401_contribs, 0.09, dips_market))
    session.add_all(build_snapshots(priya_403b.id, D("67400.00"), b403_contribs, 0.09, dips_market))
    session.add_all(build_snapshots(wei_roth.id, D("34100.00"), ira_contribs, 0.09, dips_market))
    session.add_all(build_snapshots(priya_roth.id, D("22800.00"), ira_contribs, 0.09, dips_market))
    session.add_all(
        build_snapshots(brokerage.id, D("51200.00"), brokerage_contribs, 0.09, dips_market)
    )
    session.add_all(build_snapshots(hsa.id, D("7600.00"), hsa_contribs, 0.09, dips_market))
    session.add(snapshot(mortgage.id, last_day_of(2026, 5), D("-298700.00")))

    # ── Transaction generation ────────────────────────────────────────────────
    all_txns: list = []
    # Track running totals per transaction-based account for opening balance
    running: dict[uuid.UUID, D] = {
        checking.id: D("0"),
        savings.id: D("0"),
        cc_sapphire.id: D("0"),
        rav4_loan.id: D("0"),
        mortgage.id: D("0"),
    }

    def add(*txs):
        for t in txs:
            all_txns.append(t)
            if t.account_id in running:
                running[t.account_id] += t.amount

    summer_months = {6, 7, 8, 9}
    winter_months = {11, 12, 1, 2}

    for month_start in all_months():
        y, m = month_start.year, month_start.month

        # ── Income ────────────────────────────────────────────────────────────
        for day in (7, 21):
            dt = clamp_day(y, m, day)
            add(tx(checking.id, dt, D("3425.00"), "Dell Technologies Payroll", cat["salary"]))
        for day in (1, 15):
            dt = clamp_day(y, m, day)
            add(tx(checking.id, dt, D("2875.00"), "Ascension Health Payroll", cat["salary"]))

        if m == 4:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 15),
                    D("2100.00"),
                    "IRS TREAS 310",
                    cat["tax_refund"],
                )
            )

        # ── Fixed checking outflows ────────────────────────────────────────────
        # Mortgage (transfer to mortgage account)
        d, c = transfer(
            checking.id,
            mortgage.id,
            clamp_day(y, m, 5),
            D("1828.00"),
            "University Federal CU",
            cat["mortgage_payment"],
        )
        add(d, c)

        # Utilities (direct from checking)
        add(
            tx(
                checking.id,
                clamp_day(y, m, 10),
                -D("62.00"),
                "City of Round Rock Utilities",
                cat["water_sewer"],
            )
        )
        elec = D("195.00") if m in summer_months else D("142.00")
        add(tx(checking.id, clamp_day(y, m, 10), -elec, "Oncor Electric", cat["electric"]))
        gas_amt = D("89.00") if m in winter_months else D("38.00")
        add(tx(checking.id, clamp_day(y, m, 12), -gas_amt, "Atmos Gas", cat["gas_heating"]))

        # Brokerage auto-invest
        d, c = transfer(
            checking.id,
            brokerage.id,
            clamp_day(y, m, 15),
            D("1000.00"),
            "Fidelity Auto-Invest",
            cat["brokerage_contribution"],
        )
        add(d, c)

        # Auto loan payment
        d, c = transfer(
            checking.id,
            rav4_loan.id,
            clamp_day(y, m, 22),
            D("312.00"),
            "Toyota Financial Services",
            cat["loan_payment"],
        )
        add(d, c)

        # IRA contributions Jan-May
        if m in (1, 2, 3, 4, 5):
            d, c = transfer(
                checking.id,
                wei_roth.id,
                clamp_day(y, m, 11),
                D("1400.00"),
                "Fidelity — Roth IRA",
                cat["ira_contribution"],
            )
            add(d, c)
            d, c = transfer(
                checking.id,
                priya_roth.id,
                clamp_day(y, m, 10),
                D("1400.00"),
                "Vanguard — Roth IRA",
                cat["ira_contribution"],
            )
            add(d, c)

        # ── CC variable spending ───────────────────────────────────────────────
        cc_this_month: list = []

        def cc_var(cat_slug, merchants, min_t, max_t, min_n, max_n, **kw):
            txns = gen_variable(
                cc_sapphire.id,
                y,
                m,
                cat[cat_slug],
                merchants,
                D(str(min_t)),
                D(str(max_t)),
                min_n,
                max_n,
                rng,
                **kw,
            )
            cc_this_month.extend(txns)

        cc_var(
            "groceries",
            ["H-E-B", "Costco", "Trader Joe's", "H-E-B Gas Station"],
            680,
            820,
            6,
            8,
            avoid_sunday=True,
        )
        cc_var(
            "restaurants",
            ["Torchy's Tacos", "Chuy's", "Pappasito's", "Uchi Austin", "Local Austin Bistro"],
            280,
            420,
            4,
            7,
        )
        cc_var("coffee", ["Starbucks", "Epoch Coffee", "Houndstooth Coffee"], 55, 95, 4, 8)
        cc_var("food_delivery", ["DoorDash", "Uber Eats"], 45, 90, 2, 4)
        cc_var("gas_fuel", ["H-E-B Gas", "Shell", "ExxonMobil"], 140, 180, 3, 5)

        # Fixed CC charges
        cc_this_month.append(
            tx(cc_sapphire.id, clamp_day(y, m, 3), -D("75.00"), "AT&T Fiber", cat["internet"])
        )
        cc_this_month.append(
            tx(cc_sapphire.id, clamp_day(y, m, 5), -D("110.00"), "T-Mobile", cat["cell_phone"])
        )
        for streaming_payee, streaming_amt in [
            ("Netflix", D("17.00")),
            ("Spotify", D("10.99")),
            ("Disney+", D("14.00")),
        ]:
            cc_this_month.append(
                tx(
                    cc_sapphire.id,
                    clamp_day(y, m, 7),
                    -streaming_amt,
                    streaming_payee,
                    cat["streaming"],
                )
            )
        cc_this_month.append(
            tx(
                cc_sapphire.id,
                clamp_day(y, m, 15),
                -D("186.00"),
                "USAA Auto Insurance",
                cat["auto_insurance"],
            )
        )
        cc_this_month.append(
            tx(
                cc_sapphire.id,
                clamp_day(y, m, 18),
                -D("89.00"),
                "Life Time Fitness",
                cat["fitness"],
            )
        )

        # Home insurance: Jan only
        if m == 1:
            cc_this_month.append(
                tx(
                    cc_sapphire.id,
                    date(y, 1, 8),
                    -D("165.00"),
                    "USAA Home Insurance",
                    cat["home_insurance"],
                )
            )

        cc_var("clothing", ["Target", "Amazon", "Old Navy"], 85, 200, 1, 3)
        cc_var("personal_care", ["CVS Beauty", "Ulta", "Great Clips"], 60, 120, 2, 3)
        for sub_payee in [
            ("Amazon Prime", D("14.99")),
            ("NYT", D("17.00")),
            ("Xbox Game Pass", D("15.00")),
        ]:
            cc_this_month.append(
                tx(
                    cc_sapphire.id,
                    clamp_day(y, m, 8),
                    -sub_payee[1],
                    sub_payee[0],
                    cat["subscriptions"],
                )
            )
        cc_var("events_tickets", ["Alamo Drafthouse", "Moody Center", "Live Nation"], 80, 200, 1, 3)
        if rng.random() < 0.65:
            cc_var("home_maintenance", ["Home Depot", "Lowe's", "Ace Hardware"], 50, 300, 0, 2)
        cc_var("pharmacy", ["CVS Pharmacy", "Walgreens"], 25, 65, 1, 2)
        if rng.random() < 0.25:
            cc_var("electronics", ["Best Buy", "Apple Store", "Amazon"], 80, 400, 0, 1)

        # ── Seasonal CC charges ────────────────────────────────────────────────
        if m == 3:
            cc_var("travel", ["Southwest Airlines", "VRBO", "Airbnb"], 1800, 2400, 2, 4)
        if m == 7:
            cc_var("travel", ["Delta Airlines", "Marriott", "REI"], 2200, 3100, 2, 4)
        if m == 11:
            cc_var("travel", ["American Airlines", "United Airlines"], 600, 900, 1, 2)
        if m == 12:
            cc_var("gifts_given", ["Amazon", "Nordstrom", "Local Shops"], 800, 1200, 2, 5)
        if m == 4:
            cc_this_month.append(
                tx(cc_sapphire.id, clamp_day(y, m, 20), -D("180.00"), "TurboTax", cat["tax_prep"])
            )
        if m == 1:
            cc_this_month.append(
                tx(
                    cc_sapphire.id,
                    date(y, 1, 20),
                    -D("250.00"),
                    "ABC Pest Control & HVAC",
                    cat["home_maintenance"],
                )
            )
        if m == 6:
            cc_var("lawn_garden", ["SiteOne Landscape", "Home Depot Garden"], 150, 350, 1, 2)

        add(*cc_this_month)

        # ── CC payment at month end ────────────────────────────────────────────
        cc_month_total = sum(abs(t.amount) for t in cc_this_month)
        if cc_month_total > 0:
            pay_day = clamp_day(y, m, 28)
            d, c = transfer(
                checking.id,
                cc_sapphire.id,
                pay_day,
                cc_month_total,
                "Chase Sapphire Statement Payment",
                cat["cc_payment"],
            )
            add(d, c)

    # ── Savings transfer (checking → savings each month) ───────────────────────
    for month_start in all_months():
        y, m = month_start.year, month_start.month
        d, c = transfer(
            checking.id,
            savings.id,
            clamp_day(y, m, 25),
            D("1500.00"),
            "Transfer to High-Yield Savings",
            cat["savings_transfer"],
        )
        add(d, c)

    # ── Equity compensation: Wei's Dell ESPP (15% discount, 6-mo lookback) ──────
    # Contributions accrue each pay period; shares purchase semi-annually and are
    # sold shortly after, capturing the discount with minimal accumulation.
    espp = make_equity_grant(
        hid,
        wei.id,
        "espp",
        date(2024, 1, 1),
        D("0"),
        "DELL",
        espp_discount_pct=D("0.15"),
        espp_lookback=True,
    )
    session.add(espp)
    await session.flush()  # vesting_event FK references equity_grant
    for pdate, shares, fmv in [
        (date(2024, 6, 28), D("120"), D("138.00")),
        (date(2024, 12, 27), D("130"), D("121.00")),
        (date(2025, 6, 27), D("128"), D("129.00")),
        (date(2025, 12, 26), D("126"), D("142.00")),
    ]:
        discount_value = (shares * fmv * D("0.15")).quantize(D("0.01"))
        lot = make_investment_lot(
            brokerage.id, "DELL", shares, fmv * (D("1") - D("0.15")), pdate, "espp"
        )
        session.add(lot)
        await session.flush()  # vesting_event.resulting_lot_id references investment_lot
        session.add(
            make_vesting_event(espp.id, pdate, shares, fmv, discount_value, resulting_lot_id=lot.id)
        )
        # The 15% discount shows as supplemental income on the purchase date.
        add(tx(checking.id, pdate, discount_value, "Dell ESPP discount", cat["espp_purchase"]))

    # ── Insurance: condo HO-6 + umbrella + Wei's disability ─────────────────────
    session.add(
        make_insurance_policy(
            hid,
            "homeowners",
            D("750000"),
            D("1140"),
            "annual",
            carrier="USAA",
            policy_number="USAA-HO6-2021-7741883",
            technical_notes="HO-6 condo unit owners policy; personal property replacement cost",
            insured_real_estate_id=prop_home.id,
        )
    )
    session.add(
        make_insurance_policy(
            hid,
            "umbrella_liability",
            D("1000000"),
            D("228"),
            "annual",
            carrier="USAA",
            policy_number="UMB-2021-0044821",
            metadata={"underlying": ["auto", "home"]},
        )
    )
    session.add(
        make_insurance_policy(
            hid,
            "disability",
            D("72000"),
            D("142"),
            "monthly",
            insured_member_id=wei.id,
            carrier="Guardian",
            policy_number="GDI-0089-4412",
            metadata={"benefit_period": "to_age_65", "elimination_days": 90},
        )
    )
    for prem_year in (2024, 2025, 2026):
        add(
            tx(
                checking.id,
                date(prem_year, 3, 15),
                -D("228.00"),
                "USAA Umbrella Policy",
                cat["umbrella_premium"],
            )
        )
    for month_start in all_months():
        add(
            tx(
                checking.id,
                clamp_day(month_start.year, month_start.month, 6),
                -D("142.00"),
                "Guardian Disability",
                cat["disability_insurance_premium"],
            )
        )

    # ── Mega-backdoor Roth (after-tax 401(k) → in-plan Roth conversion) ─────────
    # Dell's plan (Fidelity NetBenefits) allows after-tax contributions beyond the
    # employee deferral limit with same-plan Roth conversion. Wei converts a
    # quarterly after-tax tranche to Roth; the conversion is an in-plan transfer,
    # so it moves dollars between snapshot-valued accounts without new cash.
    for yr in (2024, 2025):
        for q_month in (3, 6, 9, 12):
            d, c = transfer(
                wei_401k.id,
                wei_roth.id,
                date(yr, q_month, 15),
                D("4500.00"),
                "Dell 401(k) after-tax → in-plan Roth conversion",
                cat["roth_conversion"],
            )
            add(d, c)

    # ── Advisory notes ──────────────────────────────────────────────────────────
    session.add(
        make_advisory_note(
            hid,
            "retirement",
            "Mega-backdoor Roth: after-tax 401(k) contributions converted in-plan",
            "When a 401(k) plan allows after-tax (non-Roth) contributions plus in-plan Roth conversion, "
            "a high earner can move dollars well beyond the regular employee-deferral limit into Roth, "
            "up to the overall defined-contribution cap (employee + employer + after-tax). Converting "
            "promptly keeps the taxable gain on the after-tax portion near zero. Confirm the plan "
            "supports both features before relying on it — many do not — and watch the combined annual "
            "addition limit.",
            account_id=wei_roth.id,
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "insurance",
            "Umbrella coverage should at least equal net worth",
            "With net worth approaching $1M, a $1M umbrella liability policy is "
            "appropriate and inexpensive relative to the protection it provides "
            "(typically a few hundred dollars per $1M of coverage). Revisit the "
            "limit as net worth grows past the policy face amount.",
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "concentration",
            "Sell ESPP shares promptly to avoid employer-stock accumulation",
            "Selling ESPP shares shortly after each 6-month purchase captures the "
            "15% discount while avoiding an accidental concentrated position in "
            "Dell stock. Holding ESPP shares to chase a long-term capital gain "
            "trades a guaranteed discount for single-stock risk.",
        )
    )

    # ── Opening balance transactions ───────────────────────────────────────────
    targets = {
        checking.id: D("18200.00"),
        savings.id: D("58200.00"),
        cc_sapphire.id: D("-3200.00"),
        rav4_loan.id: D("-12400.00"),
        mortgage.id: D("-298700.00"),
    }
    for acc_id, target in targets.items():
        needed = target - running[acc_id]
        session.add(opening_balance_tx(acc_id, needed, cat.get("between_accounts")))

    session.add_all(all_txns)

    # ── FIRE scenario ──────────────────────────────────────────────────────────
    fire = make_fire_scenario(
        hid,
        wei.id,
        "Target 55 FIRE",
        D("95000.00"),
        D("0.0700"),
        D("0.0300"),
        55,
        [
            {
                "id": str(uuid.uuid4()),
                "label": "Wei — Dell salary",
                "type": "salary",
                "amount_annual": 115000.00,
                "start_year": 2024,
                "end_year": 2040,
                "growth_rate_annual": 0.03,
                "is_pre_retirement": True,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Priya — RN salary",
                "type": "salary",
                "amount_annual": 98000.00,
                "start_year": 2024,
                "end_year": 2039,
                "growth_rate_annual": 0.02,
                "is_pre_retirement": True,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Wei Social Security (age 67)",
                "type": "social_security",
                "amount_annual": 38000.00,
                "start_year": 2051,
                "end_year": None,
                "growth_rate_annual": 0.025,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Priya Social Security (age 67)",
                "type": "social_security",
                "amount_annual": 32000.00,
                "start_year": 2053,
                "end_year": None,
                "growth_rate_annual": 0.025,
                "is_pre_retirement": False,
            },
        ],
    )
    session.add(fire)

    # ── Debt record ───────────────────────────────────────────────────────────
    session.add(
        make_debt(
            rav4_loan.id,
            D("23500.00"),
            D("12400.00"),
            D("0.0589"),
            D("312.00"),
            60,
            date(2022, 3, 1),
        )
    )

    # ── Budgets ───────────────────────────────────────────────────────────────
    budget_rows = [
        ("groceries", D("750.00"), date(2024, 1, 1)),
        ("groceries", D("780.00"), date(2025, 1, 1)),
        ("restaurants", D("350.00"), date(2024, 1, 1)),
        ("coffee", D("75.00"), date(2024, 1, 1)),
        ("food_delivery", D("60.00"), date(2024, 1, 1)),
        ("gas_fuel", D("160.00"), date(2024, 1, 1)),
        ("electric", D("155.00"), date(2024, 1, 1)),
        ("internet", D("75.00"), date(2024, 1, 1)),
        ("cell_phone", D("110.00"), date(2024, 1, 1)),
        ("streaming", D("42.00"), date(2024, 1, 1)),
        ("auto_insurance", D("186.00"), date(2024, 1, 1)),
        ("fitness", D("89.00"), date(2024, 1, 1)),
        ("clothing", D("120.00"), date(2024, 1, 1)),
        ("personal_care", D("90.00"), date(2024, 1, 1)),
        ("events_tickets", D("120.00"), date(2024, 1, 1)),
        ("home_maintenance", D("150.00"), date(2024, 1, 1)),
        ("travel", D("400.00"), date(2024, 1, 1)),
        ("gifts_given", D("100.00"), date(2024, 1, 1)),
        ("subscriptions", D("47.00"), date(2024, 1, 1)),
        ("pharmacy", D("50.00"), date(2024, 1, 1)),
    ]
    for slug, amount, eff_from in budget_rows:
        session.add(make_budget(hid, cat[slug], amount, eff_from))

    # ── Summary ───────────────────────────────────────────────────────────────
    # ReportService-computed net worth as of 2026-06-21 (end of seed window).
    return {
        "num": 1,
        "name": "Chen-Nakamura",
        "location": "Round Rock TX",
        "members": 2,
        "accounts": 12,
        "transactions": len(all_txns),
        "properties": 1,
        "net_worth": 1_003_292.0,
        "fire_scenarios": 1,
        "debt_records": 1,
    }
