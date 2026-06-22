"""Household 5 — Langford (Sarasota, FL). ~$12,856,700 net worth.

Members: Robert ("Bob") Langford (primary, b. 1952-02-18) and
Margaret ("Maggie") Langford (partner, b. 1962-09-14).
Retired couple; Bob receives SS + pension + quarterly RMDs. Maggie runs a
part-time HR consulting LLC. Two real estate properties (Sarasota primary
cash purchase; Highlands NC vacation home with low-rate 30yr mortgage).
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
    make_advisory_note,
    make_budget,
    make_debt,
    make_fire_scenario,
    make_household,
    make_insurance_policy,
    make_member,
    make_ownership_entity,
    make_property,
    make_user,
    make_valuation,
    opening_balance_tx,
    snapshot,
    third_wednesday,
    transfer,
    tx,
)
from seed_households.shared_categories import seed_categories

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

D = Decimal


async def seed(session: AsyncSession, rng: random.Random) -> dict:
    # ── Household ─────────────────────────────────────────────────────────────
    hh = make_household("Langford Household")
    session.add(hh)
    hid = hh.id

    # ── Members ───────────────────────────────────────────────────────────────
    bob = make_member(hid, "Bob Langford", "primary", date_of_birth=date(1952, 2, 18))
    maggie = make_member(hid, "Maggie Langford", "partner", date_of_birth=date(1962, 9, 14))
    session.add_all([bob, maggie])

    # ── Users ─────────────────────────────────────────────────────────────────
    session.add(make_user(bob.id, "bob@langford.local"))
    session.add(make_user(maggie.id, "maggie@langford.local"))
    await session.flush()

    # ── Categories ────────────────────────────────────────────────────────────
    cat = await seed_categories(session, hid)

    # ── Accounts ──────────────────────────────────────────────────────────────
    def acc(atype, name, inst, last4, *, owner=None, in_nw=True):
        a = make_account(
            hid, atype, name, inst, last4, owner_member_id=owner, include_in_net_worth=in_nw
        )
        session.add(a)
        return a

    # Transaction-tracked
    checking = acc("checking", "Wealth Management Checking", "Truist Bank Private", "8847")
    premium_sav = acc("savings", "Premium Savings", "Truist Bank Private", "9958")
    schwab_mm = acc("savings", "Money Market (SWVXX)", "Schwab", "1069")
    llc_checking = acc(
        "checking", "Consulting LLC Checking", "Regions Bank", "2170", owner=maggie.id
    )
    centurion = acc("credit_card", "Centurion Card", "American Express", "9847", owner=bob.id)
    sapphire = acc("credit_card", "Sapphire Reserve", "Chase", "1058")
    highlands_mort = acc("mortgage", "Highlands NC Mortgage", "Bank of America", "2169")

    # Snapshot-tracked (balance from build_snapshots)
    bob_ira = acc("retirement_ira", "Bob Rollover IRA", "Schwab", "3281", owner=bob.id)
    maggie_ira = acc("retirement_ira", "Maggie Rollover IRA", "Schwab", "4392", owner=maggie.id)
    bob_roth = acc("retirement_roth_ira", "Bob Roth IRA", "Fidelity", "5403", owner=bob.id)
    maggie_roth = acc("retirement_roth_ira", "Maggie Roth IRA", "Vanguard", "6514", owner=maggie.id)
    joint_brok = acc("investment_brokerage", "Joint Taxable Brokerage", "Schwab", "7625")
    bob_brok = acc(
        "investment_brokerage", "Bob Individual Brokerage", "Fidelity", "8736", owner=bob.id
    )

    # Real estate accounts (balance from property valuations)
    sarasota_re = acc("real_estate", "Sarasota Primary Home", "—", None)
    highlands_re = acc("real_estate", "Highlands NC Vacation Home", "—", None)

    await session.flush()

    # ── Real estate properties ────────────────────────────────────────────────
    prop_sarasota = make_property(
        sarasota_re.id,
        "4217 Osprey Point Dr, Sarasota, FL 34242",
        "primary_residence",
        date(2022, 3, 18),
        D("2100000.00"),
        linked_mortgage_id=None,  # cash purchase
    )
    session.add(prop_sarasota)
    await session.flush()
    for val_date, val_amt in [
        (date(2024, 1, 1), D("2580000.00")),
        (date(2024, 7, 1), D("2650000.00")),
        (date(2025, 1, 1), D("2720000.00")),
        (date(2025, 7, 1), D("2780000.00")),
        (date(2026, 1, 1), D("2830000.00")),
        (date(2026, 6, 1), D("2850000.00")),
    ]:
        session.add(make_valuation(prop_sarasota.id, val_date, val_amt))

    prop_highlands = make_property(
        highlands_re.id,
        "118 Sunset Ridge Rd, Highlands, NC 28741",
        "vacation",
        date(2019, 6, 4),
        D("720000.00"),
        linked_mortgage_id=highlands_mort.id,
    )
    session.add(prop_highlands)
    await session.flush()
    for val_date, val_amt in [
        (date(2024, 1, 1), D("985000.00")),
        (date(2024, 7, 1), D("1010000.00")),
        (date(2025, 1, 1), D("1042000.00")),
        (date(2025, 7, 1), D("1068000.00")),
        (date(2026, 1, 1), D("1085000.00")),
        (date(2026, 6, 1), D("1095000.00")),
    ]:
        session.add(make_valuation(prop_highlands.id, val_date, val_amt))

    # ── Investment account snapshots ──────────────────────────────────────────
    oct24 = last_day_of(2024, 10)
    apr25 = last_day_of(2025, 4)
    brokerage_dips = {oct24: -0.040, apr25: -0.025}

    # Bob Rollover IRA: no contributions; RMD withdrawals reduce quarterly from 2025
    bob_ira_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms >= date(2026, 6, 1):
            break
        bob_ira_contribs[last_day_of(ms.year, ms.month)] = D("0")
    # Subtract RMD distributions from IRA balance
    bob_ira_contribs[last_day_of(2025, 3)] = -D("34896.00")
    bob_ira_contribs[last_day_of(2025, 6)] = -D("34896.00")
    bob_ira_contribs[last_day_of(2025, 9)] = -D("34896.00")
    bob_ira_contribs[last_day_of(2025, 12)] = -D("34897.00")
    bob_ira_contribs[last_day_of(2026, 3)] = -D("36530.00")
    session.add_all(build_snapshots(bob_ira.id, D("3450000.00"), bob_ira_contribs, 0.07))

    # Maggie Rollover IRA: SEP contributions lump-sum in January each year; 7%
    maggie_ira_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms >= date(2026, 6, 1):
            break
        y, m = ms.year, ms.month
        if m == 1:
            maggie_ira_contribs[last_day_of(y, m)] = D("58000.00") if y == 2024 else D("61000.00")
        else:
            maggie_ira_contribs[last_day_of(y, m)] = D("0")
    session.add_all(build_snapshots(maggie_ira.id, D("602000.00"), maggie_ira_contribs, 0.07))

    # Bob Roth IRA: $583/mo Jan-Oct (backdoor), 7%
    bob_roth_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms >= date(2026, 6, 1):
            break
        y, m = ms.year, ms.month
        bob_roth_contribs[last_day_of(y, m)] = D("583.00") if m <= 10 else D("0")
    session.add_all(build_snapshots(bob_roth.id, D("72000.00"), bob_roth_contribs, 0.07))

    # Maggie Roth IRA: $583/mo Jan-Oct (backdoor), 7%
    maggie_roth_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms >= date(2026, 6, 1):
            break
        y, m = ms.year, ms.month
        maggie_roth_contribs[last_day_of(y, m)] = D("583.00") if m <= 10 else D("0")
    session.add_all(build_snapshots(maggie_roth.id, D("88000.00"), maggie_roth_contribs, 0.07))

    # Joint Brokerage: $2,000/mo; 6.5%; -4% Oct 2024; -2.5% Apr 2025
    jb_contribs = {
        last_day_of(y, m): D("2000.00")
        for ms in all_months()
        if ms < date(2026, 6, 1)
        for y, m in [(ms.year, ms.month)]
    }
    session.add_all(
        build_snapshots(joint_brok.id, D("2780000.00"), jb_contribs, 0.065, brokerage_dips)
    )

    # Bob Individual Brokerage: $1,000/mo; 6.5%; same dips
    bb_contribs = {
        last_day_of(y, m): D("1000.00")
        for ms in all_months()
        if ms < date(2026, 6, 1)
        for y, m in [(ms.year, ms.month)]
    }
    session.add_all(
        build_snapshots(bob_brok.id, D("612000.00"), bb_contribs, 0.065, brokerage_dips)
    )

    # ── Transaction generation ────────────────────────────────────────────────
    all_txns: list = []
    running: dict[uuid.UUID, D] = {
        checking.id: D("0"),
        premium_sav.id: D("0"),
        schwab_mm.id: D("0"),
        llc_checking.id: D("0"),
        centurion.id: D("0"),
        sapphire.id: D("0"),
        highlands_mort.id: D("0"),
    }

    def add(*txs):
        for t in txs:
            all_txns.append(t)
            if t.account_id in running:
                running[t.account_id] += t.amount

    # Quarterly dividend schedule (payee, amount, months)
    _joint_div_by_q = {3: D("18500"), 6: D("19200"), 9: D("20100"), 12: D("21000")}
    _bob_div_by_q = {3: D("4200"), 6: D("4200"), 9: D("4200"), 12: D("4200")}

    for month_start in all_months():
        y, m = month_start.year, month_start.month
        if month_start > DATE_END:
            break

        # ── Healthcare premiums (Bob — Medicare) ──────────────────────────────
        if y < 2026:
            med_b_amt, med_d_amt, medigap_amt = D("280.00"), D("48.00"), D("192.00")
        else:
            med_b_amt, med_d_amt, medigap_amt = D("284.10"), D("49.00"), D("198.00")

        add(
            tx(
                checking.id,
                clamp_day(y, m, 1),
                -med_b_amt,
                "Medicare — Part B Premium",
                cat["medicare_part_b"],
            )
        )
        add(
            tx(
                checking.id,
                clamp_day(y, m, 1),
                -med_d_amt,
                "Medicare — Part D Premium",
                cat["medicare_part_d"],
            )
        )
        add(
            tx(
                checking.id,
                clamp_day(y, m, 3),
                -medigap_amt,
                "UnitedHealthcare Medigap Plan G",
                cat["medigap_supplement"],
            )
        )

        # ACA premium (Maggie — marketplace)
        if y < 2025:
            aca_amt = D("1165.00")
        elif y < 2026:
            aca_amt = D("1245.00")
        else:
            aca_amt = D("1310.00")
        add(
            tx(
                checking.id,
                clamp_day(y, m, 5),
                -aca_amt,
                "BCBS Florida ACA Marketplace",
                cat["aca_premium"],
            )
        )

        # ── Highlands NC mortgage ─────────────────────────────────────────────
        d, c = transfer(
            checking.id,
            highlands_mort.id,
            clamp_day(y, m, 1),
            D("1632.00"),
            "Bank of America Mortgage — Highlands NC",
            cat["mortgage_payment"],
        )
        add(d, c)

        # ── Sarasota HOA + condo fees ─────────────────────────────────────────
        add(tx(checking.id, clamp_day(y, m, 10), -D("895.00"), "Osprey Point HOA", cat["hoa_fees"]))

        # ── Utilities (Sarasota) ──────────────────────────────────────────────
        add(
            tx(
                checking.id,
                clamp_day(y, m, 15),
                -D("145.00"),
                "Florida Power & Light",
                cat["electric"],
            )
        )
        add(
            tx(
                checking.id,
                clamp_day(y, m, 15),
                -D("68.00"),
                "Comcast Xfinity — Sarasota",
                cat["internet"],
            )
        )
        add(
            tx(
                checking.id,
                clamp_day(y, m, 15),
                -D("75.00"),
                "T-Mobile — Bob & Maggie",
                cat["cell_phone"],
            )
        )

        # ── Life and umbrella insurance (annual policy, billed monthly) ───────
        add(
            tx(
                checking.id,
                clamp_day(y, m, 20),
                -D("510.00"),
                "USAA Life & Umbrella Insurance",
                cat["life_insurance"],
            )
        )

        # ── Household cleaning (Sarasota condo) ──────────────────────────────
        add(
            tx(
                checking.id,
                clamp_day(y, m, 8),
                -D("225.00"),
                "Sparkling Sarasota Cleaning",
                cat["cleaning_services"],
            )
        )

        # ── Investment advisory fee (quarterly, end of Q) ─────────────────────
        if m in (3, 6, 9, 12):
            advisory_q = D("6500.00") if m in (3, 9) else D("7000.00")
            add(
                tx(
                    checking.id,
                    last_day_of(y, m),
                    -advisory_q,
                    "Truist Wealth Management Advisory Fee",
                    cat["advisory_fees"],
                )
            )

        # ── Roth IRA backdoor contributions Jan-Oct ───────────────────────────
        if m <= 10:
            d, c = transfer(
                checking.id,
                bob_roth.id,
                clamp_day(y, m, 12),
                D("583.00"),
                "Fidelity — Bob Roth IRA (Backdoor)",
                cat["ira_contribution"],
            )
            add(d, c)
            d, c = transfer(
                checking.id,
                maggie_roth.id,
                clamp_day(y, m, 13),
                D("583.00"),
                "Vanguard — Maggie Roth IRA (Backdoor)",
                cat["ira_contribution"],
            )
            add(d, c)

        # ── Joint brokerage auto-invest ───────────────────────────────────────
        d, c = transfer(
            checking.id,
            joint_brok.id,
            clamp_day(y, m, 15),
            D("2000.00"),
            "Schwab — Joint Brokerage Auto-Invest",
            cat["brokerage_contribution"],
        )
        add(d, c)
        d, c = transfer(
            checking.id,
            bob_brok.id,
            clamp_day(y, m, 16),
            D("1000.00"),
            "Fidelity — Bob Brokerage Auto-Invest",
            cat["brokerage_contribution"],
        )
        add(d, c)

        # ── Income: Bob Social Security (3rd Wednesday, net of Medicare) ──────
        ss_date = third_wednesday(y, m)
        add(
            tx(
                checking.id,
                ss_date,
                D("4886.00"),
                "US Treasury Social Security",
                cat["social_security_income"],
            )
        )

        # ── Income: Bob Meridian Packaging Pension (1st of month) ────────────
        add(
            tx(
                checking.id,
                clamp_day(y, m, 1),
                D("4000.00"),
                "Meridian Packaging Pension",
                cat["pension_income"],
            )
        )

        # ── Income: Bob IRA RMD (quarterly, 0 in 2024) ───────────────────────
        if y == 2025 and m in (3, 6, 9):
            rmd_amt = D("34896.00")
            add(
                tx(
                    checking.id,
                    last_day_of(y, m),
                    rmd_amt,
                    "Schwab IRA Distribution — RMD",
                    cat["rmd_distribution"],
                )
            )
        elif y == 2025 and m == 12:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 15),
                    D("34897.00"),
                    "Schwab IRA Distribution — RMD",
                    cat["rmd_distribution"],
                )
            )
        elif y == 2026 and m == 3:
            add(
                tx(
                    checking.id,
                    last_day_of(y, m),
                    D("36530.00"),
                    "Schwab IRA Distribution — RMD",
                    cat["rmd_distribution"],
                )
            )

        # ── Income: Quarterly dividends ───────────────────────────────────────
        if m in _joint_div_by_q:
            q_last = last_day_of(y, m)
            if q_last <= DATE_END:
                add(
                    tx(
                        checking.id,
                        q_last,
                        _joint_div_by_q[m],
                        "Schwab Brokerage Dividend",
                        cat["dividends"],
                    )
                )
                add(
                    tx(
                        checking.id,
                        q_last,
                        _bob_div_by_q[m],
                        "Fidelity Brokerage Dividend",
                        cat["dividends"],
                    )
                )

        # ── LLC consulting: revenue, expenses, net transfer ───────────────────
        # Consulting revenue: 2-3 client invoices per month
        llc_revenue_base = jitter_d(D("6200.00"), rng)
        rev_count = rng.randint(2, 3)
        rev_parts = _split(llc_revenue_base, rev_count, rng)
        for _i, rev in enumerate(rev_parts):
            rev_day = clamp_day(y, m, rng.choice([5, 8, 12, 18, 22, 26]))
            add(
                tx(
                    llc_checking.id,
                    rev_day,
                    rev,
                    "Client Invoice — HR Consulting",
                    cat["consulting_fees"],
                )
            )

        # LLC expenses
        add(
            tx(
                llc_checking.id,
                clamp_day(y, m, 5),
                -D("299.00"),
                "Microsoft 365 Business",
                cat["marketing_software"],
            )
        )
        add(
            tx(
                llc_checking.id,
                clamp_day(y, m, 7),
                -D("150.00"),
                "SHRM Membership",
                cat["professional_dev"],
            )
        )
        if rng.random() < 0.4:
            add(
                tx(
                    llc_checking.id,
                    clamp_day(y, m, rng.randint(10, 20)),
                    -D(str(rng.randint(8, 22) * 50)),
                    "1099 Contractor — Research",
                    cat["professional_services"],
                )
            )
        if rng.random() < 0.25:
            add(
                tx(
                    llc_checking.id,
                    clamp_day(y, m, rng.randint(5, 20)),
                    -D(str(rng.randint(2, 8) * 50)),
                    "Business Travel — Client Site",
                    cat["business_travel"],
                )
            )

        # Monthly draw from LLC to joint checking (15th)
        draw_amt = D("3200.00")
        d, c = transfer(
            llc_checking.id,
            checking.id,
            clamp_day(y, m, 15),
            draw_amt,
            "Langford HR Consulting LLC — Owner Draw",
            cat["consulting_fees"],
        )
        add(d, c)

        # ── Centurion Card luxury spending ────────────────────────────────────
        cen_txns: list = []

        def cv(slug, merchants, min_t, max_t, min_n, max_n, **kw):
            cen_txns.extend(
                gen_variable(
                    centurion.id,
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
            "restaurants",
            [
                "Selby Gardens Cafe",
                "Klassic Chophouse",
                "Michael's On East",
                "Ocean Prime Sarasota",
                "St. Armands Circle Restaurant",
            ],
            1100,
            1800,
            3,
            5,
        )
        cv(
            "home_goods",
            ["Restoration Hardware", "Williams-Sonoma", "Pottery Barn", "Ethan Allen"],
            600,
            1600,
            1,
            3,
        )
        cv(
            "clothing",
            ["Nordstrom", "Brooks Brothers", "Neiman Marcus", "Lilly Pulitzer"],
            400,
            900,
            1,
            3,
        )
        cv(
            "personal_care",
            ["The Spa at Sarasota", "Barber of Seville", "Ulta Beauty"],
            200,
            450,
            1,
            3,
        )
        cv(
            "subscriptions",
            ["WSJ Digital", "Financial Times", "Bloomberg", "Peacock Premium"],
            80,
            80,
            1,
            1,
        )
        if rng.random() < 0.6:
            cv(
                "hobbies",
                ["Pelican Golf Club", "Sarasota Yacht Club", "Sarasota Art Center"],
                300,
                800,
                0,
                2,
            )

        # Seasonal: Major travel months (February, June, October)
        if m == 2:
            cv("travel", ["Delta Air Lines", "Marriott Bonvoy", "Hertz Premium"], 6000, 11000, 2, 4)
        elif m == 6:
            cv(
                "travel",
                ["American Airlines", "Four Seasons Punta Mita", "Virgin Voyages"],
                8000,
                16000,
                2,
                5,
            )
        elif m == 10:
            cv(
                "travel",
                ["JetBlue", "The Greenbrier Resort", "National Car Rental"],
                4500,
                8500,
                2,
                4,
            )
        elif rng.random() < 0.35:
            cv("travel", ["Sarasota Area Hotel", "Hertz", "Delta"], 1500, 4000, 0, 2)

        # Annual tax prep (CPA firm, billed in March)
        if m == 3:
            cen_txns.append(
                tx(
                    centurion.id,
                    clamp_day(y, m, 20),
                    -D("3800.00"),
                    "Deloitte Tax Services",
                    cat["tax_prep"],
                )
            )

        # Annual property insurance Sarasota (June)
        if m == 6:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 15),
                    -D("9400.00"),
                    "Citizens Insurance — Sarasota",
                    cat["home_insurance"],
                )
            )

        # Annual property insurance Highlands NC (March)
        if m == 3:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 15),
                    -D("3200.00"),
                    "State Farm — Highlands NC",
                    cat["home_insurance"],
                )
            )

        # Property taxes — Sarasota primary residence (June, December)
        if m == 6:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 28),
                    -D("17500.00"),
                    "Sarasota County Tax Collector",
                    cat["home_property_tax"],
                )
            )
        if m == 12:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 20),
                    -D("17500.00"),
                    "Sarasota County Tax Collector",
                    cat["home_property_tax"],
                )
            )

        # Property taxes — Highlands NC (July, December)
        if m == 7:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 15),
                    -D("5800.00"),
                    "Macon County NC Tax",
                    cat["rental_property_tax"],
                )
            )
        if m == 12:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 20),
                    -D("5800.00"),
                    "Macon County NC Tax",
                    cat["rental_property_tax"],
                )
            )

        # Sarasota home maintenance / landscaping (quarterly)
        if m in (1, 4, 7, 10):
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 14),
                    -D("750.00"),
                    "Heritage Landscaping Sarasota",
                    cat["lawn_garden"],
                )
            )
        if rng.random() < 0.3:
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, rng.randint(5, 25)),
                    -D(str(rng.randint(5, 30) * 100)),
                    "Sarasota Home Services",
                    cat["home_maintenance"],
                )
            )

        add(*cen_txns)

        # ── Sapphire Reserve joint spending ───────────────────────────────────
        sap_txns: list = []

        def sv(slug, merchants, min_t, max_t, min_n, max_n, **kw):
            sap_txns.extend(
                gen_variable(
                    sapphire.id,
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

        sv(
            "restaurants",
            [
                "Owen's Fish Camp",
                "Brine Seafood & Raw Bar",
                "The Francis",
                "Farmer's Market Bistro",
                "Verbena Sarasota",
            ],
            600,
            1100,
            3,
            5,
        )
        sv(
            "groceries",
            ["Publix", "Whole Foods Sarasota", "Morton's Gourmet Market"],
            450,
            650,
            4,
            7,
            avoid_sunday=True,
        )
        sv(
            "travel",
            ["Highlands NC Weekend", "Tampa Day Trip", "Clearwater Beach", "Visit Asheville NC"],
            300,
            1200,
            0,
            2,
        )
        sv("gas_fuel", ["Shell Sarasota", "Costco Gas", "BP"], 120, 180, 3, 5)
        sv(
            "fitness",
            ["Gold's Gym Sarasota", "Life Time Fitness", "Paddle Sarasota"],
            80,
            120,
            1,
            2,
        )
        if rng.random() < 0.5:
            sv(
                "events_tickets",
                ["Van Wezel Performing Arts Hall", "Sarasota Opera", "Ringling Museum"],
                150,
                500,
                0,
                2,
            )

        add(*sap_txns)

        # ── CC full payments each month (checking → each card) ────────────────
        cen_spend = abs(
            sum(t.amount for t in cen_txns if t.account_id == centurion.id and t.amount < 0)
        )
        if cen_spend > 0:
            d, c = transfer(
                checking.id,
                centurion.id,
                clamp_day(y, m, 28),
                cen_spend,
                "AmEx Centurion Statement Payment",
                cat["cc_payment"],
            )
            add(d, c)

        sap_spend = abs(
            sum(t.amount for t in sap_txns if t.account_id == sapphire.id and t.amount < 0)
        )
        if sap_spend > 0:
            d, c = transfer(
                checking.id,
                sapphire.id,
                clamp_day(y, m, 28),
                sap_spend,
                "Chase Sapphire Reserve Statement Payment",
                cat["cc_payment"],
            )
            add(d, c)

    # ── Revocable living trust (titling layer) ──────────────────────────────────
    # In net worth and in the taxable estate — pure probate-avoidance titling.
    rev_trust = make_ownership_entity(
        hid,
        "revocable_trust",
        "Langford Family Revocable Trust",
        counts_in_net_worth=True,
        in_taxable_estate=True,
        grantor_member_id=bob.id,
    )
    session.add(rev_trust)
    await session.flush()
    for titled in (sarasota_re, joint_brok):
        titled.ownership_entity_id = rev_trust.id
    prop_sarasota.ownership_entity_id = rev_trust.id

    # ── T-bill ladder / money-market (cash management) ──────────────────────────
    tbill = acc("treasury", "Treasury / T-Bill Ladder", "Schwab", "5471")
    await session.flush()
    session.add(snapshot(tbill.id, last_day_of(2026, 5), D("210000.00")))

    # ── Cash-value permanent life (Bob owns — estate-liquidity provisioning) ─────
    life_cv = acc("life_insurance_cash_value", "Whole Life Cash Value", "Northwestern Mutual", "8890")
    await session.flush()
    session.add(snapshot(life_cv.id, last_day_of(2026, 5), D("186000.00")))
    session.add(
        make_insurance_policy(
            hid,
            "permanent_life",
            D("1500000"),
            D("2400"),
            "quarterly",
            insured_member_id=bob.id,
            cash_value_account_id=life_cv.id,
            metadata={"carrier": "Northwestern Mutual", "purpose": "estate_liquidity"},
        )
    )

    # ── Umbrella ($10M) + long-term-care policies ───────────────────────────────
    session.add(
        make_insurance_policy(
            hid, "umbrella_liability", D("10000000"), D("1850"), "annual",
            metadata={"underlying": ["auto", "home", "vacation_home"]},
        )
    )
    for who in (bob, maggie):
        session.add(
            make_insurance_policy(
                hid, "long_term_care", D("400000"), D("3800"), "annual",
                insured_member_id=who.id,
                metadata={"daily_benefit": 350, "inflation_rider": "3pct_compound"},
            )
        )

    # Premium transactions (umbrella annual, LTC annual, permanent-life quarterly).
    for prem_year in (2024, 2025, 2026):
        add(tx(checking.id, date(prem_year, 2, 12), -D("1850.00"), "Chubb Umbrella Policy",
               cat["umbrella_premium"]))
        if prem_year < 2026:
            add(tx(checking.id, date(prem_year, 9, 20), -D("7600.00"),
                   "Mutual of Omaha LTC (both)", cat["ltc_insurance_premium"]))
        for q_month in (3, 6, 9, 12):
            if date(prem_year, q_month, 1) <= DATE_END:
                add(tx(checking.id, clamp_day(prem_year, q_month, 14), -D("2400.00"),
                       "Northwestern Mutual Whole Life", cat["permanent_life_premium"]))

    # ── Roth-conversion window (2024, pre-RMD) — partial conversions ─────────────
    # IRA/Roth are snapshot-valued, so these document the conversion cash-flow
    # without double-counting against the snapshot balances.
    for conv_month in (3, 7, 11):
        d, c = transfer(bob_ira.id, bob_roth.id, clamp_day(2024, conv_month, 18),
                        D("40000.00"), "Roth conversion — fill 24% bracket", cat["roth_conversion"])
        add(d, c)

    # ── QCD satisfying part of the RMD (excluded from income; not to a DAF) ──────
    for qcd_year in (2025, 2026):
        if date(qcd_year, 11, 1) <= DATE_END:
            add(tx(bob_ira.id, clamp_day(qcd_year, 11, 15), -D("25000.00"),
                   "QCD — Sarasota Community Foundation", cat["qcd_note"]))

    # ── Advisory notes ──────────────────────────────────────────────────────────
    session.add(make_advisory_note(
        hid, "retirement",
        "Roth-conversion window and the IRMAA two-year lookback",
        "In the low-income years before RMDs begin, partial Roth conversions fill the lower "
        "brackets and shrink future RMDs. Watch the IRMAA two-year lookback: a conversion in "
        "year N raises Medicare Part B/D premiums in year N+2, so size conversions against the "
        "next IRMAA tier, not just the marginal income-tax bracket.",
    ))
    session.add(make_advisory_note(
        hid, "charitable",
        "QCD satisfies the RMD while staying out of taxable income",
        "A Qualified Charitable Distribution from the IRA counts toward the year's RMD but is "
        "excluded from AGI, which also helps manage IRMAA tiers. A QCD must go directly to a "
        "public charity — it cannot be routed to a donor-advised fund.",
    ))
    session.add(make_advisory_note(
        hid, "insurance",
        "Permanent life as an estate-liquidity asset; umbrella sizing",
        "The whole-life cash value is a balance-sheet asset (owned by Bob, in net worth) that can "
        "fund estate costs without forcing asset sales. Umbrella coverage should at least equal "
        "net worth; at this level $10M is appropriate given the homes and vacation rental exposure.",
        account_id=life_cv.id,
    ))

    # ── Opening balance transactions ───────────────────────────────────────────
    targets: dict[uuid.UUID, D] = {
        checking.id: D("62000.00"),
        premium_sav.id: D("128000.00"),
        schwab_mm.id: D("265000.00"),
        llc_checking.id: D("38500.00"),
        centurion.id: D("-6200.00"),
        sapphire.id: D("-1600.00"),
        highlands_mort.id: D("-342000.00"),
    }
    for acc_id, target in targets.items():
        needed = target - running[acc_id]
        session.add(opening_balance_tx(acc_id, needed, cat.get("between_accounts")))

    session.add_all(all_txns)

    # ── FIRE Scenario A — 30-Year Portfolio Sustainability ────────────────────
    fire_a = make_fire_scenario(
        hid,
        bob.id,
        "30-Year Portfolio Sustainability",
        D("280000.00"),
        D("0.0550"),
        D("0.0300"),
        95,
        [
            {
                "id": str(uuid.uuid4()),
                "label": "Bob — Social Security (COLA 2.5%)",
                "type": "social_security",
                "amount_annual": 65004.00,
                "start_year": 2020,
                "end_year": None,
                "growth_rate_annual": 0.025,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Bob — Meridian Packaging Pension",
                "type": "pension",
                "amount_annual": 48000.00,
                "start_year": 2020,
                "end_year": 2045,
                "growth_rate_annual": 0.0,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Maggie — HR Consulting LLC",
                "type": "consulting",
                "amount_annual": 48000.00,
                "start_year": 2024,
                "end_year": 2029,
                "growth_rate_annual": -0.05,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Maggie — Former Employer Pension",
                "type": "pension",
                "amount_annual": 28800.00,
                "start_year": 2027,
                "end_year": 2055,
                "growth_rate_annual": 0.0,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Maggie — Social Security (FRA 67)",
                "type": "social_security",
                "amount_annual": 42000.00,
                "start_year": 2029,
                "end_year": None,
                "growth_rate_annual": 0.025,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Joint Brokerage — Dividends",
                "type": "investment",
                "amount_annual": 78000.00,
                "start_year": 2024,
                "end_year": None,
                "growth_rate_annual": 0.020,
                "is_pre_retirement": False,
            },
        ],
        safe_withdrawal_rate=D("0.04"),
    )
    session.add(fire_a)

    # ── FIRE Scenario B — Longevity Stress Test (to Age 100) ─────────────────
    fire_b = make_fire_scenario(
        hid,
        bob.id,
        "Longevity Stress Test (to Age 100)",
        D("320000.00"),
        D("0.0450"),
        D("0.0350"),
        100,
        [
            {
                "id": str(uuid.uuid4()),
                "label": "Bob — Social Security (COLA 1.5%)",
                "type": "social_security",
                "amount_annual": 65004.00,
                "start_year": 2020,
                "end_year": None,
                "growth_rate_annual": 0.015,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Bob — Meridian Packaging Pension",
                "type": "pension",
                "amount_annual": 48000.00,
                "start_year": 2020,
                "end_year": 2042,
                "growth_rate_annual": 0.0,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Maggie — Former Employer Pension",
                "type": "pension",
                "amount_annual": 28800.00,
                "start_year": 2027,
                "end_year": 2050,
                "growth_rate_annual": 0.0,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Maggie — Social Security (FRA 67)",
                "type": "social_security",
                "amount_annual": 42000.00,
                "start_year": 2029,
                "end_year": None,
                "growth_rate_annual": 0.015,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Joint Brokerage — Dividends",
                "type": "investment",
                "amount_annual": 78000.00,
                "start_year": 2024,
                "end_year": None,
                "growth_rate_annual": 0.020,
                "is_pre_retirement": False,
            },
        ],
        safe_withdrawal_rate=D("0.035"),
    )
    session.add(fire_b)

    # ── Debt record (Highlands NC Mortgage) ───────────────────────────────────
    session.add(
        make_debt(
            highlands_mort.id,
            D("375000.00"),
            D("342000.00"),
            D("0.0325"),
            D("1632.00"),
            360,
            date(2019, 6, 4),
        )
    )

    # ── Budgets ───────────────────────────────────────────────────────────────
    budget_rows = [
        # Housing
        ("hoa_fees", D("895.00"), date(2024, 1, 1)),
        # home_insurance: $9,400 (June/Sarasota) + $3,200 (March/Highlands) = $12,600/yr / 12 = $1,050/mo avg
        ("home_insurance", D("1050.00"), date(2024, 1, 1)),
        ("home_maintenance", D("500.00"), date(2024, 1, 1)),
        ("cleaning_services", D("225.00"), date(2024, 1, 1)),
        ("lawn_garden", D("250.00"), date(2024, 1, 1)),
        # Utilities
        ("electric", D("145.00"), date(2024, 1, 1)),
        ("internet", D("68.00"), date(2024, 1, 1)),
        ("cell_phone", D("75.00"), date(2024, 1, 1)),
        # Healthcare
        ("medicare_part_b", D("280.00"), date(2024, 1, 1)),
        ("medicare_part_d", D("48.00"), date(2024, 1, 1)),
        ("medigap_supplement", D("192.00"), date(2024, 1, 1)),
        ("aca_premium", D("1165.00"), date(2024, 1, 1)),
        ("aca_premium", D("1245.00"), date(2025, 1, 1)),
        ("aca_premium", D("1310.00"), date(2026, 1, 1)),
        # Food
        ("groceries", D("550.00"), date(2024, 1, 1)),
        ("restaurants", D("2500.00"), date(2024, 1, 1)),
        # Transportation
        ("gas_fuel", D("150.00"), date(2024, 1, 1)),
        # Lifestyle
        ("travel", D("2000.00"), date(2024, 1, 1)),
        ("hobbies", D("600.00"), date(2024, 1, 1)),
        ("fitness", D("100.00"), date(2024, 1, 1)),
        ("clothing", D("700.00"), date(2024, 1, 1)),
        ("events_tickets", D("300.00"), date(2024, 1, 1)),
        ("personal_care", D("325.00"), date(2024, 1, 1)),
        ("subscriptions", D("80.00"), date(2024, 1, 1)),
        # Financial
        ("life_insurance", D("510.00"), date(2024, 1, 1)),
        # advisory_fees: quarterly Q1/Q3=$6,500 + Q2/Q4=$7,000 = $27,000/yr / 12 = $2,250/mo avg
        ("advisory_fees", D("2250.00"), date(2024, 1, 1)),
        # tax_prep: $3,800 annual (March CPA bill) / 12 = $316.67/mo avg
        ("tax_prep", D("320.00"), date(2024, 1, 1)),
    ]
    for slug, amount, eff_from in budget_rows:
        session.add(make_budget(hid, cat[slug], amount, eff_from))

    # ── Summary ───────────────────────────────────────────────────────────────
    return {
        "num": 5,
        "name": "Langford",
        "location": "Sarasota FL",
        "members": 2,
        "accounts": 17,  # +2: T-bill ladder, whole-life cash value
        "transactions": len(all_txns),
        "properties": 2,
        "net_worth": 13_371_349.0,  # ReportService-computed as of 2026-06-01
        "fire_scenarios": 2,
        "debt_records": 1,
    }


# ── Module-level helpers (not exported) ──────────────────────────────────────


def jitter_d(amount: Decimal, rng: random.Random, pct: float = 0.12) -> Decimal:
    from decimal import ROUND_HALF_UP

    f = Decimal(str(1.0 + rng.uniform(-pct, pct)))
    return (amount * f).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _split(total: Decimal, count: int, rng: random.Random) -> list[Decimal]:
    from decimal import ROUND_HALF_UP

    if count == 1:
        return [total]
    parts: list[Decimal] = []
    remaining = total
    for i in range(count - 1):
        share = jitter_d(total / count, rng, pct=0.25)
        share = min(share, remaining - Decimal("0.01") * (count - 1 - i))
        parts.append(share.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        remaining -= parts[-1]
    parts.append(remaining.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return parts
