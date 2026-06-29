"""State individual income-tax constants, year-keyed, for the tax-estimate engine.

Like `tax_tables`, this module is intentionally data-only and isolated so the
figures can be audited and updated annually without touching engine logic. State
brackets, standard deductions, and rates change yearly; update this file when the
new figures are published (states typically follow the federal Rev. Proc. in the
fall).

Source (verified 2026-06-29):
  - Tax Foundation, "State Individual Income Tax Rates and Brackets, 2025"
    https://taxfoundation.org/data/all/state/state-income-tax-rates/
    (rates, bracket lower bounds, and standard deductions, single + married-filing-
    jointly, for the modeled states; and the list of states with no income tax).

Scope (v1): a deliberately small, demo-relevant set of states is modeled in full
(California, New York, Georgia, Illinois). The eight states with no individual
income tax are recognized and return a real $0. Every other taxing state is
"not modeled" — the engine returns $0 with an explanatory note rather than a
wrong number. Add a state by appending its bracket table + standard deduction
here, with the same cite-and-update discipline.

Documented simplifications (state estimates are for planning, not preparation):
  - States tax long-term capital gains and qualified dividends as ordinary income;
    no preferential state schedule is applied.
  - Social Security benefits are excluded. None of the modeled states (CA, NY, GA,
    IL) tax Social Security, so this is exact for the shipped data; revisit if a
    state that taxes SS is added.
  - State-specific retirement-income exclusions are NOT applied: Illinois fully
    excludes qualified retirement income, Georgia has an age-based retirement
    exclusion, and New York has a $20k pension exclusion. Ignoring these
    overstates tax for retirees in those states; tracked as future scope.
  - States with separate head-of-household or married-filing-separately schedules
    are approximated: HoH and MFS map to the single schedule, and qualifying
    surviving spouse maps to married-filing-jointly (mirrors the federal QSS rule).
"""

from __future__ import annotations

from decimal import Decimal

# Internal filing keys. State tables publish single and married-filing-jointly
# schedules; the engine maps the five household filing statuses onto these two.
SINGLE_KEY = "single"
MFJ_KEY = "mfj"

SUPPORTED_YEARS = (2025,)

# Bracket = (lower_bound_inclusive, marginal_rate), ascending; last entry runs to
# infinity. A flat-tax state is a single-entry table starting at 0. Mirrors the
# federal `tax_tables.BracketTable` shape so the engine math is identical.
type Bracket = tuple[Decimal, Decimal]
type BracketTable = list[Bracket]

# States with no individual income tax on wage/ordinary income (Tax Foundation,
# 2025). New Hampshire's interest-and-dividends tax is fully repealed for 2025;
# Washington's capital-gains tax and New Hampshire are not modeled here, so any
# investment-income tax in those states is out of scope.
NO_INCOME_TAX_STATES = frozenset({"AK", "FL", "NV", "NH", "SD", "TN", "TX", "WY"})


def _b(*pairs: tuple[int, str]) -> BracketTable:
    return [(Decimal(lo), Decimal(rate)) for lo, rate in pairs]


# --- California (graduated; the 13.3% top includes the 1% >$1M surcharge) ------
_CA_2025: dict[str, BracketTable] = {
    SINGLE_KEY: _b(
        (0, "0.01"),
        (10_756, "0.02"),
        (25_499, "0.04"),
        (40_245, "0.06"),
        (55_866, "0.08"),
        (70_606, "0.093"),
        (360_659, "0.103"),
        (432_787, "0.113"),
        (721_314, "0.123"),
        (1_000_000, "0.133"),
    ),
    MFJ_KEY: _b(
        (0, "0.01"),
        (21_512, "0.02"),
        (50_998, "0.04"),
        (80_490, "0.06"),
        (111_732, "0.08"),
        (141_732, "0.093"),
        (721_318, "0.103"),
        (865_574, "0.113"),
        (1_000_000, "0.123"),
        (1_442_628, "0.133"),
    ),
}

# --- New York (graduated) ------------------------------------------------------
_NY_2025: dict[str, BracketTable] = {
    SINGLE_KEY: _b(
        (0, "0.04"),
        (8_500, "0.045"),
        (11_700, "0.0525"),
        (13_900, "0.055"),
        (80_650, "0.06"),
        (215_400, "0.0685"),
        (1_077_550, "0.0965"),
        (5_000_000, "0.103"),
        (25_000_000, "0.109"),
    ),
    MFJ_KEY: _b(
        (0, "0.04"),
        (17_150, "0.045"),
        (23_600, "0.0525"),
        (27_900, "0.055"),
        (161_550, "0.06"),
        (323_200, "0.0685"),
        (2_155_350, "0.0965"),
        (5_000_000, "0.103"),
        (25_000_000, "0.109"),
    ),
}

# --- Georgia (flat 5.39%) ------------------------------------------------------
_GA_2025: dict[str, BracketTable] = {
    SINGLE_KEY: _b((0, "0.0539")),
    MFJ_KEY: _b((0, "0.0539")),
}

# --- Illinois (flat 4.95%) -----------------------------------------------------
_IL_2025: dict[str, BracketTable] = {
    SINGLE_KEY: _b((0, "0.0495")),
    MFJ_KEY: _b((0, "0.0495")),
}

STATE_BRACKETS: dict[int, dict[str, dict[str, BracketTable]]] = {
    2025: {
        "CA": _CA_2025,
        "NY": _NY_2025,
        "GA": _GA_2025,
        "IL": _IL_2025,
    },
}

# State standard deduction by filing key. Illinois has no standard deduction; it
# uses a personal exemption that functions as an equivalent income subtraction
# ($2,850 single / $5,700 married), modeled here in that slot.
STATE_STANDARD_DEDUCTION: dict[int, dict[str, dict[str, Decimal]]] = {
    2025: {
        "CA": {SINGLE_KEY: Decimal("5540"), MFJ_KEY: Decimal("11080")},
        "NY": {SINGLE_KEY: Decimal("8000"), MFJ_KEY: Decimal("16050")},
        "GA": {SINGLE_KEY: Decimal("12000"), MFJ_KEY: Decimal("24000")},
        "IL": {SINGLE_KEY: Decimal("2850"), MFJ_KEY: Decimal("5700")},
    },
}
