"""Household 3 — Whitfield-Torres (Brentwood, CA). ~$9.9M net worth."""

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
    jitter,
    last_day_of,
    make_access_grant,
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
    make_ownership_entity,
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
    hh = make_household("Whitfield-Torres Household")
    session.add(hh)
    hid = hh.id

    # ── Members ───────────────────────────────────────────────────────────────
    ben = make_member(hid, "Benjamin Whitfield", "primary", date_of_birth=date(1972, 3, 22))
    gabriela = make_member(
        hid, "Gabriela Torres-Whitfield", "partner", date_of_birth=date(1975, 8, 11)
    )
    sophia = make_member(hid, "Sophia Whitfield", "dependent")
    ethan = make_member(hid, "Ethan Torres-Whitfield", "dependent")
    session.add_all([ben, gabriela, sophia, ethan])

    user_ben = make_user(ben.id, "ben@whitfield-torres.local")
    user_gabriela = make_user(gabriela.id, "gabriela@whitfield-torres.local")
    user_sophia = make_user(sophia.id, "sophia@whitfield-torres.local")
    user_ethan = make_user(ethan.id, "ethan@whitfield-torres.local")
    session.add_all([user_ben, user_gabriela, user_sophia, user_ethan])
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

    jpm_chk = acc("checking", "Private Client Checking", "JPMorgan Chase", "3847")
    jpm_sav = acc("savings", "Private Client Savings", "JPMorgan Chase", "5512")
    schwab_chk = acc("checking", "Investor Checking", "Charles Schwab", "7723", owner=ben.id)
    vanguard_mm = acc("savings", "Money Market (VMFXX)", "Vanguard", "2241")
    ben_401k = acc(
        "retirement_401k", "401(k) / Profit-Sharing Plan", "Fidelity", "8834", owner=ben.id
    )
    gab_sep = acc("retirement_ira", "SEP-IRA", "Charles Schwab", "9905", owner=gabriela.id)
    ben_roth = acc("retirement_roth_ira", "Roth IRA", "Fidelity", "4421", owner=ben.id)
    gab_roth = acc("retirement_roth_ira", "Roth IRA", "Vanguard", "5536", owner=gabriela.id)
    joint_brok = acc("investment_brokerage", "Joint Taxable Brokerage", "Charles Schwab", "6647")
    ben_brok = acc("investment_brokerage", "Individual Brokerage", "Fidelity", "7758", owner=ben.id)
    sophia_roth = acc("retirement_roth_ira", "Roth IRA", "Fidelity", "1102", owner=sophia.id)
    ethan_529 = acc("investment_brokerage", "529 College Savings", "ScholarShare CA", "2213")
    hsa = acc("hsa", "HSA", "Fidelity", "3324")
    amex_plat = acc("credit_card", "Platinum Card", "American Express", "9981", owner=ben.id)
    amex_gold = acc("credit_card", "Gold Card", "American Express", "4472", owner=gabriela.id)
    chase_sap = acc("credit_card", "Sapphire Reserve", "Chase", "5583")
    jpm_mort = acc("mortgage", "Primary Home Mortgage", "JPMorgan Chase Private", "8891")
    wf_mort = acc("mortgage", "Silver Lake Duplex Mortgage", "Wells Fargo", "9902")
    ld_mort = acc("mortgage", "Palm Springs Mortgage", "LoanDepot", "1123")
    heloc = acc("heloc", "HELOC", "Chase", "4437")
    tesla_loan = acc("auto_loan", "Tesla Model X", "Tesla Financial", "5548", owner=ben.id)
    porsche_loan = acc(
        "auto_loan", "Porsche Cayenne", "Porsche Financial", "6659", owner=gabriela.id
    )
    brentwood_re = acc("real_estate", "12847 Corsair Way", "—", None)
    silver_lake = acc("real_estate", "Silver Lake Duplex", "—", None)
    palm_springs = acc("real_estate", "Palm Springs Vacation Rental", "—", None)

    # ── Access grants for Sophia ───────────────────────────────────────────────
    await session.flush()  # accounts must exist before account_access_grants FK check
    for granted_acc in (jpm_chk, jpm_sav, joint_brok):
        session.add(make_access_grant(granted_acc.id, ben.id, sophia.id, user_ben.id))

    # ── Real estate ───────────────────────────────────────────────────────────
    prop_brentwood = make_property(
        brentwood_re.id,
        "12847 Corsair Way, Los Angeles, CA 90049",
        "primary_residence",
        date(2020, 11, 12),
        D("3200000.00"),
        linked_mortgage_id=jpm_mort.id,
    )
    session.add(prop_brentwood)
    await session.flush()  # real_estate_properties must exist before property_valuations FK check
    for val_date, val_amt in [
        (date(2024, 1, 1), D("3750000.00")),
        (date(2024, 7, 1), D("3850000.00")),
        (date(2025, 1, 1), D("3980000.00")),
        (date(2025, 7, 1), D("4050000.00")),
        (date(2026, 1, 1), D("4090000.00")),
        (date(2026, 6, 1), D("4100000.00")),
    ]:
        session.add(make_valuation(prop_brentwood.id, val_date, val_amt))

    prop_silver = make_property(
        silver_lake.id,
        "2218 Marathon St, Los Angeles, CA 90026",
        "rental",
        date(2017, 8, 22),
        D("1050000.00"),
        linked_mortgage_id=wf_mort.id,
    )
    session.add(prop_silver)
    await session.flush()  # real_estate_properties must exist before property_valuations FK check
    for val_date, val_amt in [
        (date(2024, 1, 1), D("1240000.00")),
        (date(2024, 7, 1), D("1280000.00")),
        (date(2025, 1, 1), D("1310000.00")),
        (date(2025, 7, 1), D("1335000.00")),
        (date(2026, 1, 1), D("1345000.00")),
        (date(2026, 6, 1), D("1350000.00")),
    ]:
        session.add(make_valuation(prop_silver.id, val_date, val_amt))

    prop_ps = make_property(
        palm_springs.id,
        "78456 Desert Hills Dr, Palm Springs, CA 92264",
        "vacation",
        date(2021, 6, 8),
        D("1085000.00"),
        linked_mortgage_id=ld_mort.id,
    )
    session.add(prop_ps)
    await session.flush()  # real_estate_properties must exist before property_valuations FK check
    for val_date, val_amt in [
        (date(2024, 1, 1), D("1040000.00")),
        (date(2024, 7, 1), D("1020000.00")),
        (date(2025, 1, 1), D("1000000.00")),
        (date(2025, 7, 1), D("988000.00")),
        (date(2026, 1, 1), D("983000.00")),
        (date(2026, 6, 1), D("985000.00")),
    ]:
        session.add(make_valuation(prop_ps.id, val_date, val_amt))

    # ── Investment account snapshots ───────────────────────────────────────────
    oct24 = last_day_of(2024, 10)
    apr25 = last_day_of(2025, 4)
    equity_dips = {oct24: -0.05, apr25: -0.03}

    roth_contribs: dict[date, D] = {}
    for y in (2024, 2025, 2026):
        for mo in range(1, 11):
            if date(y, mo, 1) <= date(2026, 6, 20):
                roth_contribs[last_day_of(y, mo)] = D("583.00")

    sophia_roth_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("500.00")
        for ms in all_months()
        if ms < date(2026, 6, 1)
        for y2, m2 in [(ms.year, ms.month)]
    }

    ben_401k_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms < date(2026, 6, 1):
            y2, m2 = ms.year, ms.month
            monthly = D("2708.00")
            if m2 == 1:
                monthly += D("62000.00") if y2 == 2024 else D("65000.00")
            ben_401k_contribs[last_day_of(y2, m2)] = monthly

    gab_sep_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms < date(2026, 6, 1):
            y2, m2 = ms.year, ms.month
            monthly = D("0.00")
            if m2 == 1:
                monthly = D("66000.00") if y2 == 2024 else D("69000.00")
            gab_sep_contribs[last_day_of(y2, m2)] = monthly

    joint_brok_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms < date(2026, 6, 1):
            y2, m2 = ms.year, ms.month
            amt = D("5000.00")
            if m2 == 1:
                amt += D("50000.00")
            joint_brok_contribs[last_day_of(y2, m2)] = amt

    ben_brok_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms < date(2026, 6, 1):
            y2, m2 = ms.year, ms.month
            amt = D("2000.00")
            if m2 == 10:
                amt += D("30000.00")
            ben_brok_contribs[last_day_of(y2, m2)] = amt

    ethan_529_contribs: dict[date, D] = {}
    for ms in all_months():
        if ms < date(2026, 6, 1):
            y2, m2 = ms.year, ms.month
            if date(y2, m2, 1) <= date(2025, 7, 1):
                ethan_529_contribs[last_day_of(y2, m2)] = D("2333.00")
            else:
                ethan_529_contribs[last_day_of(y2, m2)] = D("0.00")

    hsa_contribs: dict[date, D] = {
        last_day_of(y2, m2): D("646.00")
        for ms in all_months()
        if ms < date(2026, 6, 1)
        for y2, m2 in [(ms.year, ms.month)]
    }

    session.add_all(build_snapshots(ben_401k.id, D("1492000.00"), ben_401k_contribs, 0.09))
    session.add_all(build_snapshots(gab_sep.id, D("508000.00"), gab_sep_contribs, 0.09))
    session.add_all(build_snapshots(ben_roth.id, D("88200.00"), roth_contribs, 0.09))
    session.add_all(build_snapshots(gab_roth.id, D("73600.00"), roth_contribs, 0.09))
    session.add_all(
        build_snapshots(joint_brok.id, D("1175000.00"), joint_brok_contribs, 0.09, equity_dips)
    )
    session.add_all(
        build_snapshots(ben_brok.id, D("421000.00"), ben_brok_contribs, 0.09, equity_dips)
    )
    session.add_all(build_snapshots(sophia_roth.id, D("4800.00"), sophia_roth_contribs, 0.09))
    session.add_all(build_snapshots(ethan_529.id, D("60000.00"), ethan_529_contribs, 0.09))
    session.add_all(build_snapshots(hsa.id, D("28400.00"), hsa_contribs, 0.09))
    session.add(snapshot(jpm_mort.id, last_day_of(2026, 5), D("-1285000.00")))
    session.add(snapshot(wf_mort.id, last_day_of(2026, 5), D("-645200.00")))
    session.add(snapshot(ld_mort.id, last_day_of(2026, 5), D("-418600.00")))

    # ── Transaction generation ────────────────────────────────────────────────
    all_txns: list = []
    running: dict = {
        jpm_chk.id: D("0"),
        jpm_sav.id: D("0"),
        schwab_chk.id: D("0"),
        vanguard_mm.id: D("0"),
        amex_plat.id: D("0"),
        amex_gold.id: D("0"),
        chase_sap.id: D("0"),
        jpm_mort.id: D("0"),
        wf_mort.id: D("0"),
        ld_mort.id: D("0"),
        heloc.id: D("0"),
        tesla_loan.id: D("0"),
        porsche_loan.id: D("0"),
    }

    def add(*txs):
        for t in txs:
            all_txns.append(t)
            if t.account_id in running:
                running[t.account_id] += t.amount

    summer_months = {6, 7, 8, 9}
    winter_months = {11, 12, 1, 2}

    # STR income by month pattern
    str_income_range = {
        1: (5800, 7200),
        2: (5800, 7200),
        3: (5800, 7200),
        4: (5800, 7200),
        5: (2400, 3200),
        6: (0, 0),
        7: (0, 0),
        8: (1800, 2600),
        9: (1800, 2600),
        10: (4200, 5800),
        11: (4200, 5800),
        12: (3200, 4400),
    }

    for month_start in all_months():
        y, m = month_start.year, month_start.month

        # ── Income to JPM Checking ─────────────────────────────────────────────
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 1),
                D("18500.00"),
                "Whitfield & Associates LLP",
                cat["salary"],
            )
        )
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 15),
                D("24000.00"),
                "Torres Dev Consulting LLC",
                cat["consulting_fees"],
            )
        )

        # Silver Lake rental income (tagged to prop_silver)
        unit_a_amt = D("3200.00")
        unit_b_amt = D("0.00") if (y == 2024 and m == 11) else D("2950.00")
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 1),
                unit_a_amt,
                "Tenant ACH — Unit A",
                cat["residential_rental"],
                prop_id=prop_silver.id,
            )
        )
        if unit_b_amt > 0:
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 1),
                    unit_b_amt,
                    "Tenant ACH — Unit B",
                    cat["residential_rental"],
                    prop_id=prop_silver.id,
                )
            )

        # Palm Springs STR income (tagged to prop_ps, deposited 15th)
        lo, hi = str_income_range[m]
        if hi > 0:
            str_amt = jitter(D(str((lo + hi) // 2)), rng, 0.15)
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 15),
                    str_amt,
                    "Airbnb Payout",
                    cat["short_term_rental"],
                    prop_id=prop_ps.id,
                )
            )

        # W&A LLP Annual Distribution (October to Schwab Checking)
        if m == 10:
            add(
                tx(
                    schwab_chk.id,
                    clamp_day(y, m, 20),
                    D("120000.00"),
                    "W&A LLP Partner Distribution",
                    cat["profit_distribution"],
                )
            )

        # CA Tax refund (April)
        if m == 4:
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 25),
                    D("8400.00"),
                    "CA Franchise Tax Board",
                    cat["tax_refund"],
                )
            )

        # ── Fixed outflows from JPM Checking ──────────────────────────────────
        d, c = transfer(
            jpm_chk.id,
            jpm_mort.id,
            clamp_day(y, m, 5),
            D("15050.00"),
            "JPM Chase Private Mortgage",
            cat["mortgage_payment"],
        )
        add(d, c)
        d, c = transfer(
            jpm_chk.id,
            wf_mort.id,
            clamp_day(y, m, 5),
            D("5170.00"),
            "Wells Fargo — Silver Lake",
            cat["mortgage_payment"],
            prop_id=prop_silver.id,
        )
        add(d, c)
        d, c = transfer(
            jpm_chk.id,
            ld_mort.id,
            clamp_day(y, m, 5),
            D("4876.00"),
            "LoanDepot — Palm Springs",
            cat["mortgage_payment"],
            prop_id=prop_ps.id,
        )
        add(d, c)

        # HELOC: interest charge (from Chase) + payment from checking
        add(
            tx(
                heloc.id,
                clamp_day(y, m, 10),
                -D("920.00"),
                "Chase HELOC Interest",
                cat["heloc_payment"],
            )
        )
        d, c = transfer(
            jpm_chk.id,
            heloc.id,
            clamp_day(y, m, 15),
            D("920.00"),
            "Chase HELOC Payment",
            cat["heloc_payment"],
        )
        add(d, c)

        d, c = transfer(
            jpm_chk.id,
            porsche_loan.id,
            clamp_day(y, m, 22),
            D("752.00"),
            "Porsche Financial",
            cat["loan_payment"],
        )
        add(d, c)
        d, c = transfer(
            jpm_chk.id,
            joint_brok.id,
            clamp_day(y, m, 15),
            D("5000.00"),
            "Schwab Auto-Invest",
            cat["brokerage_contribution"],
        )
        add(d, c)

        # Ethan 529 contribution (through July 2025)
        if date(y, m, 1) <= date(2025, 7, 1):
            d, c = transfer(
                jpm_chk.id,
                ethan_529.id,
                clamp_day(y, m, 10),
                D("2333.00"),
                "ScholarShare 529 — Ethan",
                cat["brokerage_contribution"],
            )
            add(d, c)

        # Sophia's Roth IRA (from Ben, as gift)
        d, c = transfer(
            jpm_chk.id,
            sophia_roth.id,
            clamp_day(y, m, 10),
            D("500.00"),
            "Ben → Sophia Roth IRA",
            cat["ira_contribution"],
        )
        add(d, c)

        # Direct debits from JPM Checking
        add(tx(jpm_chk.id, clamp_day(y, m, 10), -D("120.00"), "Spectrum Business", cat["internet"]))
        elec = D("520.00") if m in summer_months else D("380.00")
        add(tx(jpm_chk.id, clamp_day(y, m, 10), -elec, "SCE", cat["electric"]))
        add(tx(jpm_chk.id, clamp_day(y, m, 10), -D("165.00"), "LADWP Water", cat["water_sewer"]))
        gas = D("220.00") if m in winter_months else D("85.00")
        add(tx(jpm_chk.id, clamp_day(y, m, 12), -gas, "SoCalGas", cat["gas_heating"]))
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 15),
                -D("645.00"),
                "AIG Private Client Auto",
                cat["auto_insurance"],
            )
        )
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 15),
                -D("520.00"),
                "Chubb Masterpiece Home",
                cat["home_insurance"],
            )
        )
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 15),
                -D("1800.00"),
                "Housekeeper",
                cat["cleaning_services"],
            )
        )
        add(tx(jpm_chk.id, clamp_day(y, m, 15), -D("680.00"), "Gardener", cat["lawn_garden"]))
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 15),
                -D("1240.00"),
                "Pacific Life Insurance",
                cat["life_insurance"],
            )
        )

        # Advisory fees — quarterly ($5,400 in Jan/Apr/Jul/Oct)
        if m in (1, 4, 7, 10):
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 20),
                    -D("5400.00"),
                    "Schwab Private Client Advisory",
                    cat["advisory_fees"],
                )
            )

        # Silver Lake Duplex expenses (tagged to prop_silver)
        sl_maint = jitter(D("1200.00"), rng, 0.40)
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, rng.randint(10, 20)),
                -sl_maint,
                "Contractor — Silver Lake",
                cat["rental_maintenance"],
                prop_id=prop_silver.id,
            )
        )
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 10),
                -D("285.00"),
                "Farmers Landlord Policy",
                cat["rental_insurance"],
                prop_id=prop_silver.id,
            )
        )
        if m in (4, 10):
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 20),
                    -D("10500.00"),
                    "LA County Assessor — Property Tax",
                    cat["rental_property_tax"],
                    prop_id=prop_silver.id,
                )
            )

        # Palm Springs expenses (tagged to prop_ps)
        if str_income_range[m][1] > 0:
            ps_maint_range = (400, 800) if str_income_range[m][1] >= 2600 else (100, 300)
            ps_maint = jitter(D(str((ps_maint_range[0] + ps_maint_range[1]) // 2)), rng, 0.30)
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, rng.randint(10, 20)),
                    -ps_maint,
                    "PS Contractor",
                    cat["rental_maintenance"],
                    prop_id=prop_ps.id,
                )
            )
            lo2, hi2 = str_income_range[m]
            str_gross = jitter(D(str((lo2 + hi2) // 2)), rng, 0.15)
            mgmt_fee = (str_gross * D("0.15")).quantize(D("0.01"))
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 20),
                    -mgmt_fee,
                    "Stay Duvet Property Management",
                    cat["property_management"],
                    prop_id=prop_ps.id,
                )
            )
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 10),
                -D("320.00"),
                "Proper Insurance STR Policy",
                cat["rental_insurance"],
                prop_id=prop_ps.id,
            )
        )
        if m in (3, 11):
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 20),
                    -D("5800.00"),
                    "Riverside County — Property Tax",
                    cat["rental_property_tax"],
                    prop_id=prop_ps.id,
                )
            )

        # ── Schwab Checking fixed outflows ─────────────────────────────────────
        # Tesla loan (with $500 extra)
        d, c = transfer(
            schwab_chk.id,
            tesla_loan.id,
            clamp_day(y, m, 22),
            D("1788.00"),
            "Tesla Financial",
            cat["loan_payment"],
        )
        add(d, c)
        # Ben's individual brokerage
        d, c = transfer(
            schwab_chk.id,
            ben_brok.id,
            clamp_day(y, m, 15),
            D("2000.00"),
            "Fidelity — Individual Brokerage",
            cat["brokerage_contribution"],
        )
        add(d, c)

        # Roth IRA contributions Jan-Oct (from JPM Checking)
        if m in range(1, 11):
            d, c = transfer(
                jpm_chk.id,
                ben_roth.id,
                clamp_day(y, m, 5),
                D("583.00"),
                "Fidelity — Backdoor Roth IRA",
                cat["ira_contribution"],
            )
            add(d, c)
            d, c = transfer(
                jpm_chk.id,
                gab_roth.id,
                clamp_day(y, m, 5),
                D("583.00"),
                "Vanguard — Backdoor Roth IRA",
                cat["ira_contribution"],
            )
            add(d, c)

        # ── Amex Platinum spending (Benjamin's card) — paid from Schwab Checking ──
        plat_txns: list = []

        def plat_var(slug, merchants, mn, mx, min_n, max_n):
            plat_txns.extend(
                gen_variable(
                    amex_plat.id,
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

        plat_var(
            "restaurants",
            ["Nobu", "Jon & Vinny's", "Spago", "Republique", "Osteria Mozza"],
            1400,
            2800,
            5,
            10,
        )
        plat_txns.append(
            tx(amex_plat.id, clamp_day(y, m, 5), -D("320.00"), "AT&T (4 lines)", cat["cell_phone"])
        )
        for sub, amt in [
            ("Netflix 4K", D("22.99")),
            ("HBO Max", D("15.99")),
            ("Apple TV+", D("9.99")),
            ("Spotify Family", D("16.99")),
            ("Peloton App", D("24.99")),
        ]:
            plat_txns.append(tx(amex_plat.id, clamp_day(y, m, 7), -amt, sub, cat["streaming"]))
        plat_txns.append(
            tx(amex_plat.id, clamp_day(y, m, 5), -D("390.00"), "Equinox", cat["fitness"])
        )
        plat_txns.append(
            tx(amex_plat.id, clamp_day(y, m, 8), -D("880.00"), "Therapy Sessions", cat["therapy"])
        )
        plat_var(
            "clothing",
            ["Nordstrom", "Saks Fifth Avenue", "Maxfield LA", "Mr Porter"],
            800,
            2200,
            1,
            4,
        )
        plat_var("ev_charging", ["Tesla Supercharger", "ChargePoint"], 65, 120, 2, 5)
        for sub in [
            ("Amex Centurion Lounge", D("50.00")),
            ("WSJ", D("30.00")),
            ("FT Digital", D("40.00")),
            ("NYT", D("25.00")),
            ("LinkedIn Premium", D("40.00")),
        ]:
            plat_txns.append(
                tx(amex_plat.id, clamp_day(y, m, 8), -sub[1], sub[0], cat["subscriptions"])
            )
        if rng.random() < 0.50:
            plat_var(
                "home_goods", ["RH Brentwood", "Williams-Sonoma", "Crate & Barrel"], 400, 2000, 0, 2
            )

        # ── Amex Gold spending (Gabriela's card) — paid from JPM Checking ─────
        gold_txns: list = []

        def gold_var(slug, merchants, mn, mx, min_n, max_n, **kw):
            gold_txns.extend(
                gen_variable(
                    amex_gold.id,
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

        gold_var(
            "groceries",
            ["Erewhon", "Bristol Farms", "Gelson's", "Costco"],
            1800,
            2400,
            6,
            10,
            avoid_sunday=True,
        )
        gold_var("coffee", ["Starbucks Reserve", "Blue Bottle", "Intelligentsia"], 120, 180, 5, 10)
        gold_var("food_delivery", ["Uber Eats", "Postmates", "DoorDash"], 200, 350, 3, 6)
        gold_var(
            "personal_care", ["Salon Cristophe", "Burke Williams Spa", "Drybar"], 600, 1100, 3, 6
        )
        gold_var("pet_care", ["VCA Animal Hospitals", "Pet Groomer", "Petco"], 180, 450, 2, 4)

        # Chase Sapphire — gas + occasional shared spending
        chase_txns: list = []
        chase_txns.append(
            tx(chase_sap.id, clamp_day(y, m, 15), -D("95.00"), "Chevron", cat["gas_fuel"])
        )

        # ── Car maintenance (CA registration + service, two cars incl. Tesla) ──
        if m == 11:
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 12),
                    -D("920.00"),
                    "CA DMV — Registration Renewal (2 vehicles)",
                    cat["car_maintenance"],
                )
            )
        if m in (3, 9):
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, rng.randint(8, 22)),
                    -jitter(D("650.00"), rng, 0.30),
                    "Tesla Service Center / Hansel Auto",
                    cat["car_maintenance"],
                )
            )

        # ── Out-of-pocket healthcare (concierge MD, copays, dental, vision, Rx) ─
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 6),
                -D("400.00"),
                "Concierge MD — Brentwood",
                cat["doctor_medical"],
            )
        )
        add(
            tx(
                jpm_chk.id,
                clamp_day(y, m, 9),
                -jitter(D("120.00"), rng, 0.35),
                "CVS Pharmacy — Brentwood",
                cat["pharmacy"],
            )
        )
        if m in (4, 10):  # semiannual family cleanings
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 11),
                    -D("680.00"),
                    "Brentwood Dental Studio — Family",
                    cat["dental"],
                )
            )
        if m == 9:  # annual family exams + lenses
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 17),
                    -D("780.00"),
                    "LA Vision — Family Exams & Lenses",
                    cat["vision"],
                )
            )

        # Seasonal
        if m == 1:
            plat_var("travel", ["PrivateFly", "United Polaris", "Amex Travel"], 8000, 14000, 2, 4)
        if m == 7:
            plat_var(
                "travel",
                ["Lufthansa First", "Four Seasons Paris", "Hertz Europe"],
                18000,
                28000,
                3,
                6,
            )
        if m in (9, 12, 3):
            # UCSB tuition (Ethan)
            add(tx(jpm_chk.id, clamp_day(y, m, 15), -D("4800.00"), "UCSB Fees", cat["tuition"]))
        if m == 12:
            plat_var(
                "gifts_given", ["Neiman Marcus", "Amazon", "Amorim Beverly Hills"], 5000, 8000, 3, 7
            )
        if m == 4:
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 20),
                    -D("12500.00"),
                    "Holthouse Carlin & Van Trigt LLP",
                    cat["tax_prep"],
                )
            )
        if m == 2:
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 15),
                    -D("4200.00"),
                    "Estate Attorney Annual Review",
                    cat["professional_services"],
                )
            )
        if m == 8:
            hm_amt = jitter(D("4500.00"), rng, 0.25)
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 15),
                    -hm_amt,
                    "Pool Service & HVAC",
                    cat["home_maintenance"],
                )
            )

        # Record all card charges (incl. seasonal travel/gifts added above) before
        # computing statement payments, so each payment matches actual spend.
        add(*plat_txns, *gold_txns, *chase_txns)

        # ── CC payments ───────────────────────────────────────────────────────
        plat_total = sum(abs(t.amount) for t in plat_txns)
        if plat_total > 0:
            d, c = transfer(
                schwab_chk.id,
                amex_plat.id,
                clamp_day(y, m, 28),
                plat_total,
                "Amex Platinum Statement Payment",
                cat["cc_payment"],
            )
            add(d, c)

        gold_total = sum(abs(t.amount) for t in gold_txns)
        if gold_total > 0:
            d, c = transfer(
                jpm_chk.id,
                amex_gold.id,
                clamp_day(y, m, 27),
                gold_total,
                "Amex Gold Statement Payment",
                cat["cc_payment"],
            )
            add(d, c)

        chase_total = sum(abs(t.amount) for t in chase_txns)
        if chase_total > 0:
            d, c = transfer(
                jpm_chk.id,
                chase_sap.id,
                clamp_day(y, m, 27),
                chase_total,
                "Chase Sapphire Statement Payment",
                cat["cc_payment"],
            )
            add(d, c)

        # Periodic transfer JPM Checking → JPM Savings
        if rng.random() < 0.65:
            sav_amt = D(str(rng.choice([5000, 10000, 15000])))
            d, c = transfer(
                jpm_chk.id,
                jpm_sav.id,
                clamp_day(y, m, 26),
                sav_amt,
                "Transfer to Private Client Savings",
                cat["savings_transfer"],
            )
            add(d, c)

    # ── Revocable living trust (titles residence + taxable brokerage) ───────────
    rev_trust = make_ownership_entity(
        hid,
        "revocable_trust",
        "Whitfield-Torres Family Revocable Trust",
        counts_in_net_worth=True,
        in_taxable_estate=True,
        grantor_member_id=ben.id,
    )
    session.add(rev_trust)
    await session.flush()
    brentwood_re.ownership_entity_id = rev_trust.id
    joint_brok.ownership_entity_id = rev_trust.id
    prop_brentwood.ownership_entity_id = rev_trust.id

    # ── Equity compensation: Ben's RSU + ISO at a public streamer (NFLX) ─────────
    rsu = make_equity_grant(
        hid,
        ben.id,
        "rsu",
        date(2022, 2, 15),
        D("8000"),
        "NFLX",
        vesting_schedule={"cliff_months": 12, "cadence": "quarterly", "years": 4},
    )
    iso = make_equity_grant(
        hid,
        ben.id,
        "iso",
        date(2023, 1, 20),
        D("4000"),
        "NFLX",
        strike_price=D("330.00"),
        vesting_schedule={"cliff_months": 12, "cadence": "annual", "years": 4},
    )
    session.add_all([rsu, iso])
    await session.flush()

    # Quarterly RSU vests across the window, sell-to-cover ~40%, retained shares
    # build a concentrated single-stock position (lots: rsu_vest).
    _rsu_fmv = {2024: D("485.00"), 2025: D("620.00"), 2026: D("710.00")}
    for ms in all_months():
        y, m = ms.year, ms.month
        if m not in (3, 6, 9, 12) or ms > DATE_END:
            continue
        fmv = _rsu_fmv[y]
        shares = D("125")
        sold = D("50")
        income = (shares * fmv).quantize(D("0.01"))
        lot = make_investment_lot(
            ben_brok.id, "NFLX", shares - sold, fmv, clamp_day(y, m, 5), "rsu_vest"
        )
        session.add(lot)
        await session.flush()
        session.add(
            make_vesting_event(
                rsu.id,
                clamp_day(y, m, 5),
                shares,
                fmv,
                income,
                shares_sold_to_cover=sold,
                resulting_lot_id=lot.id,
            )
        )
        add(tx(schwab_chk.id, clamp_day(y, m, 5), income, "NFLX RSU vest", cat["rsu_vest_income"]))
        add(
            tx(
                schwab_chk.id,
                clamp_day(y, m, 6),
                -(sold * fmv).quantize(D("0.01")),
                "NFLX sell-to-cover",
                cat["equity_sale"],
            )
        )

    # ISO held tranche exercised-and-held in 2024 → AMT preference that year.
    iso_shares = D("2000")
    iso_fmv = D("485.00")
    amt_pref = ((iso_fmv - D("330.00")) * iso_shares).quantize(D("0.01"))
    iso_lot = make_investment_lot(
        ben_brok.id, "NFLX", iso_shares, D("330.00"), date(2024, 5, 10), "purchase"
    )
    session.add(iso_lot)
    await session.flush()
    session.add(
        make_vesting_event(
            iso.id,
            date(2024, 5, 10),
            iso_shares,
            iso_fmv,
            D("0"),
            amt_preference_amount=amt_pref,
            resulting_lot_id=iso_lot.id,
        )
    )
    # Direct long-held purchase lots that deepen the concentration.
    for buy_date, sh, basis in [
        (date(2018, 6, 1), D("1500"), D("180.00")),
        (date(2020, 9, 1), D("1200"), D("250.00")),
    ]:
        session.add(make_investment_lot(ben_brok.id, "NFLX", sh, basis, buy_date, "purchase"))

    # ── 10b5-1 scheduled diversification sales (systematic trims) ───────────────
    for ms in all_months():
        y, m = ms.year, ms.month
        if m in (2, 8) and ms <= DATE_END:  # semiannual pre-scheduled trim
            add(
                tx(
                    ben_brok.id,
                    clamp_day(y, m, 12),
                    -D("90000.00"),
                    "10b5-1 scheduled NFLX sale",
                    cat["equity_sale"],
                )
            )
            add(
                tx(
                    jpm_chk.id,
                    clamp_day(y, m, 13),
                    D("90000.00"),
                    "Diversification proceeds",
                    cat["equity_sale"],
                )
            )

    # ── Donor-advised fund (held away, excluded from personal net worth) ────────
    daf = acc("other_asset", "Schwab Charitable DAF", "Schwab Charitable", "7781", in_nw=False)
    await session.flush()
    add(
        tx(
            daf.id,
            date(2024, 11, 20),
            D("250000.00"),
            "Appreciated NFLX contribution",
            cat["daf_contribution"],
        )
    )
    add(
        tx(
            daf.id,
            date(2025, 11, 19),
            D("180000.00"),
            "Appreciated NFLX contribution",
            cat["daf_contribution"],
        )
    )
    for grant_date in (date(2024, 12, 10), date(2025, 6, 10), date(2025, 12, 10)):
        add(
            tx(
                daf.id,
                grant_date,
                -D("60000.00"),
                "DAF grant to charities",
                cat["daf_contribution"],
            )
        )

    # ── Securities-based line of credit (revolving) ─────────────────────────────
    sbloc = make_account(
        hid, "sbloc", "Pledged-Asset Line", "Schwab Bank", "6690", is_revolving=True
    )
    session.add(sbloc)
    await session.flush()
    add(tx(sbloc.id, date(2024, 4, 15), -D("300000.00"), "SBLOC draw", cat["sbloc_draw"]))
    for ms in all_months():
        y, m = ms.year, ms.month
        if date(y, m, 1) < date(2024, 4, 1) or ms > DATE_END:
            continue
        add(
            tx(
                sbloc.id,
                clamp_day(y, m, 28),
                -D("1450.00"),
                "SBLOC interest",
                cat["sbloc_interest"],
            )
        )
    add(tx(sbloc.id, date(2025, 6, 20), D("150000.00"), "SBLOC partial paydown", cat["sbloc_draw"]))

    # ── Margin loan at the taxable brokerage (revolving) ────────────────────────
    # Distinct from the pledged-asset SBLOC: margin borrows inside the brokerage
    # against marginable securities and is subject to maintenance calls. Drawn to
    # bridge a real-estate close; interest capitalizes monthly; partially repaid.
    margin = make_account(
        hid, "margin", "Brokerage Margin Loan", "Fidelity", "7705", is_revolving=True
    )
    session.add(margin)
    await session.flush()
    add(tx(margin.id, date(2024, 7, 10), -D("150000.00"), "Margin draw", cat["margin_draw"]))
    for ms in all_months():
        y, m = ms.year, ms.month
        if date(y, m, 1) < date(2024, 7, 1) or ms > DATE_END:
            continue
        add(
            tx(
                margin.id,
                clamp_day(y, m, 25),
                -D("700.00"),
                "Margin interest",
                cat["margin_interest"],
            )
        )
    add(
        tx(
            margin.id,
            date(2025, 12, 12),
            D("50000.00"),
            "Margin partial paydown",
            cat["margin_draw"],
        )
    )

    # ── Scheduled/specialty insurance + wine collection asset ───────────────────
    wine = acc("other_asset", "Wine Collection (manually valued)", "—", None)
    await session.flush()
    session.add(snapshot(wine.id, last_day_of(2026, 5), D("145000.00")))
    session.add(
        make_insurance_policy(
            hid,
            "scheduled_specialty",
            D("145000"),
            D("1100"),
            "annual",
            carrier="AXA Art",
            policy_number="AXA-SCH-2024-00417",
            metadata={"schedule": "fine_wine", "appraisal_date": "2024-01"},
        )
    )
    for prem_year in (2024, 2025, 2026):
        add(
            tx(
                jpm_chk.id,
                date(prem_year, 1, 22),
                -D("1100.00"),
                "AXA Art / Wine Schedule",
                cat["specialty_insurance_premium"],
            )
        )

    # ── Backdoor Roth (over the direct-Roth income limit) ───────────────────────
    for who_roth, label in ((ben_roth, "Ben"), (gab_roth, "Gabriela")):
        for yr in (2024, 2025):
            d, c = transfer(
                jpm_chk.id,
                who_roth.id,
                date(yr, 1, 12),
                D("7000.00"),
                f"{label} backdoor Roth conversion",
                cat["roth_conversion"],
            )
            add(d, c)

    # ── One-time bonus / liquidity spike ────────────────────────────────────────
    add(tx(schwab_chk.id, date(2025, 3, 15), D("220000.00"), "Performance bonus", cat["bonus"]))

    # ── Advisory notes ──────────────────────────────────────────────────────────
    session.add(
        make_advisory_note(
            hid,
            "concentration",
            "Concentrated single-stock position and 10b5-1 selling",
            "Vested RSUs plus direct holdings concentrate roughly 30% of the investment portfolio in "
            "one employer stock. A position above ~20% of net worth warrants deliberate "
            "diversification; a 10b5-1 plan lets an insider sell on a pre-scheduled basis without "
            "insider-trading exposure, trimming the position systematically rather than timing it.",
            account_id=ben_brok.id,
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "tax",
            "AMT year, backdoor Roth, and California Prop 13",
            "Exercising and holding the ISO tranche creates an AMT preference equal to the bargain "
            "element in that year, generating an AMT credit to carry forward against future regular "
            "tax. The household is over the direct-Roth income limit, so Roth funding goes through a "
            "non-deductible IRA conversion (backdoor Roth). On the residence, California Proposition 13 "
            "caps the assessed value's growth, so the property-tax basis lags well behind current "
            "market value.",
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "charitable",
            "Appreciated-stock-to-DAF mechanics and the 2026 OBBBA deduction limits",
            "Donating appreciated company stock to a donor-advised fund avoids capital-gains tax on "
            "the donated shares and gives a deduction at fair market value (subject to the 30%-of-AGI "
            "limit for long-term appreciated non-cash gifts). For 2026, OBBBA adds a 0.5%-of-AGI floor "
            "and caps the deduction benefit at 35% for top-bracket itemizers, so do not assume "
            "dollar-for-dollar benefit at the top rate.",
            account_id=daf.id,
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "concentration",
            "Margin vs. SBLOC, and the maintenance-call risk on a concentrated book",
            "Brokerage margin and a pledged-asset SBLOC both borrow against securities, but margin sits "
            "inside the brokerage and is marked daily: a drawdown in the concentrated single-stock "
            "position can trigger a maintenance call and forced sales at the worst time. An SBLOC is "
            "typically more forgiving on call terms. Keep total borrowing well below the maintenance "
            "threshold, and remember margin interest is deductible only against net investment income "
            "(Form 4952), not automatically.",
            account_id=margin.id,
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "insurance",
            "Scheduled coverage for the wine collection",
            "Fine-wine and other collectibles are excluded or sub-limited on a standard homeowners "
            "policy; a scheduled/specialty floater insures the appraised value against breakage, "
            "spoilage, and theft. Re-appraise periodically as the collection appreciates.",
            account_id=wine.id,
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "scope_omission",
            "Family-office structures (PPLI, captive insurance) are out of scope",
            "Private-placement life insurance (PPLI), captive insurance, and funded irrevocable "
            "vehicles (GRATs/SLATs/IDGTs, FLPs, dynasty trusts) belong to the >$20M family-office "
            "world and are intentionally outside HearthLedger's scope. At this level the system models "
            "revocable-trust titling, equity compensation, concentration, charitable vehicles, and "
            "SBLOC borrowing — not funded ultra-HNW transfer structures. See docs/scope-boundaries.md.",
        )
    )

    # ── Opening balance transactions ───────────────────────────────────────────
    targets = {
        jpm_chk.id: D("72400.00"),
        jpm_sav.id: D("145000.00"),
        schwab_chk.id: D("38500.00"),
        vanguard_mm.id: D("168000.00"),
        amex_plat.id: D("-8200.00"),
        amex_gold.id: D("-3800.00"),
        chase_sap.id: D("-2400.00"),
        jpm_mort.id: D("-1285000.00"),
        wf_mort.id: D("-645200.00"),
        ld_mort.id: D("-418600.00"),
        heloc.id: D("-92000.00"),
        tesla_loan.id: D("-38200.00"),
        porsche_loan.id: D("-28400.00"),
    }
    for acc_id, target in targets.items():
        needed = target - running[acc_id]
        session.add(opening_balance_tx(acc_id, needed, cat.get("between_accounts")))

    session.add_all(all_txns)

    # ── FIRE scenarios ─────────────────────────────────────────────────────────
    fire_a_streams = [
        {
            "id": str(uuid.uuid4()),
            "label": "Ben — Law Firm (until 58)",
            "type": "salary",
            "amount_annual": 650000.00,
            "start_year": 2024,
            "end_year": 2030,
            "growth_rate_annual": 0.04,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Gabriela — Consulting (full)",
            "type": "consulting",
            "amount_annual": 385000.00,
            "start_year": 2024,
            "end_year": 2030,
            "growth_rate_annual": 0.03,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Gabriela — Consulting (reduced, post-56)",
            "type": "consulting",
            "amount_annual": 120000.00,
            "start_year": 2030,
            "end_year": None,
            "growth_rate_annual": 0.02,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Silver Lake Duplex — Net Rental",
            "type": "rental",
            "amount_annual": 58000.00,
            "start_year": 2024,
            "end_year": None,
            "growth_rate_annual": 0.02,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Palm Springs STR — Net",
            "type": "rental",
            "amount_annual": 32000.00,
            "start_year": 2024,
            "end_year": None,
            "growth_rate_annual": 0.01,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Benjamin Social Security (age 70)",
            "type": "social_security",
            "amount_annual": 65000.00,
            "start_year": 2042,
            "end_year": None,
            "growth_rate_annual": 0.025,
            "is_pre_retirement": False,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Gabriela Social Security (age 70)",
            "type": "social_security",
            "amount_annual": 52000.00,
            "start_year": 2044,
            "end_year": None,
            "growth_rate_annual": 0.025,
            "is_pre_retirement": False,
        },
    ]
    session.add(
        make_fire_scenario(
            hid,
            ben.id,
            "Coast at 58 — Semi-Retirement",
            D("420000.00"),
            D("0.0650"),
            D("0.0300"),
            58,
            fire_a_streams,
        )
    )

    fire_b_streams = [
        {
            "id": str(uuid.uuid4()),
            "label": "Silver Lake Duplex — Net Rental",
            "type": "rental",
            "amount_annual": 58000.00,
            "start_year": 2024,
            "end_year": None,
            "growth_rate_annual": 0.02,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Palm Springs STR — Net",
            "type": "rental",
            "amount_annual": 32000.00,
            "start_year": 2024,
            "end_year": None,
            "growth_rate_annual": 0.01,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Benjamin Social Security (age 70)",
            "type": "social_security",
            "amount_annual": 65000.00,
            "start_year": 2042,
            "end_year": None,
            "growth_rate_annual": 0.025,
            "is_pre_retirement": False,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "Gabriela Social Security (age 70)",
            "type": "social_security",
            "amount_annual": 52000.00,
            "start_year": 2044,
            "end_year": None,
            "growth_rate_annual": 0.025,
            "is_pre_retirement": False,
        },
    ]
    session.add(
        make_fire_scenario(
            hid,
            ben.id,
            "True FIRE — Stress Test",
            D("380000.00"),
            D("0.0550"),
            D("0.0350"),
            54,
            fire_b_streams,
        )
    )

    # ── Debt record ───────────────────────────────────────────────────────────
    session.add(
        make_debt(
            tesla_loan.id,
            D("58000.00"),
            D("38200.00"),
            D("0.0790"),
            D("1288.00"),
            72,
            date(2023, 2, 1),
        )
    )

    # ── Budgets ───────────────────────────────────────────────────────────────
    for slug, amount, eff_from in [
        ("groceries", D("2000.00"), date(2024, 1, 1)),
        ("restaurants", D("2000.00"), date(2024, 1, 1)),
        ("restaurants", D("2400.00"), date(2025, 6, 1)),  # lifestyle increase
        ("coffee", D("150.00"), date(2024, 1, 1)),
        ("food_delivery", D("300.00"), date(2024, 1, 1)),
        ("gas_fuel", D("95.00"), date(2024, 1, 1)),
        ("ev_charging", D("100.00"), date(2024, 1, 1)),
        ("internet", D("120.00"), date(2024, 1, 1)),
        ("cell_phone", D("320.00"), date(2024, 1, 1)),
        ("streaming", D("91.00"), date(2024, 1, 1)),
        ("electric", D("420.00"), date(2024, 1, 1)),
        ("fitness", D("390.00"), date(2024, 1, 1)),
        ("therapy", D("880.00"), date(2024, 1, 1)),
        ("cleaning_services", D("1800.00"), date(2024, 1, 1)),
        ("lawn_garden", D("680.00"), date(2024, 1, 1)),
        ("clothing", D("1500.00"), date(2024, 1, 1)),
        ("personal_care", D("850.00"), date(2024, 1, 1)),
        ("auto_insurance", D("645.00"), date(2024, 1, 1)),
        ("home_insurance", D("520.00"), date(2024, 1, 1)),
        ("life_insurance", D("1240.00"), date(2024, 1, 1)),
        ("advisory_fees", D("1800.00"), date(2024, 1, 1)),
        ("travel", D("3000.00"), date(2024, 1, 1)),
        ("home_maintenance", D("375.00"), date(2024, 1, 1)),
        ("pet_care", D("300.00"), date(2024, 1, 1)),
        ("tuition", D("1200.00"), date(2024, 1, 1)),
        # car_maintenance: $920 reg + 2 x ~$650 service ≈ $2,220/yr / 12 ≈ $185/mo avg
        ("car_maintenance", D("185.00"), date(2024, 1, 1)),
        # doctor_medical: $400/mo concierge retainer
        ("doctor_medical", D("400.00"), date(2024, 1, 1)),
        ("pharmacy", D("120.00"), date(2024, 1, 1)),
        # dental: 2 x $680 (Apr/Oct) = $1,360/yr / 12 ≈ $113/mo avg
        ("dental", D("115.00"), date(2024, 1, 1)),
        # vision: $780/yr (Sep) / 12 ≈ $65/mo avg
        ("vision", D("65.00"), date(2024, 1, 1)),
    ]:
        session.add(make_budget(hid, cat[slug], amount, eff_from))

    return {
        "num": 3,
        "name": "Whitfield-Torres",
        "location": "Brentwood CA",
        "members": 4,
        "accounts": 29,  # +4: DAF (held away), SBLOC, margin loan, wine collection
        "transactions": len(all_txns),
        "properties": 3,
        "net_worth": 9_902_497.0,  # -$116,800 margin loan; ReportService-computed as of 2026-06-21
        "fire_scenarios": 2,
        "debt_records": 1,
    }
