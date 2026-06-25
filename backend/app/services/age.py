"""Pure age arithmetic over a member's date of birth.

No database, no session — this is the single source of age math shared by FIRE
projections, RMD calculations, and (later) the milestone timeline. Keeping it
pure keeps every age-based engine consistent and trivially testable.

Two age notions live here, and the distinction matters:

  current_age(dob, as_of)  -> completed years lived, MONTH/DAY accurate. A
                              birthday that hasn't happened yet this year does
                              not count. Use for "your current age" displays.

  age_in_year(dob, year)   -> the age the member REACHES during calendar `year`
                              (= year - birth_year). Use for year-by-year
                              projection rows, where each row is one full year
                              and the conventional label is "the age you turn
                              that year."
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


def current_age(dob: date | None, as_of: date | None = None) -> int | None:
    """Completed years lived as of ``as_of`` (today when omitted).

    Month/day accurate: someone born 1990-12-31 is 33, not 34, on 2024-06-01.
    Returns ``None`` when ``dob`` is unknown so callers can render an
    "add your birthdate" prompt rather than a wrong number.
    """
    if dob is None:
        return None
    on = as_of if as_of is not None else date.today()
    years = on.year - dob.year
    # The birthday hasn't occurred yet this year -> subtract one completed year.
    if (on.month, on.day) < (dob.month, dob.day):
        years -= 1
    return years


def age_in_year(dob: date | None, year: int) -> int | None:
    """The age the member reaches during calendar ``year`` (= year - birth_year).

    This is the conventional "age that year" for a year-by-year projection row.
    Returns ``None`` when ``dob`` is unknown.
    """
    if dob is None:
        return None
    return year - dob.year


def year_turning_age(dob: date | None, age: int) -> int | None:
    """The calendar year in which the member turns ``age`` (= birth_year + age).

    Used to place age-triggered events (RMD start, Social Security, Medicare)
    on a timeline. Returns ``None`` when ``dob`` is unknown.
    """
    if dob is None:
        return None
    return dob.year + age


def rmd_start_age(dob: date | None) -> int | None:
    """Age at which Required Minimum Distributions begin, per SECURE 2.0.

    The start age is NOT a constant — it steps up by birth year:
      * born 1950 or earlier -> 72  (pre-SECURE 2.0)
      * born 1951-1959       -> 73
      * born 1960 or later    -> 75

    Hardcoding 73 would understate the start age by two years for anyone born
    in 1960+, starting forced withdrawals early in exactly the projection this
    feature exists to provide. Returns ``None`` when ``dob`` is unknown.
    """
    if dob is None:
        return None
    if dob.year <= 1950:
        return 72
    if dob.year <= 1959:
        return 73
    return 75


def full_retirement_age_months(dob: date | None) -> int | None:
    """Social Security full retirement age (FRA), in total months, per the SSA
    schedule that steps up by birth year:

      * born 1937 or earlier -> 65y
      * 1938-1942            -> 65y + 2 months per year past 1937
      * 1943-1954            -> 66y
      * 1955-1959            -> 66y + 2 months per year past 1954
      * 1960 or later         -> 67y

    Returned in months so the exact milestone date can be computed. None when
    ``dob`` is unknown.
    """
    if dob is None:
        return None
    y = dob.year
    if y <= 1937:
        return 65 * 12
    if y <= 1942:
        return 65 * 12 + (y - 1937) * 2
    if y <= 1954:
        return 66 * 12
    if y <= 1959:
        return 66 * 12 + (y - 1954) * 2
    return 67 * 12


def _add_months(d: date, months: int) -> date:
    """``d`` shifted forward by ``months``, clamping the day to the target month
    length (so adding to a Jan 31 doesn't overflow February)."""
    total = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _months_label(months: int) -> str:
    """Render a month count as an age label, e.g. 794 -> '66y 2m', 780 -> '66'."""
    years, rem = divmod(months, 12)
    return f"{years}y {rem}m" if rem else str(years)


@dataclass(frozen=True)
class Milestone:
    key: str
    label: str
    age_label: str
    date: date
    year: int


def milestones(
    dob: date | None, retirement_target_age: int | None = None
) -> list[Milestone] | None:
    """Age-triggered financial milestone dates for a member, ordered by date.

    Covers the early-withdrawal threshold (59½), the Social Security claiming
    window (earliest 62, full retirement age), Medicare (65), and the SECURE 2.0
    RMD start age. When ``retirement_target_age`` is set, a "Target retirement"
    milestone is added at that age. Returns ``None`` when ``dob`` is unknown so
    callers can prompt for a birthdate instead of rendering an empty timeline.
    """
    if dob is None:
        return None

    rmd_age = rmd_start_age(dob)
    fra_months = full_retirement_age_months(dob)
    assert rmd_age is not None and fra_months is not None  # dob is not None here

    specs: list[tuple[str, str, int]] = [
        ("early_withdrawal", "Penalty-free retirement withdrawals", 59 * 12 + 6),
        ("social_security_earliest", "Social Security earliest claim", 62 * 12),
        ("medicare", "Medicare eligibility", 65 * 12),
        ("full_retirement_age", "Social Security full retirement age", fra_months),
        ("rmd", "Required minimum distributions begin", rmd_age * 12),
    ]
    if retirement_target_age is not None:
        specs.append(("retirement_target", "Target retirement", retirement_target_age * 12))

    result = [
        Milestone(
            key=key,
            label=label,
            age_label=_months_label(months),
            date=_add_months(dob, months),
            year=_add_months(dob, months).year,
        )
        for key, label, months in specs
    ]
    result.sort(key=lambda m: m.date)
    return result
