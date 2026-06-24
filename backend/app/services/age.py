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
