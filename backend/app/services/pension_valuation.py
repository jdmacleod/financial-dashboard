"""Present-value model for defined-benefit pensions.

The legacy model valued a pension as a simple perpetuity (``annual / 0.04``).
That overstated the value of a pension for members far from retirement (it
ignored the years until benefits begin) and ignored both COLA growth and the
survivor benefit. This module centralises a single, more defensible model that:

  * discounts deferred benefits back over the years until eligibility,
  * models COLA growth via a *growing* annuity,
  * values a finite life annuity rather than an infinite perpetuity,
  * adds the survivor's continued (reduced) benefit.

Historical accuracy comes from ``PensionEstimateHistory``: each net-worth point
is valued from the estimate in effect at that date (``pension_value_at``), so
editing today's estimate does not rewrite past chart points. The valuation
itself is duck-typed — it reads the same four fields from either a
``PensionAccount`` or a ``PensionEstimateHistory`` row.

It is still an approximation — a fully accurate model would use member age and
mortality tables. The discount rate is intentionally the same constant the rest
of the reporting layer uses so pension accounts value identically everywhere.
"""

from datetime import date
from decimal import Decimal
from typing import Protocol

from app.db.models.pension import PensionAccount, PensionEstimateHistory


class _PVInputs(Protocol):
    """The fields the present-value formula reads. Both PensionAccount and
    PensionEstimateHistory satisfy this."""

    monthly_benefit_estimate: Decimal | None
    cola_adjustment_rate: Decimal
    survivor_benefit_percent: Decimal | None
    eligibility_date: date | None


# Real discount rate applied to projected benefits.
PENSION_DISCOUNT_RATE = Decimal("0.04")
# Life-annuity horizon (years of benefit payments) from the date payments begin.
# A finite annuity is more accurate than the old perpetuity, which assumed
# benefits were paid forever and overstated the present value.
DEFAULT_PAYOUT_YEARS = 25
# Years a survivor continues drawing the reduced benefit after the primary
# payout horizon ends.
SURVIVOR_PAYOUT_YEARS = 10
_DAYS_PER_YEAR = Decimal("365.25")


def _growing_annuity_pv(annual: Decimal, rate: Decimal, growth: Decimal, years: int) -> Decimal:
    """PV, at the moment payments begin, of an annuity that pays ``annual`` in
    the first year, grows at ``growth`` per year, discounted at ``rate`` per
    year, for ``years`` payments."""
    if years <= 0 or annual <= 0:
        return Decimal("0")
    if rate == growth:
        # Degenerate case: each discounted payment is equal.
        return annual * Decimal(years) / (1 + rate)
    ratio = (1 + growth) / (1 + rate)
    return annual * (1 - ratio**years) / (rate - growth)


def pension_present_value(pension: _PVInputs | None, as_of: date) -> Decimal:
    """Present value of a set of pension PV inputs as of ``as_of``.

    Accepts a ``PensionAccount`` or a ``PensionEstimateHistory`` row (both expose
    the same four fields). Returns ``Decimal("0")`` when absent or when no
    benefit estimate is recorded.
    """
    if pension is None or not pension.monthly_benefit_estimate:
        return Decimal("0")

    annual = pension.monthly_benefit_estimate * 12
    rate = PENSION_DISCOUNT_RATE
    growth = pension.cola_adjustment_rate or Decimal("0")

    pv_at_start = _growing_annuity_pv(annual, rate, growth, DEFAULT_PAYOUT_YEARS)

    if pension.survivor_benefit_percent:
        survivor_annual = annual * pension.survivor_benefit_percent
        survivor_pv = _growing_annuity_pv(survivor_annual, rate, growth, SURVIVOR_PAYOUT_YEARS)
        # The survivor's benefit begins only after the primary payout horizon,
        # so discount it back over those years.
        pv_at_start += survivor_pv / (1 + rate) ** DEFAULT_PAYOUT_YEARS

    # Discount the whole stream back to today for benefits that have not yet
    # begun. Benefits already in payment (no future eligibility date) are not
    # discounted further.
    if pension.eligibility_date and pension.eligibility_date > as_of:
        years_to_start = Decimal((pension.eligibility_date - as_of).days) / _DAYS_PER_YEAR
        return pv_at_start / (1 + rate) ** years_to_start
    return pv_at_start


def effective_estimate(
    history: list[PensionEstimateHistory], as_of: date
) -> PensionEstimateHistory | None:
    """The estimate snapshot in effect at ``as_of``: the latest row whose
    ``effective_date`` is on or before ``as_of``. For dates before the first
    recorded estimate, the earliest row applies (the inception estimate covers
    all prior history). ``history`` must be sorted oldest-first. Returns ``None``
    only when ``history`` is empty.
    """
    if not history:
        return None
    chosen = history[0]
    for row in history:
        if row.effective_date <= as_of:
            chosen = row
        else:
            break
    return chosen


def pension_value_at(
    pension: PensionAccount | None,
    history: list[PensionEstimateHistory],
    as_of: date,
) -> Decimal:
    """Present value of a pension at ``as_of``, valued from the estimate in
    effect at that date. Falls back to the pension's current fields when no
    history exists (e.g. pensions created before the history table)."""
    estimate = effective_estimate(history, as_of)
    return pension_present_value(estimate if estimate is not None else pension, as_of)
