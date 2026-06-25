"""Federal tax constants, year-keyed, for the tax-estimate engine.

This module is intentionally data-only and isolated so the figures can be audited
and updated annually without touching engine logic. Update it each year when the
IRS releases the inflation-adjusted figures (typically a Rev. Proc. in Oct/Nov).

Sources (verified 2026-06-25):
  - 2025 brackets + standard deduction: IRS Rev. Proc. 2024-40 as amended by the
    One Big Beautiful Bill Act (OBBBA, 2025), via Tax Foundation
    https://taxfoundation.org/data/all/federal/2025-tax-brackets/
  - 2026 brackets + standard deduction: via Tax Foundation
    https://taxfoundation.org/data/all/federal/2026-tax-brackets/
  - Social Security provisional-income base amounts: 26 U.S.C. §86 (statutory,
    NOT inflation-indexed; unchanged since 1993).

Scope (v1): ordinary-income brackets, the standard deduction, and the preferential
long-term capital-gains / qualified-dividend rate schedule (0/15/20%). AMT, NIIT,
additional Medicare tax, itemized deductions, credits, the senior add-on deduction,
and state income tax are out of scope and tracked separately.

Capital-gains rate breakpoints (2025 = IRS Rev. Proc. 2024-40, 2026 = Rev. Proc.
2025-32) verified 2026-06-25 via published IRS / Tax Foundation figures.

Married-filing-separately (MFS) uses the Single schedule for the lower brackets and
half the MFJ thresholds at the top two brackets (the standard MFS construction).
Qualifying-surviving-spouse (QSS) uses the MFJ rate schedule and standard deduction,
but the §86 "all others" Social Security base amounts ($25k/$34k), per statute.
"""

from __future__ import annotations

from decimal import Decimal

# Filing-status keys mirror households.filing_status (app.db.models.household).
SINGLE = "single"
MFJ = "married_filing_jointly"
MFS = "married_filing_separately"
HOH = "head_of_household"
QSS = "qualifying_surviving_spouse"

SUPPORTED_YEARS = (2025, 2026)

# Bracket = (lower_bound_inclusive, marginal_rate), ascending. The last entry runs
# to infinity. Tax on taxable income X = sum over brackets of rate * (X-portion in
# that bracket).
type Bracket = tuple[Decimal, Decimal]
type BracketTable = list[Bracket]


def _d(*pairs: tuple[int, str]) -> BracketTable:
    return [(Decimal(lo), Decimal(rate)) for lo, rate in pairs]


_2025: dict[str, BracketTable] = {
    SINGLE: _d(
        (0, "0.10"),
        (11_925, "0.12"),
        (48_475, "0.22"),
        (103_350, "0.24"),
        (197_300, "0.32"),
        (250_525, "0.35"),
        (626_350, "0.37"),
    ),
    MFJ: _d(
        (0, "0.10"),
        (23_850, "0.12"),
        (96_950, "0.22"),
        (206_700, "0.24"),
        (394_600, "0.32"),
        (501_050, "0.35"),
        (751_600, "0.37"),
    ),
    HOH: _d(
        (0, "0.10"),
        (17_000, "0.12"),
        (64_850, "0.22"),
        (103_350, "0.24"),
        (197_300, "0.32"),
        (250_500, "0.35"),
        (626_350, "0.37"),
    ),
    MFS: _d(
        (0, "0.10"),
        (11_925, "0.12"),
        (48_475, "0.22"),
        (103_350, "0.24"),
        (197_300, "0.32"),
        (250_525, "0.35"),
        (375_800, "0.37"),
    ),
}
_2025[QSS] = _2025[MFJ]

_2026: dict[str, BracketTable] = {
    SINGLE: _d(
        (0, "0.10"),
        (12_400, "0.12"),
        (50_400, "0.22"),
        (105_700, "0.24"),
        (201_775, "0.32"),
        (256_225, "0.35"),
        (640_600, "0.37"),
    ),
    MFJ: _d(
        (0, "0.10"),
        (24_800, "0.12"),
        (100_800, "0.22"),
        (211_400, "0.24"),
        (403_550, "0.32"),
        (512_450, "0.35"),
        (768_700, "0.37"),
    ),
    HOH: _d(
        (0, "0.10"),
        (17_700, "0.12"),
        (67_450, "0.22"),
        (105_700, "0.24"),
        (201_775, "0.32"),
        (256_200, "0.35"),
        (640_600, "0.37"),
    ),
    MFS: _d(
        (0, "0.10"),
        (12_400, "0.12"),
        (50_400, "0.22"),
        (105_700, "0.24"),
        (201_775, "0.32"),
        (256_225, "0.35"),
        (384_350, "0.37"),
    ),
}
_2026[QSS] = _2026[MFJ]

FEDERAL_BRACKETS: dict[int, dict[str, BracketTable]] = {2025: _2025, 2026: _2026}

STANDARD_DEDUCTION: dict[int, dict[str, Decimal]] = {
    2025: {
        SINGLE: Decimal("15750"),
        MFJ: Decimal("31500"),
        MFS: Decimal("15750"),
        HOH: Decimal("23625"),
        QSS: Decimal("31500"),
    },
    2026: {
        SINGLE: Decimal("16100"),
        MFJ: Decimal("32200"),
        MFS: Decimal("16100"),
        HOH: Decimal("24150"),
        QSS: Decimal("32200"),
    },
}

# Long-term capital-gains / qualified-dividend preferential rate schedule. Rates
# are a fixed 0% / 15% / 20%; only the breakpoints are inflation-indexed. Each
# entry is (zero_rate_ceiling, fifteen_rate_ceiling) measured against TOTAL taxable
# income: qualified income stacked on top of ordinary taxable income is taxed at 0%
# up to the first ceiling, 15% up to the second, and 20% above it.
type CapGainsBreakpoints = tuple[Decimal, Decimal]

CAPITAL_GAINS_RATES = (Decimal("0.00"), Decimal("0.15"), Decimal("0.20"))

CAPITAL_GAINS_BREAKPOINTS: dict[int, dict[str, CapGainsBreakpoints]] = {
    2025: {
        SINGLE: (Decimal("48350"), Decimal("533400")),
        MFJ: (Decimal("96700"), Decimal("600050")),
        HOH: (Decimal("64750"), Decimal("566700")),
        MFS: (Decimal("48350"), Decimal("300000")),
    },
    2026: {
        SINGLE: (Decimal("49450"), Decimal("545500")),
        MFJ: (Decimal("98900"), Decimal("613700")),
        HOH: (Decimal("66200"), Decimal("579600")),
        MFS: (Decimal("49450"), Decimal("306850")),
    },
}
# QSS uses the MFJ schedule (mirrors the ordinary brackets above).
CAPITAL_GAINS_BREAKPOINTS[2025][QSS] = CAPITAL_GAINS_BREAKPOINTS[2025][MFJ]
CAPITAL_GAINS_BREAKPOINTS[2026][QSS] = CAPITAL_GAINS_BREAKPOINTS[2026][MFJ]

# §86 base amounts (base1 -> up to 50% taxable, base2 -> up to 85% taxable).
# MFS living with spouse is $0/$0 (up to 85% taxable from the first dollar); we
# model MFS as that common case.
SS_PROVISIONAL_BASE: dict[str, tuple[Decimal, Decimal]] = {
    SINGLE: (Decimal("25000"), Decimal("34000")),
    HOH: (Decimal("25000"), Decimal("34000")),
    QSS: (Decimal("25000"), Decimal("34000")),
    MFJ: (Decimal("32000"), Decimal("44000")),
    MFS: (Decimal("0"), Decimal("0")),
}
