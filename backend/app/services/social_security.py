"""Social Security claiming-age benefit adjustment.

Given a member's Primary Insurance Amount (PIA — the monthly benefit payable at
Full Retirement Age) and date of birth, this computes the benefit actually payable
when claiming at a different age: reduced for claiming before FRA, increased by
delayed-retirement credits for claiming after FRA (up to age 70).

Rules (SSA, for anyone born 1943 or later — i.e. everyone planning today):
  - Early: benefit is reduced 5/9 of 1% per month for the first 36 months before
    FRA, then 5/12 of 1% per month beyond 36. (FRA 67 claimed at 62 -> 70% of PIA.)
  - Delayed: 2/3 of 1% per month (8%/year) of delayed-retirement credit, FRA to 70.
    (FRA 67 claimed at 70 -> 124% of PIA.)

Claiming is bounded to ages 62-70. PIA itself (the FRA benefit estimate) is a user
input — this engine adjusts it; it does not compute earnings histories.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.social_security import SocialSecurityClaimingOption, SocialSecurityComparison
from app.services.age import full_retirement_age_months

_CENTS = Decimal("0.01")
EARLIEST_CLAIM_AGE = 62
LATEST_CLAIM_AGE = 70

# Per-month adjustment fractions, expressed as Decimals.
_EARLY_FIRST_36 = Decimal("5") / Decimal("900")  # 5/9 of 1% per month
_EARLY_BEYOND_36 = Decimal("5") / Decimal("1200")  # 5/12 of 1% per month
_DELAYED_PER_MONTH = Decimal("2") / Decimal("300")  # 2/3 of 1% per month (8%/yr)


def benefit_adjustment_factor(fra_months: int, claiming_age_months: int) -> Decimal:
    """Multiplier applied to the PIA for claiming at `claiming_age_months`.

    1.0 at FRA, < 1 before, > 1 after (capped at age 70).
    """
    months_diff = claiming_age_months - fra_months
    if months_diff == 0:
        return Decimal("1")
    if months_diff < 0:
        early = -months_diff
        first = min(early, 36)
        beyond = max(early - 36, 0)
        reduction = first * _EARLY_FIRST_36 + beyond * _EARLY_BEYOND_36
        return Decimal("1") - reduction
    return Decimal("1") + months_diff * _DELAYED_PER_MONTH


def benefit_at_claiming_age(pia: Decimal, fra_months: int, claiming_age_months: int) -> Decimal:
    """Monthly benefit (rounded to cents) for claiming at the given age."""
    factor = benefit_adjustment_factor(fra_months, claiming_age_months)
    return (pia * factor).quantize(_CENTS, ROUND_HALF_UP)


def claiming_comparison(pia: Decimal, dob: date) -> SocialSecurityComparison:
    """Benefit at each whole claiming age 62-70 for a member with this PIA and DOB."""
    fra_months = full_retirement_age_months(dob)
    assert fra_months is not None  # dob is not None here
    options: list[SocialSecurityClaimingOption] = []
    for age in range(EARLIEST_CLAIM_AGE, LATEST_CLAIM_AGE + 1):
        claim_months = age * 12
        monthly = benefit_at_claiming_age(pia, fra_months, claim_months)
        factor = benefit_adjustment_factor(fra_months, claim_months)
        options.append(
            SocialSecurityClaimingOption(
                claiming_age=age,
                monthly_benefit=monthly,
                annual_benefit=(monthly * 12).quantize(_CENTS, ROUND_HALF_UP),
                pct_of_pia=float(factor * 100),
                is_fra=claim_months == fra_months,
            )
        )
    return SocialSecurityComparison(
        pia_monthly=pia.quantize(_CENTS, ROUND_HALF_UP),
        fra_months=fra_months,
        options=options,
    )
