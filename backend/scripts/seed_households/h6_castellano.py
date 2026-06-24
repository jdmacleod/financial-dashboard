"""Household 6 — Castellano (Scarsdale, NY). ~$18.29M net worth.

Rosa Castellano, 74, widowed and retired in Westchester County. The dataset's
only single-member household: one primary principal, full visibility, zero
access grants. Carries the full estate-and-legacy stack — revocable trust
titling, an ILIT-owned permanent policy and a charitable remainder unitrust
(both outside personal net worth and the taxable estate), a donor-advised fund,
a legacy concentrated stock position with stepped-up basis, an inherited IRA on
the SECURE 10-year clock, a private-equity commitment with capital calls, and a
revolving SBLOC. Single decumulation FIRE scenario.

Net worth (ReportService-computed as of 2026-06-01) is set on the summary below.
The deterministic inventory sums to ~$18,290,000: assets $18,810,000 less the
$520,000 SBLOC. CRT (~$2.5M), the ILIT-owned policy, and the DAF (~$1.1M) are
deliberately excluded from personal net worth.
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
    clamp_day,
    make_account,
    make_advisory_note,
    make_budget,
    make_capital_commitment,
    make_fire_scenario,
    make_household,
    make_insurance_policy,
    make_investment_lot,
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
    # ── Household & single member (degenerate RBAC: one principal, no grants) ───
    hh = make_household("Castellano Household")
    session.add(hh)
    hid = hh.id

    rosa = make_member(hid, "Rosa Castellano", "primary", date_of_birth=date(1951, 6, 10))
    session.add(rosa)
    session.add(make_user(rosa.id, "rosa@castellano.local"))
    await session.flush()

    cat = await seed_categories(session, hid)

    # ── Ownership entities ──────────────────────────────────────────────────────
    rev_trust = make_ownership_entity(
        hid,
        "revocable_trust",
        "Castellano Family Revocable Trust",
        counts_in_net_worth=True,
        in_taxable_estate=True,
        grantor_member_id=rosa.id,
    )
    ilit = make_ownership_entity(
        hid,
        "ilit",
        "Castellano Irrevocable Life Insurance Trust",
        counts_in_net_worth=False,
        in_taxable_estate=False,
        grantor_member_id=rosa.id,
    )
    crt = make_ownership_entity(
        hid,
        "crt_crut",
        "Castellano Charitable Remainder Unitrust",
        counts_in_net_worth=False,
        in_taxable_estate=False,
        grantor_member_id=rosa.id,
    )
    session.add_all([rev_trust, ilit, crt])
    await session.flush()

    # ── Accounts ──────────────────────────────────────────────────────────────
    def acc(atype, name, inst, last4, *, in_nw=True, entity_id=None, revolving=False):
        a = make_account(
            hid,
            atype,
            name,
            inst,
            last4,
            owner_member_id=rosa.id,
            include_in_net_worth=in_nw,
            ownership_entity_id=entity_id,
            is_revolving=revolving,
        )
        session.add(a)
        return a

    checking = acc("checking", "Private Client Checking", "JPMorgan Chase Private", "4417")
    savings = acc("savings", "Private Client Savings", "JPMorgan Chase Private", "4418")
    diversified = acc(
        "investment_brokerage",
        "Diversified Taxable Brokerage",
        "Fidelity PWM",
        "5521",
        entity_id=rev_trust.id,
    )
    legacy_stock = acc("investment_brokerage", "Legacy Concentrated Stock", "Fidelity PWM", "5522")
    mm_cash = acc("investment_brokerage", "Money-Market Sweep", "Fidelity PWM", "5523")
    rollover_ira = acc("retirement_ira", "Spousal Rollover IRA", "Fidelity PWM", "6610")
    inherited_ira = acc("inherited_ira", "Inherited IRA (sister)", "Fidelity PWM", "6611")
    roth = acc("retirement_roth_ira", "Roth IRA", "Fidelity PWM", "6612")
    treasury = acc("treasury", "Treasury / T-Bill Ladder", "Fidelity PWM", "6613")
    whole_life_cv = acc(
        "life_insurance_cash_value", "Whole Life Cash Value", "Northwestern Mutual", "7720"
    )
    art = acc("other_asset", "Art Collection (manually valued)", "—", None)
    pe_fund = acc(
        "private_fund", "Meridian Private Equity Fund III NAV", "Meridian Capital", "8830"
    )
    sbloc = acc("sbloc", "Pledged-Asset Line (SBLOC)", "Fidelity PWM", "9940", revolving=True)
    residence_re = acc("real_estate", "Scarsdale Residence", "—", None, entity_id=rev_trust.id)
    coop_re = acc("real_estate", "Manhattan Co-op", "—", None, entity_id=rev_trust.id)

    # Excluded from personal net worth (exercise the ownership-entity / held-away path)
    crt_brok = acc(
        "investment_brokerage",
        "CRT Investment Account",
        "Fidelity Charitable",
        "8841",
        in_nw=False,
        entity_id=crt.id,
    )
    daf = acc(
        "other_asset", "Castellano Donor-Advised Fund", "Fidelity Charitable", "8842", in_nw=False
    )
    await session.flush()

    # ── Real estate (titled in the revocable trust) ─────────────────────────────
    prop_residence = make_property(
        residence_re.id,
        "27 Heathcote Manor Rd, Scarsdale, NY 10583",
        "primary_residence",
        date(1998, 5, 1),
        D("950000.00"),
        ownership_entity_id=rev_trust.id,
    )
    prop_coop = make_property(
        coop_re.id,
        "180 Riverside Dr, Apt 8C, New York, NY 10024",
        "other",
        date(2005, 9, 1),
        D("740000.00"),
        ownership_entity_id=rev_trust.id,
    )
    session.add_all([prop_residence, prop_coop])
    await session.flush()
    for val_date, amt in [
        (date(2024, 1, 1), D("3650000.00")),
        (date(2024, 10, 1), D("3680000.00")),
        (date(2025, 6, 1), D("3740000.00")),
        (date(2026, 6, 1), D("3800000.00")),
    ]:
        session.add(make_valuation(prop_residence.id, val_date, amt))
    for val_date, amt in [
        (date(2024, 1, 1), D("1170000.00")),
        (date(2025, 1, 1), D("1185000.00")),
        (date(2026, 6, 1), D("1200000.00")),
    ]:
        session.add(make_valuation(prop_coop.id, val_date, amt))

    # ── Snapshot series (explicit; ending value = inventory target as of 2026-05) ─
    def snaps(account, points):
        for d, v in points:
            session.add(snapshot(account.id, d, D(v)))

    dip = (date(2024, 10, 31), None)  # 2024 market dip reflected in the series below
    snaps(
        diversified,
        [
            (date(2024, 1, 31), "3300000.00"),
            (dip[0], "3120000.00"),
            (date(2025, 6, 30), "3280000.00"),
            (date(2026, 5, 31), "3400000.00"),
        ],
    )
    # Legacy concentrated position — single ticker, trimmed via scheduled sales.
    snaps(
        legacy_stock,
        [
            (date(2024, 1, 31), "2480000.00"),
            (date(2024, 10, 31), "2360000.00"),
            (date(2025, 6, 30), "2360000.00"),
            (date(2026, 5, 31), "2300000.00"),
        ],
    )
    snaps(mm_cash, [(date(2024, 1, 31), "350000.00"), (date(2026, 5, 31), "400000.00")])
    # Rollover IRA decumulates via RMDs.
    snaps(
        rollover_ira,
        [
            (date(2024, 1, 31), "2950000.00"),
            (date(2024, 10, 31), "2880000.00"),
            (date(2025, 6, 30), "2840000.00"),
            (date(2026, 5, 31), "2800000.00"),
        ],
    )
    # Inherited IRA on the SECURE 10-year clock (full depletion by 2033).
    snaps(
        inherited_ira,
        [
            (date(2024, 1, 31), "700000.00"),
            (date(2025, 6, 30), "660000.00"),
            (date(2026, 5, 31), "620000.00"),
        ],
    )
    snaps(roth, [(date(2024, 1, 31), "840000.00"), (date(2026, 5, 31), "900000.00")])
    snaps(treasury, [(date(2024, 1, 31), "680000.00"), (date(2026, 5, 31), "700000.00")])
    snaps(whole_life_cv, [(date(2024, 1, 31), "382000.00"), (date(2026, 5, 31), "410000.00")])
    snaps(art, [(date(2024, 1, 31), "760000.00"), (date(2026, 5, 31), "800000.00")])
    snaps(
        pe_fund,
        [
            (date(2024, 1, 31), "980000.00"),
            (date(2025, 6, 30), "1120000.00"),
            (date(2026, 5, 31), "1180000.00"),
        ],
    )
    # Excluded-from-NW accounts (still get balances for in-app display).
    snaps(crt_brok, [(date(2024, 1, 31), "2450000.00"), (date(2026, 5, 31), "2500000.00")])
    snaps(daf, [(date(2024, 1, 31), "1050000.00"), (date(2026, 5, 31), "1100000.00")])

    # ── Cost-basis lots: legacy position stepped up at David's 2022 death ───────
    session.add(
        make_investment_lot(
            legacy_stock.id, "INDP", D("18000"), D("83.33"), date(2022, 6, 15), "inherited_stepup"
        )
    )  # basis ≈ 1,500,000
    session.add(
        make_investment_lot(
            diversified.id, "VTI", D("12000"), D("220.00"), date(2015, 3, 1), "purchase"
        )
    )  # single synthetic lot ok

    # ── Capital commitment (private equity) ─────────────────────────────────────
    session.add(
        make_capital_commitment(
            hid,
            "Meridian Private Equity Fund III",
            D("2000000.00"),
            D("1300000.00"),
            pe_fund.id,
            2021,
        )
    )

    # ── Insurance ────────────────────────────────────────────────────────────────
    # Rosa's whole life — cash value is a net-worth asset (not ILIT-owned).
    session.add(
        make_insurance_policy(
            hid,
            "permanent_life",
            D("750000"),
            D("4200"),
            "quarterly",
            insured_member_id=rosa.id,
            cash_value_account_id=whole_life_cv.id,
            carrier="Northwestern Mutual",
            policy_number="NM-WL-2001-3389045",
            metadata={"purpose": "legacy"},
        )
    )
    # ILIT-owned permanent policy — death benefit outside the estate; NOT in NW.
    session.add(
        make_insurance_policy(
            hid,
            "permanent_life",
            D("3000000"),
            D("45000"),
            "annual",
            insured_member_id=rosa.id,
            owner_ownership_entity_id=ilit.id,
            carrier="Northwestern Mutual",
            policy_number="NM-WL-2006-4412198",
            metadata={"purpose": "estate_liquidity", "owned_by": "ilit"},
        )
    )
    # Homeowners for both properties
    session.add(
        make_insurance_policy(
            hid,
            "homeowners",
            D("4500000"),
            D("9200"),
            "annual",
            carrier="Chubb",
            policy_number="CHB-HO3-2018-5521904",
            technical_notes="Masterpiece HO-3; replacement cost; fine arts blanket $500K",
            insured_real_estate_id=prop_residence.id,
        )
    )
    session.add(
        make_insurance_policy(
            hid,
            "homeowners",
            D("2200000"),
            D("4800"),
            "annual",
            carrier="Chubb",
            policy_number="CHB-HO6-2020-6631082",
            technical_notes="HO-6 co-op unit; loss assessment coverage; board approval rider",
            insured_real_estate_id=prop_coop.id,
        )
    )
    session.add(
        make_insurance_policy(
            hid,
            "umbrella_liability",
            D("10000000"),
            D("2100"),
            "annual",
            carrier="Chubb",
            policy_number="CHB-UMB-9921037",
            metadata={"underlying": ["auto", "scarsdale_home", "manhattan_coop"]},
        )
    )
    session.add(
        make_insurance_policy(
            hid,
            "long_term_care",
            D("500000"),
            D("6200"),
            "annual",
            insured_member_id=rosa.id,
            carrier="Genworth",
            policy_number="GNW-LTC-2012-0087334",
            metadata={"daily_benefit": 400, "inflation_rider": "3pct_compound"},
        )
    )
    session.add(
        make_insurance_policy(
            hid,
            "scheduled_specialty",
            D("800000"),
            D("4800"),
            "annual",
            carrier="AXA Art",
            policy_number="AXA-SCH-2022-00891",
            metadata={"schedule": "fine_art", "appraisal_date": "2024-02"},
        )
    )

    # ── Transactions ─────────────────────────────────────────────────────────────
    all_txns: list = []
    running: dict[uuid.UUID, D] = {
        checking.id: D("0"),
        savings.id: D("0"),
        sbloc.id: D("0"),
    }

    def add(*txs):
        for t in txs:
            all_txns.append(t)
            if t.account_id in running:
                running[t.account_id] += t.amount

    for ms in all_months():
        y, m = ms.year, ms.month
        if ms > DATE_END:
            break

        # Income (to checking)
        add(
            tx(
                checking.id,
                clamp_day(y, m, 3),
                D("4200.00"),
                "SSA — Survivor Benefit",
                cat["social_security_income"],
            )
        )
        add(
            tx(
                checking.id,
                clamp_day(y, m, 10),
                D("9800.00"),
                "Brokerage dividends + T-bill interest",
                cat["dividends"],
            )
        )
        if m in (3, 6, 9, 12):  # CRT unitrust, quarterly (~$125K/yr)
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 15),
                    D("31250.00"),
                    "CRT unitrust distribution",
                    cat["crt_income"],
                )
            )
            # Rollover-IRA RMD net of QCD: ~$60K/yr taxable cash, quarterly.
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 18),
                    D("15000.00"),
                    "RMD — Spousal Rollover IRA",
                    cat["rmd_distribution"],
                )
            )
            # Inherited-IRA RMD (SECURE 10-year), quarterly.
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 20),
                    D("16000.00"),
                    "RMD — Inherited IRA",
                    cat["inherited_ira_rmd"],
                )
            )

        # Medicare top IRMAA tier (single filer) + Medigap; steps up across years.
        if y == 2024:
            part_b, part_d = D("594.00"), D("82.00")
        elif y == 2025:
            part_b, part_d = D("628.90"), D("86.00")
        else:
            part_b, part_d = D("650.00"), D("90.00")
        add(
            tx(
                checking.id,
                clamp_day(y, m, 2),
                -part_b,
                "Medicare Part B (IRMAA top tier)",
                cat["medicare_part_b"],
            )
        )
        add(
            tx(
                checking.id,
                clamp_day(y, m, 2),
                -part_d,
                "Medicare Part D (IRMAA top tier)",
                cat["medicare_part_d"],
            )
        )
        add(
            tx(
                checking.id,
                clamp_day(y, m, 3),
                -D("310.00"),
                "UnitedHealthcare Medigap Plan G",
                cat["medigap_supplement"],
            )
        )

        # Co-op maintenance (monthly) + Westchester property tax (semiannual ~$60K/yr)
        add(
            tx(
                checking.id,
                clamp_day(y, m, 1),
                -D("2650.00"),
                "Manhattan Co-op Maintenance",
                cat["hoa_fees"],
            )
        )
        if m in (1, 7):
            add(
                tx(
                    checking.id,
                    clamp_day(y, m, 10),
                    -D("30000.00"),
                    "Westchester County Property Tax",
                    cat["home_property_tax"],
                )
            )

        # SBLOC interest (monthly) once drawn
        if (y, m) >= (2024, 5):
            add(
                tx(
                    sbloc.id,
                    clamp_day(y, m, 28),
                    -D("2300.00"),
                    "SBLOC interest",
                    cat["sbloc_interest"],
                )
            )

    # ── Discrete events ───────────────────────────────────────────────────────
    # PE capital calls against the outstanding commitment, and one distribution.
    add(
        *transfer(
            mm_cash.id,
            pe_fund.id,
            date(2024, 3, 14),
            D("150000.00"),
            "Meridian PE — capital call",
            cat["capital_call"],
        )
    )
    add(
        *transfer(
            mm_cash.id,
            pe_fund.id,
            date(2024, 11, 12),
            D("180000.00"),
            "Meridian PE — capital call",
            cat["capital_call"],
        )
    )
    add(
        tx(
            checking.id,
            date(2025, 9, 18),
            D("220000.00"),
            "Meridian PE — distribution",
            cat["capital_distribution"],
        )
    )

    # SBLOC: draw in 2024, partial paydown in 2025 (target reconciles to -520K below).
    add(tx(sbloc.id, date(2024, 5, 6), -D("520000.00"), "SBLOC draw", cat["sbloc_draw"]))
    add(tx(sbloc.id, date(2025, 4, 22), D("60000.00"), "SBLOC partial paydown", cat["sbloc_draw"]))

    # Annual-exclusion gifts ($19K per recipient: 2 children + 3 grandchildren).
    for gift_year in (2024, 2025, 2026):
        if date(gift_year, 1, 1) <= DATE_END:
            add(
                tx(
                    checking.id,
                    clamp_day(gift_year, 1, 20),
                    -D("95000.00"),
                    "Annual-exclusion gifts (children & grandchildren)",
                    cat["annual_exclusion_gift"],
                )
            )

    # Annual gift to ILIT funding the ~$45K premium (Crummey-style).
    for gift_year in (2024, 2025, 2026):
        if date(gift_year, 1, 1) <= DATE_END:
            add(
                tx(
                    checking.id,
                    clamp_day(gift_year, 2, 15),
                    -D("45000.00"),
                    "Gift to ILIT (premium funding)",
                    cat["gift_to_ilit"],
                )
            )

    # Systematic diversification trims of the legacy concentrated position.
    for ms in all_months():
        y, m = ms.year, ms.month
        if m in (3, 9) and ms <= DATE_END:
            add(
                tx(
                    legacy_stock.id,
                    clamp_day(y, m, 12),
                    -D("60000.00"),
                    "Scheduled diversification sale (legacy stock)",
                    cat["equity_sale"],
                )
            )

    # QCD satisfying part of the RMD (excluded from income; direct to charity).
    for qcd_year in (2025, 2026):
        if date(qcd_year, 11, 1) <= DATE_END:
            add(
                tx(
                    rollover_ira.id,
                    clamp_day(qcd_year, 11, 15),
                    -D("50000.00"),
                    "QCD — direct to public charity",
                    cat["qcd_note"],
                )
            )

    # Other premiums + a modest art acquisition.
    for prem_year in (2024, 2025, 2026):
        add(
            tx(
                checking.id,
                date(prem_year, 1, 12),
                -D("2100.00"),
                "Chubb Umbrella Policy",
                cat["umbrella_premium"],
            )
        )
        add(
            tx(
                checking.id,
                date(prem_year, 1, 14),
                -D("4800.00"),
                "AXA Art Schedule",
                cat["specialty_insurance_premium"],
            )
        )
        if prem_year < 2026:
            add(
                tx(
                    checking.id,
                    date(prem_year, 9, 10),
                    -D("6200.00"),
                    "Genworth LTC",
                    cat["ltc_insurance_premium"],
                )
            )
        for q in (3, 6, 9, 12):
            if date(prem_year, q, 1) <= DATE_END:
                add(
                    tx(
                        checking.id,
                        clamp_day(prem_year, q, 14),
                        -D("4200.00"),
                        "Northwestern Mutual Whole Life",
                        cat["permanent_life_premium"],
                    )
                )
    add(
        tx(
            checking.id,
            date(2025, 5, 8),
            -D("85000.00"),
            "Sotheby's — art acquisition",
            cat["hobbies"],
        )
    )

    # ── Opening balances ────────────────────────────────────────────────────────
    targets: dict[uuid.UUID, D] = {
        checking.id: D("120000.00"),
        savings.id: D("180000.00"),
        sbloc.id: D("-520000.00"),
    }
    for acc_id, target in targets.items():
        session.add(
            opening_balance_tx(acc_id, target - running[acc_id], cat.get("between_accounts"))
        )

    session.add_all(all_txns)

    # ── FIRE scenario — single-life decumulation ────────────────────────────────
    fire = make_fire_scenario(
        hid,
        rosa.id,
        "Single-Life Decumulation (estate-exposed)",
        D("420000.00"),
        D("0.0500"),
        D("0.0300"),
        95,
        [
            {
                "id": str(uuid.uuid4()),
                "label": "SSA survivor benefit",
                "type": "social_security",
                "amount_annual": 50400.00,
                "start_year": 2024,
                "end_year": None,
                "growth_rate_annual": 0.025,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "CRT unitrust income",
                "type": "other",
                "amount_annual": 125000.00,
                "start_year": 2024,
                "end_year": None,
                "growth_rate_annual": 0.0,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "RMDs + dividends + T-bill interest",
                "type": "investment",
                "amount_annual": 178000.00,
                "start_year": 2024,
                "end_year": None,
                "growth_rate_annual": 0.0,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "Inherited-IRA RMD (declining, depletes 2033)",
                "type": "investment",
                "amount_annual": 64000.00,
                "start_year": 2024,
                "end_year": 2033,
                "growth_rate_annual": -0.08,
                "is_pre_retirement": False,
            },
            {
                "id": str(uuid.uuid4()),
                "label": "PE distributions (irregular)",
                "type": "other",
                "amount_annual": 70000.00,
                "start_year": 2024,
                "end_year": 2028,
                "growth_rate_annual": 0.0,
                "is_pre_retirement": False,
            },
        ],
        safe_withdrawal_rate=D("0.0500"),
    )
    session.add(fire)

    # ── Budget (decumulation) with a Medicare/IRMAA budget-history step ─────────
    budget_rows = [
        ("home_property_tax", D("5000.00"), date(2024, 1, 1)),
        ("hoa_fees", D("2650.00"), date(2024, 1, 1)),
        ("home_maintenance", D("3500.00"), date(2024, 1, 1)),
        ("travel", D("6000.00"), date(2024, 1, 1)),
        ("medicare_part_b", D("594.00"), date(2024, 1, 1)),
        ("medicare_part_b", D("628.90"), date(2025, 1, 1)),  # IRMAA step-up
        ("medicare_part_b", D("650.00"), date(2026, 1, 1)),  # IRMAA step-up
        ("medigap_supplement", D("310.00"), date(2024, 1, 1)),
        ("advisory_fees", D("9500.00"), date(2024, 1, 1)),
        ("gifts_given", D("2000.00"), date(2024, 1, 1)),
        ("personal_care", D("800.00"), date(2024, 1, 1)),
        ("restaurants", D("1500.00"), date(2024, 1, 1)),
        ("ltc_insurance_premium", D("520.00"), date(2024, 1, 1)),
        ("umbrella_premium", D("175.00"), date(2024, 1, 1)),
    ]
    for slug, amount, eff_from in budget_rows:
        session.add(make_budget(hid, cat[slug], amount, eff_from))

    # ── Advisory notes ──────────────────────────────────────────────────────────
    session.add(
        make_advisory_note(
            hid,
            "estate",
            "Combined federal + New York estate exposure drives the ILIT liquidity plan",
            "At ~$18.3M the estate is ~$3.3M over the permanent $15M federal exemption (40% top rate) "
            "and fully exposed at the New York level: NY's $7.35M exemption has no portability and a "
            "cliff that taxes the entire estate once it exceeds 105% of the exemption, at rates up to "
            "16%. The ILIT-owned policy provides liquidity to pay the combined tax without a forced "
            "sale of the illiquid PE and concentrated-stock holdings.",
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "retirement",
            "Inherited IRA: SECURE 10-year depletion deadline",
            "The inherited IRA (sister, d. 2023) must be fully distributed by the end of 2033 under the "
            "SECURE Act 10-year rule, with annual RMDs along the way. Sequencing these distributions "
            "around the rollover-IRA RMDs and IRMAA tiers manages the year-to-year income spikes.",
            account_id=inherited_ira.id,
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "concentration",
            "Legacy single-stock position with 2022 step-up basis",
            "The legacy position is one public ticker that received a basis step-up at David's 2022 "
            "death (basis ≈ $1.5M) and has appreciated since. Systematic quarterly trims realize "
            "long-term gains against the stepped-up lots while reducing single-stock risk.",
            account_id=legacy_stock.id,
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "charitable",
            "Coordinated CRT + DAF + QCD giving strategy",
            "The CRUT was funded in 2023 with low-basis stock: it defers the capital gain, pays Rosa a "
            "5% lifetime income stream (taxed under the four-tier rules), and gave an up-front "
            "deduction for the present value of the remainder, with a DAF named as remainder "
            "beneficiary for flexibility. Separately, a QCD from the IRA satisfies part of the RMD while "
            "staying out of taxable income — a QCD must go directly to a public charity, not the DAF.",
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "tax",
            "Single-filer brackets and single-filer IRMAA thresholds",
            "As a single filer Rosa hits the top income-tax brackets and the top IRMAA tier at roughly "
            "half the income thresholds that apply to a married couple, so Medicare Part B/D surcharges "
            "and bracket creep bite earlier. Conversions, QCDs, and gain realization are sized against "
            "the single-filer thresholds, not joint.",
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "insurance",
            "Whole-life cash value (asset) vs. the ILIT-owned policy (excluded)",
            "Rosa's own whole-life policy has cash value that is a balance-sheet asset in her net worth. "
            "The separate ~$3M permanent policy is owned by the ILIT, so neither its cash value nor its "
            "death benefit is in her net worth or her taxable estate — that is the whole point of the "
            "ILIT. Premiums on the ILIT policy are funded by annual Crummey gifts.",
        )
    )
    session.add(
        make_advisory_note(
            hid,
            "scope_omission",
            "Funded irrevocable vehicles beyond the ILIT and CRT are out of scope",
            "HearthLedger deliberately stops at revocable-trust titling plus the single ILIT and CRT "
            "modeled here, justified by the $15M federal estate boundary a single filer at ~$18.3M "
            "actually crosses. Funded GRATs/SLATs/IDGTs, dynasty trusts, family limited partnerships, "
            "private-placement life insurance, and captive insurance belong to the >$20M family-office "
            "world and are intentionally not modeled. See docs/scope-boundaries.md.",
        )
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    # ReportService-computed net worth as of 2026-06-21 (end of seed window) —
    # matches the spec inventory exactly: assets $18.81M less the $520K SBLOC.
    return {
        "num": 6,
        "name": "Castellano",
        "location": "Scarsdale NY",
        "members": 1,
        "accounts": 17,
        "transactions": len(all_txns),
        "properties": 2,
        "net_worth": 18_290_000.0,
        "fire_scenarios": 1,
        "debt_records": 0,
    }
