"""Household 2 — Okonkwo-Rivera (Naperville, IL). ~$3.4M net worth."""

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
    jitter,
    last_day_of,
    make_access_grant,
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
    transfer,
    tx,
)
from seed_households.shared_categories import seed_categories

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

D = Decimal


async def seed(session: AsyncSession, rng: random.Random) -> dict:
    # ── Household ─────────────────────────────────────────────────────────────
    hh = make_household("Okonkwo-Rivera Household")
    session.add(hh)
    hid = hh.id

    # ── Members ───────────────────────────────────────────────────────────────
    darius = make_member(hid, "Darius Okonkwo", "primary", date_of_birth=date(1979, 11, 8))
    carmen = make_member(hid, "Carmen Rivera-Okonkwo", "partner", date_of_birth=date(1981, 7, 15))
    emma = make_member(hid, "Emma Okonkwo", "dependent")
    noah = make_member(hid, "Noah Okonkwo", "dependent")
    session.add_all([darius, carmen, emma, noah])

    user_darius = make_user(darius.id, "darius@okonkwo-rivera.local")
    user_carmen = make_user(carmen.id, "carmen@okonkwo-rivera.local")
    user_emma = make_user(emma.id, "emma@okonkwo-rivera.local")
    user_noah = make_user(noah.id, "noah@okonkwo-rivera.local")
    session.add_all([user_darius, user_carmen, user_emma, user_noah])
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

    checking1 = acc("checking", "Premier Plus Checking", "Chase", "5589")
    savings2 = acc("savings", "Savings", "Chase", "6712")
    savings3 = acc("savings", "Online Savings", "Ally Bank", "3881")
    d_401k = acc("retirement_401k", "401(k)", "Fidelity NetBenefits", "4405", owner=darius.id)
    c_403b = acc("retirement_403b", "403(b)", "TIAA", "7723", owner=carmen.id)
    d_roth = acc("retirement_roth_ira", "Roth IRA", "Fidelity", "8834", owner=darius.id)
    c_roth = acc("retirement_roth_ira", "Roth IRA", "Vanguard", "9921", owner=carmen.id)
    brokerage = acc("investment_brokerage", "Joint Brokerage", "Charles Schwab", "2267")
    emma_529 = acc("investment_brokerage", "529 — Emma", "Illinois Bright Start", "3306")
    noah_529 = acc("investment_brokerage", "529 — Noah", "Illinois Bright Start", "3307")
    hsa = acc("hsa", "HSA", "HSA Bank", "8872")
    cc_reserve = acc("credit_card", "Sapphire Reserve", "Chase", "1188")
    cc_amazon = acc("credit_card", "Amazon Prime Visa", "Chase", "4456")
    vw_loan = acc("auto_loan", "VW ID.4 Auto Loan", "Volkswagen Financial", "5543", owner=darius.id)
    rav4_loan = acc("auto_loan", "Toyota RAV4 Loan", "Toyota Financial", "6621", owner=carmen.id)
    mortgage1 = acc("mortgage", "Primary Home Mortgage", "Wells Fargo", "9905")
    mortgage2 = acc("mortgage", "Evanston Condo Mortgage", "Chase Mortgage", "1122")
    home_re = acc("real_estate", "2614 Whispering Pines Dr", "—", None)
    condo_re = acc("real_estate", "Evanston Rental Condo", "—", None)

    # ── Access grant: Carmen views Darius's 401k ──────────────────────────────
    await session.flush()  # accounts must exist before account_access_grants FK check
    session.add(make_access_grant(d_401k.id, darius.id, carmen.id, user_darius.id))

    # ── Real estate ───────────────────────────────────────────────────────────
    prop_home = make_property(
        home_re.id,
        "2614 Whispering Pines Dr, Naperville, IL 60564",
        "primary_residence",
        date(2018, 9, 14),
        D("780000.00"),
        linked_mortgage_id=mortgage1.id,
    )
    session.add(prop_home)
    await session.flush()  # real_estate_properties must exist before property_valuations FK check
    for val_date, val_amt in [
        (date(2024, 1, 1), D("1138000.00")),
        (date(2024, 7, 1), D("1162000.00")),
        (date(2025, 1, 1), D("1192000.00")),
        (date(2025, 7, 1), D("1210000.00")),
        (date(2026, 1, 1), D("1220000.00")),
        (date(2026, 6, 1), D("1225000.00")),
    ]:
        session.add(make_valuation(prop_home.id, val_date, val_amt))

    prop_condo = make_property(
        condo_re.id,
        "1847 Dempster St #3C, Evanston, IL 60201",
        "rental",
        date(2014, 5, 20),
        D("310000.00"),
        linked_mortgage_id=mortgage2.id,
    )
    session.add(prop_condo)
    await session.flush()  # real_estate_properties must exist before property_valuations FK check
    for val_date, val_amt in [
        (date(2024, 1, 1), D("445000.00")),
        (date(2024, 7, 1), D("460000.00")),
        (date(2025, 1, 1), D("472000.00")),
        (date(2025, 7, 1), D("481000.00")),
        (date(2026, 1, 1), D("486000.00")),
        (date(2026, 6, 1), D("488000.00")),
    ]:
        session.add(make_valuation(prop_condo.id, val_date, val_amt))

    # ── Investment account snapshots ───────────────────────────────────────────
    oct24 = last_day_of(2024, 10)
    brokerage_dips = {oct24: -0.04}

    roth_contribs: dict[date, D] = {}
    for y in (2024, 2025, 2026):
        for mo in range(1, 11):
            if date(y, mo, 1) <= date(2026, 6, 20):
                roth_contribs[last_day_of(y, mo)] = D("583.00")

    k401_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("3255.00")  # 2542 employee + 713 employer
        for ms in all_months()
        if ms < date(2026, 6, 1)
        for y2, m2 in [(ms.year, ms.month)]
    }
    b403_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("1917.00")
        for ms in all_months()
        if ms < date(2026, 6, 1)
        for y2, m2 in [(ms.year, ms.month)]
    }
    brokerage_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms < date(2026, 6, 1):
            y2, m2 = ms.year, ms.month
            amt = D("10000.00") if m2 == 3 else D("2500.00")
            brokerage_contribs[last_day_of(y2, m2)] = amt

    e529_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("500.00")
        for ms in all_months()
        if ms < date(2026, 6, 1)
        for y2, m2 in [(ms.year, ms.month)]
    }
    hsa_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("646.00")
        for ms in all_months()
        if ms < date(2026, 6, 1)
        for y2, m2 in [(ms.year, ms.month)]
    }

    session.add_all(build_snapshots(d_401k.id, D("741000.00"), k401_contribs, 0.09))
    session.add_all(build_snapshots(c_403b.id, D("303200.00"), b403_contribs, 0.09))
    session.add_all(build_snapshots(d_roth.id, D("65400.00"), roth_contribs, 0.09))
    session.add_all(build_snapshots(c_roth.id, D("52200.00"), roth_contribs, 0.09))
    session.add_all(
        build_snapshots(brokerage.id, D("465000.00"), brokerage_contribs, 0.09, brokerage_dips)
    )
    session.add_all(build_snapshots(emma_529.id, D("70200.00"), e529_contribs, 0.09))
    session.add_all(build_snapshots(noah_529.id, D("48600.00"), e529_contribs, 0.09))
    session.add_all(build_snapshots(hsa.id, D("15800.00"), hsa_contribs, 0.09))
    session.add(snapshot(mortgage1.id, last_day_of(2026, 5), D("-512400.00")))
    session.add(snapshot(mortgage2.id, last_day_of(2026, 5), D("-261200.00")))

    # ── Transaction generation ────────────────────────────────────────────────
    all_txns: list = []
    running: dict = {
        checking1.id: D("0"),
        savings2.id: D("0"),
        savings3.id: D("0"),
        cc_reserve.id: D("0"),
        cc_amazon.id: D("0"),
        vw_loan.id: D("0"),
        rav4_loan.id: D("0"),
        mortgage1.id: D("0"),
        mortgage2.id: D("0"),
    }

    def add(*txs):
        for t in txs:
            all_txns.append(t)
            if t.account_id in running:
                running[t.account_id] += t.amount

    late_rent_months = {(2024, 8), (2025, 3)}
    summer_months = {6, 7, 8, 9}
    winter_months = {11, 12, 1, 2}

    for month_start in all_months():
        y, m = month_start.year, month_start.month

        # ── Income ────────────────────────────────────────────────────────────
        # Darius law firm draw
        add(
            tx(
                checking1.id,
                clamp_day(y, m, 1),
                D("13000.00"),
                "Feldman & Okonkwo LLP Payroll",
                cat["salary"],
            )
        )
        # Carmen school district (1st and 15th)
        for day in (1, 15):
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, day),
                    D("2875.00"),
                    "CUSD 203 Payroll",
                    cat["salary"],
                )
            )
        # Rental income — Evanston condo
        rent_day = 8 if (y, m) in late_rent_months else 1
        add(
            tx(
                checking1.id,
                clamp_day(y, m, rent_day),
                D("2650.00"),
                "ACH Tenant Payment",
                cat["residential_rental"],
                prop_id=prop_condo.id,
            )
        )
        # Year-end bonus (December only)
        if m == 12:
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, 15),
                    D("80000.00"),
                    "Feldman & Okonkwo Year-End Distribution",
                    cat["profit_distribution"],
                )
            )
        # IL tax refund (March)
        if m == 3:
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, 20),
                    D("3200.00"),
                    "Illinois Dept of Revenue",
                    cat["tax_refund"],
                )
            )

        # ── Fixed checking outflows ────────────────────────────────────────────
        d, c = transfer(
            checking1.id,
            mortgage1.id,
            clamp_day(y, m, 5),
            D("3620.00"),
            "Wells Fargo Mortgage",
            cat["mortgage_payment"],
        )
        add(d, c)
        d, c = transfer(
            checking1.id,
            mortgage2.id,
            clamp_day(y, m, 5),
            D("1352.00"),
            "Chase Mortgage",
            cat["mortgage_payment"],
            prop_id=prop_condo.id,
        )
        add(d, c)
        d, c = transfer(
            checking1.id,
            rav4_loan.id,
            clamp_day(y, m, 22),
            D("462.00"),
            "Toyota Financial",
            cat["loan_payment"],
        )
        add(d, c)
        d, c = transfer(
            checking1.id,
            vw_loan.id,
            clamp_day(y, m, 22),
            D("548.00"),
            "Volkswagen Financial",
            cat["loan_payment"],
        )
        add(d, c)
        d, c = transfer(
            checking1.id,
            brokerage.id,
            clamp_day(y, m, 15),
            D("2500.00"),
            "Schwab Auto-Invest",
            cat["brokerage_contribution"],
        )
        add(d, c)
        d, c = transfer(
            checking1.id,
            emma_529.id,
            clamp_day(y, m, 10),
            D("500.00"),
            "IL Bright Start — Emma",
            cat["brokerage_contribution"],
        )
        add(d, c)
        d, c = transfer(
            checking1.id,
            noah_529.id,
            clamp_day(y, m, 10),
            D("500.00"),
            "IL Bright Start — Noah",
            cat["brokerage_contribution"],
        )
        add(d, c)

        # Roth IRA contributions Jan-Oct
        if m in range(1, 11):
            d, c = transfer(
                checking1.id,
                d_roth.id,
                clamp_day(y, m, 5),
                D("583.00"),
                "Fidelity — Backdoor Roth IRA",
                cat["ira_contribution"],
            )
            add(d, c)
            d, c = transfer(
                checking1.id,
                c_roth.id,
                clamp_day(y, m, 5),
                D("583.00"),
                "Vanguard — Backdoor Roth IRA",
                cat["ira_contribution"],
            )
            add(d, c)

        # Direct checking debits
        add(tx(checking1.id, clamp_day(y, m, 10), -D("95.00"), "Comcast Xfinity", cat["internet"]))
        elec = D("230.00") if m in summer_months else D("165.00")
        add(tx(checking1.id, clamp_day(y, m, 10), -elec, "ComEd", cat["electric"]))
        gas = D("220.00") if m in winter_months else D("45.00")
        add(tx(checking1.id, clamp_day(y, m, 12), -gas, "Nicor Gas", cat["gas_heating"]))
        add(
            tx(
                checking1.id,
                clamp_day(y, m, 15),
                -D("298.00"),
                "State Farm Auto",
                cat["auto_insurance"],
            )
        )
        add(
            tx(
                checking1.id,
                clamp_day(y, m, 15),
                -D("212.00"),
                "Allstate Home Insurance",
                cat["home_insurance"],
            )
        )
        add(
            tx(
                checking1.id,
                clamp_day(y, m, 20),
                -D("280.00"),
                "Molly Maid",
                cat["cleaning_services"],
            )
        )

        # Rental condo expenses (property 2)
        add(
            tx(
                checking1.id,
                clamp_day(y, m, 10),
                -D("125.00"),
                "State Farm Landlord Policy",
                cat["rental_insurance"],
                prop_id=prop_condo.id,
            )
        )
        if m in (3, 9):
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, 20),
                    -D("2850.00"),
                    "Cook County Treasurer",
                    cat["rental_property_tax"],
                    prop_id=prop_condo.id,
                )
            )
        # Rental maintenance (1-2 per quarter)
        if rng.random() < 0.5:
            amt = jitter(D("450.00"), rng, 0.30)
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, rng.randint(5, 25)),
                    -amt,
                    "Contractor",
                    cat["rental_maintenance"],
                    prop_id=prop_condo.id,
                )
            )

        # Variable student activities from checking
        if rng.random() < 0.80:
            sa_amt = jitter(D("230.00"), rng, 0.25)
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, rng.randint(5, 25)),
                    -sa_amt,
                    "Activity Fee",
                    cat["student_activities"],
                )
            )
        if rng.random() < 0.60:
            hm_amt = jitter(D("350.00"), rng, 0.40)
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, rng.randint(5, 25)),
                    -hm_amt,
                    "Home Depot / Contractor",
                    cat["home_maintenance"],
                )
            )

        # ── Chase Sapphire Reserve spending ───────────────────────────────────
        res_txns: list = []

        def res_var(slug, merchants, mn, mx, min_n, max_n):
            res_txns.extend(
                gen_variable(
                    cc_reserve.id,
                    y,
                    m,
                    cat[slug],
                    merchants,
                    D(str(mn)),
                    D(str(mx)),
                    min_n,
                    max_n,
                    rng,
                )
            )

        res_var(
            "restaurants",
            ["Lou Malnati's", "Wildfire", "Boka Restaurant", "Lettuce Entertain You"],
            480,
            680,
            4,
            7,
        )
        res_var("coffee", ["Starbucks", "Intelligentsia Coffee", "Caribou Coffee"], 85, 130, 4, 8)
        res_var("food_delivery", ["Grubhub", "DoorDash", "Uber Eats"], 120, 200, 2, 4)
        res_var("gas_fuel", ["BP", "Shell", "Costco Gas"], 280, 360, 4, 6)
        res_var("fitness", ["Lifetime Fitness Naperville"], 125, 125, 1, 1)
        res_var(
            "clothing", ["Nordstrom", "Gap Factory", "Target", "Banana Republic"], 200, 450, 1, 4
        )
        res_var("personal_care", ["Salon", "Dry Cleaning", "CVS Pharmacy"], 180, 280, 2, 4)
        res_var(
            "events_tickets",
            ["Goodman Theatre", "Cubs Wrigley", "United Center", "House of Blues"],
            200,
            450,
            1,
            3,
        )
        if m == 10:
            res_var("events_tickets", ["Cubs NLCS", "Fall Events"], 400, 900, 1, 2)

        # ── Amazon Prime Visa spending ─────────────────────────────────────────
        amz_txns: list = []

        def amz_var(slug, merchants, mn, mx, min_n, max_n, **kw):
            amz_txns.extend(
                gen_variable(
                    cc_amazon.id,
                    y,
                    m,
                    cat[slug],
                    merchants,
                    D(str(mn)),
                    D(str(mx)),
                    min_n,
                    max_n,
                    rng,
                    **kw,
                )
            )

        amz_var(
            "groceries",
            ["Jewel-Osco", "Whole Foods", "Costco", "Trader Joe's"],
            1050,
            1280,
            6,
            9,
            avoid_sunday=True,
        )
        amz_txns.append(
            tx(cc_amazon.id, clamp_day(y, m, 5), -D("185.00"), "Verizon", cat["cell_phone"])
        )
        for sub_payee, sub_amt in [
            ("Netflix", D("23.00")),
            ("Peacock", D("13.00")),
            ("Apple TV+", D("10.00")),
            ("Spotify", D("11.00")),
        ]:
            amz_txns.append(
                tx(cc_amazon.id, clamp_day(y, m, 7), -sub_amt, sub_payee, cat["streaming"])
            )
        amz_var("school_supplies", ["Staples", "Target", "Amazon"], 40, 120, 1, 2)
        for sub in [("Amazon Prime", D("14.99")), ("Hulu", D("18.00")), ("Audible", D("14.95"))]:
            amz_txns.append(
                tx(cc_amazon.id, clamp_day(y, m, 8), -sub[1], sub[0], cat["subscriptions"])
            )

        add(*res_txns, *amz_txns)

        # Seasonal on Sapphire Reserve or Checking
        if m == 3:
            res_var("travel", ["American Airlines", "VRBO", "Marriott Hotels"], 3800, 5200, 2, 4)
        if m == 7:
            res_var("travel", ["Delta Airlines", "Resort Hotel", "Hertz"], 4500, 6800, 2, 4)
        if m == 8:
            add(
                tx(
                    cc_reserve.id,
                    clamp_day(y, m, 15),
                    -D("3200.00"),
                    "Northwestern Summer Program",
                    cat["tuition"],
                )
            )
        if m == 12:
            res_var("gifts_given", ["Amazon", "Nordstrom", "Local Merchants"], 1800, 2800, 3, 6)
        if m == 4:
            add(tx(cc_reserve.id, clamp_day(y, m, 20), -D("2400.00"), "CPA Firm", cat["tax_prep"]))
        if m == 1:
            add(
                tx(
                    cc_reserve.id,
                    clamp_day(y, m, 10),
                    -D("850.00"),
                    "Schwab Portfolio Advisory",
                    cat["advisory_fees"],
                )
            )

        # ── CC payments ───────────────────────────────────────────────────────
        reserve_total = sum(abs(t.amount) for t in res_txns)
        if reserve_total > 0:
            d, c = transfer(
                checking1.id,
                cc_reserve.id,
                clamp_day(y, m, 28),
                reserve_total,
                "Chase Sapphire Reserve Payment",
                cat["cc_payment"],
            )
            add(d, c)

        amz_total = sum(abs(t.amount) for t in amz_txns)
        if amz_total > 0:
            d, c = transfer(
                checking1.id,
                cc_amazon.id,
                clamp_day(y, m, 27),
                amz_total,
                "Amazon Prime Visa Payment",
                cat["cc_payment"],
            )
            add(d, c)

        # Periodic savings transfer from checking to Ally
        if rng.random() < 0.75:
            sav_amt = D(str(rng.choice([2000, 3000, 5000])))
            d, c = transfer(
                checking1.id,
                savings3.id,
                clamp_day(y, m, 26),
                sav_amt,
                "Transfer to Ally Savings",
                cat["savings_transfer"],
            )
            add(d, c)

    # ── Estate titling: revocable trust + documented bypass trust ───────────────
    rev_trust = make_ownership_entity(
        hid,
        "revocable_trust",
        "Okonkwo-Rivera Family Revocable Trust",
        counts_in_net_worth=True,
        in_taxable_estate=True,
        grantor_member_id=darius.id,
    )
    session.add(rev_trust)
    # Bypass / credit-shelter trust: documented now, funded at the first death to
    # preserve both spouses' Illinois exemptions (no portability). Unfunded in the
    # current both-living state — no accounts titled into it yet.
    bypass_trust = make_ownership_entity(
        hid,
        "irrevocable_trust",
        "Okonkwo-Rivera Credit Shelter Trust (first-death funding)",
        counts_in_net_worth=True,
        in_taxable_estate=False,
        grantor_member_id=darius.id,
    )
    session.add(bypass_trust)
    await session.flush()
    home_re.ownership_entity_id = rev_trust.id
    brokerage.ownership_entity_id = rev_trust.id
    prop_home.ownership_entity_id = rev_trust.id

    # ── Insurance: umbrella + long-term care for both adults ────────────────────
    session.add(
        make_insurance_policy(
            hid,
            "umbrella_liability",
            D("4000000"),
            D("780"),
            "annual",
            carrier="Chubb",
            policy_number="CHB-UMB-7734902",
            metadata={"underlying": ["auto", "home", "rental_condo"]},
        )
    )
    for who, pnum in zip((darius, carmen), ("GDI-LTC-2019-0341", "GDI-LTC-2019-0342"), strict=True):
        session.add(
            make_insurance_policy(
                hid,
                "long_term_care",
                D("300000"),
                D("3200"),
                "annual",
                insured_member_id=who.id,
                carrier="Guardian",
                policy_number=pnum,
                metadata={"daily_benefit": 250, "inflation_rider": "3pct_compound"},
            )
        )
    for prem_year in (2024, 2025, 2026):
        add(
            tx(
                checking1.id,
                date(prem_year, 4, 10),
                -D("780.00"),
                "Chubb Umbrella Policy",
                cat["umbrella_premium"],
            )
        )
        if prem_year < 2026:
            add(
                tx(
                    checking1.id,
                    date(prem_year, 10, 5),
                    -D("6400.00"),
                    "Northwestern LTC (both)",
                    cat["ltc_insurance_premium"],
                )
            )

    # ── 529 superfunding (five-year-forward gift election) + private school ──────
    for kid_529 in (emma_529, noah_529):
        d, c = transfer(
            checking1.id,
            kid_529.id,
            date(2024, 1, 18),
            D("90000.00"),
            "529 Superfund (5-yr election)",
            cat["529_superfund"],
        )
        add(d, c)
    for month_start in all_months():
        y, m = month_start.year, month_start.month
        if m in (1, 2, 3, 4, 5, 8, 9, 10, 11, 12):  # 10 months, school year
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, 5),
                    -D("1650.00"),
                    "Naperville Day School Tuition",
                    cat["private_school_tuition"],
                )
            )

    # ── Sandwich generation: recurring support for Carmen's aging mother ────────
    # Monthly assisted-living top-up plus a periodic medical/dental outlay. This
    # is a real cash-flow drag layered on top of childcare and private school —
    # the defining squeeze of the sandwich generation.
    for month_start in all_months():
        y, m = month_start.year, month_start.month
        add(
            tx(
                checking1.id,
                clamp_day(y, m, 3),
                -D("1450.00"),
                "Brookdale Senior Living — Mom",
                cat["eldercare"],
            )
        )
        if m in (4, 10):  # semiannual out-of-pocket medical / dental
            add(
                tx(
                    checking1.id,
                    clamp_day(y, m, 16),
                    -D("900.00"),
                    "Mom — medical & dental",
                    cat["eldercare"],
                )
            )

    # ── Advisory notes ──────────────────────────────────────────────────────────
    session.add(
        make_advisory_note(
            hid,
            "retirement",
            "Sandwich-generation cash flow: funding parents and kids at once",
            "Supporting an aging parent while paying childcare, private school, and 529s competes "
            "directly with the household's own retirement savings. Treat eldercare as a recurring "
            "budget line, not an ad-hoc expense, and check whether the support qualifies a parent as a "
            "tax dependent (medical-expense deductions, dependent-care considerations). Protect "
            "retirement contributions first — there are loans for college and care, but none for "
            "retirement.",
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "estate",
            "Illinois estate tax: $4M exemption, non-portable, with a cliff",
            "Illinois imposes its own estate tax at a $4,000,000 per-person exemption that is not "
            "indexed for inflation and not portable between spouses, with graduated rates up to 16% "
            "and a cliff that taxes the whole estate once the threshold is crossed. At ~$3.4M the "
            "household is just under the line, but appreciation and life-insurance death benefits "
            "could push it over. The standard mitigation is a bypass/credit-shelter trust funded at "
            "the first death to preserve both spouses' exemptions.",
            ownership_entity_id=bypass_trust.id,
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "charitable",
            "529 superfunding gift-tax election",
            "A five-year-forward lump 529 contribution lets each parent front-load up to five years "
            "of the annual gift exclusion per child in one year without using lifetime exemption, by "
            "filing the 5-year election on Form 709. No federal gift tax is due if no further gifts "
            "are made to the same beneficiary during the five-year spread.",
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "insurance",
            "Long-term-care timing",
            "Pre-retirement (mid-40s to mid-50s) is the standard window to lock in LTC coverage while "
            "premiums and underwriting are favorable; waiting raises both cost and decline risk.",
        )
    )

    # ── Opening balance transactions ───────────────────────────────────────────
    targets = {
        checking1.id: D("35200.00"),
        savings2.id: D("52400.00"),
        savings3.id: D("118000.00"),
        cc_reserve.id: D("-4850.00"),
        cc_amazon.id: D("-1650.00"),
        vw_loan.id: D("-22800.00"),
        rav4_loan.id: D("-16400.00"),
        mortgage1.id: D("-512400.00"),
        mortgage2.id: D("-261200.00"),
    }
    for acc_id, target in targets.items():
        needed = target - running[acc_id]
        session.add(opening_balance_tx(acc_id, needed, cat.get("between_accounts")))

    session.add_all(all_txns)

    # ── FIRE scenarios ─────────────────────────────────────────────────────────
    fire_a_streams = [
        {
            "id": str(uuid.uuid4()),
            "label": "Darius — Law Firm Income",
            "type": "salary",
            "amount_annual": 285000.00,
            "start_year": 2024,
            "end_year": 2038,
            "growth_rate_annual": 0.03,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Carmen — School District",
            "type": "salary",
            "amount_annual": 130000.00,
            "start_year": 2024,
            "end_year": 2038,
            "growth_rate_annual": 0.025,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Evanston Rental — Net",
            "type": "rental",
            "amount_annual": 24000.00,
            "start_year": 2024,
            "end_year": None,
            "growth_rate_annual": 0.02,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Carmen IMRF Pension (age 62)",
            "type": "pension",
            "amount_annual": 72000.00,
            "start_year": 2044,
            "end_year": None,
            "growth_rate_annual": 0.00,
            "is_pre_retirement": False,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Darius Social Security (age 67)",
            "type": "social_security",
            "amount_annual": 48000.00,
            "start_year": 2045,
            "end_year": None,
            "growth_rate_annual": 0.025,
            "is_pre_retirement": False,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Carmen Social Security (age 67)",
            "type": "social_security",
            "amount_annual": 36000.00,
            "start_year": 2047,
            "end_year": None,
            "growth_rate_annual": 0.025,
            "is_pre_retirement": False,
        },
    ]
    session.add(
        make_fire_scenario(
            hid,
            darius.id,
            "Retire at 60",
            D("220000.00"),
            D("0.0650"),
            D("0.0300"),
            60,
            fire_a_streams,
        )
    )

    fire_b_streams = [
        {
            "id": str(uuid.uuid4()),
            "label": "Darius — Law Firm Income",
            "type": "salary",
            "amount_annual": 285000.00,
            "start_year": 2024,
            "end_year": 2033,
            "growth_rate_annual": 0.03,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Carmen — School District",
            "type": "salary",
            "amount_annual": 130000.00,
            "start_year": 2024,
            "end_year": 2033,
            "growth_rate_annual": 0.025,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Evanston Rental — Net",
            "type": "rental",
            "amount_annual": 24000.00,
            "start_year": 2024,
            "end_year": None,
            "growth_rate_annual": 0.02,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Carmen IMRF Pension (age 62)",
            "type": "pension",
            "amount_annual": 72000.00,
            "start_year": 2044,
            "end_year": None,
            "growth_rate_annual": 0.00,
            "is_pre_retirement": False,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Darius Social Security (age 67)",
            "type": "social_security",
            "amount_annual": 48000.00,
            "start_year": 2045,
            "end_year": None,
            "growth_rate_annual": 0.025,
            "is_pre_retirement": False,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Carmen Social Security (age 67)",
            "type": "social_security",
            "amount_annual": 36000.00,
            "start_year": 2047,
            "end_year": None,
            "growth_rate_annual": 0.025,
            "is_pre_retirement": False,
        },
    ]
    session.add(
        make_fire_scenario(
            hid,
            darius.id,
            "Aggressive FIRE at 55",
            D("180000.00"),
            D("0.0700"),
            D("0.0300"),
            55,
            fire_b_streams,
        )
    )

    # ── Debt records ──────────────────────────────────────────────────────────
    session.add(
        make_debt(
            vw_loan.id, D("34000.00"), D("22800.00"), D("0.0690"), D("548.00"), 72, date(2022, 8, 1)
        )
    )
    session.add(
        make_debt(
            rav4_loan.id,
            D("28000.00"),
            D("16400.00"),
            D("0.0399"),
            D("462.00"),
            72,
            date(2021, 9, 1),
        )
    )

    # ── Budgets ───────────────────────────────────────────────────────────────
    for slug, amount, eff_from in [
        ("groceries", D("1150.00"), date(2024, 1, 1)),
        ("restaurants", D("550.00"), date(2024, 1, 1)),
        ("restaurants", D("650.00"), date(2025, 3, 1)),  # lifestyle creep
        ("coffee", D("100.00"), date(2024, 1, 1)),
        ("food_delivery", D("150.00"), date(2024, 1, 1)),
        ("gas_fuel", D("320.00"), date(2024, 1, 1)),
        ("internet", D("95.00"), date(2024, 1, 1)),
        ("cell_phone", D("185.00"), date(2024, 1, 1)),
        ("streaming", D("57.00"), date(2024, 1, 1)),
        ("electric", D("195.00"), date(2024, 1, 1)),
        ("auto_insurance", D("298.00"), date(2024, 1, 1)),
        ("home_insurance", D("212.00"), date(2024, 1, 1)),
        ("fitness", D("125.00"), date(2024, 1, 1)),
        ("clothing", D("300.00"), date(2024, 1, 1)),
        ("personal_care", D("230.00"), date(2024, 1, 1)),
        ("cleaning_services", D("280.00"), date(2024, 1, 1)),
        ("student_activities", D("250.00"), date(2024, 1, 1)),
        ("events_tickets", D("300.00"), date(2024, 1, 1)),
        ("home_maintenance", D("210.00"), date(2024, 1, 1)),
        ("travel", D("846.00"), date(2024, 1, 1)),
        ("gifts_given", D("200.00"), date(2024, 1, 1)),
        ("subscriptions", D("48.00"), date(2024, 1, 1)),
    ]:
        session.add(make_budget(hid, cat[slug], amount, eff_from))

    return {
        "num": 2,
        "name": "Okonkwo-Rivera",
        "location": "Naperville IL",
        "members": 4,
        "accounts": 19,
        "transactions": len(all_txns),
        "properties": 2,
        "net_worth": 3_620_411.0,  # ReportService-computed as of 2026-06-21
        "fire_scenarios": 2,
        "debt_records": 2,
    }
