# Phase 4 — FIRE Modeling and Debt Payoff

Implements FIRE scenario modeling with auto-detection from transaction data,
the formalized income stream schema, debt payoff projections (avalanche and
snowball), and the FIRE and debt analysis UI pages.

---

## Deliverables

- [ ] `FireInputDetector` service (auto-detects income streams from transactions)
- [ ] `FireProjector` service (year-by-year compound projection)
- [ ] FIRE scenario CRUD with income stream editor
- [ ] FIRE projection endpoint
- [ ] Debt payoff projector (avalanche + snowball)
- [ ] Debt payoff endpoint
- [ ] Frontend: FIRE scenario editor, FIRE projection chart, debt payoff page

---

## Income stream schema (Amendment 3)

The `fire_scenarios.additional_income_streams` JSONB field stores a list
of `IncomeStream` objects. Validated by Pydantic before every write.

```python
from enum import Enum
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class IncomeStreamType(str, Enum):
    salary          = "salary"
    rental          = "rental"
    consulting      = "consulting"
    pension         = "pension"
    social_security = "social_security"
    investment      = "investment"
    other           = "other"

class IncomeStream(BaseModel):
    id: str                               # client-generated UUID string
    label: str = Field(max_length=100)
    type: IncomeStreamType
    amount_annual: Decimal = Field(ge=0)
    growth_rate_annual: float = Field(ge=-1.0, le=1.0)  # e.g. 0.03
    start_year: int = Field(ge=1900, le=2200)
    end_year: int | None = None           # None = indefinite
    is_pre_retirement: bool = True
    notes: str | None = None
    real_estate_property_id: str | None = None
    auto_detected: bool = False
    detected_at: datetime | None = None

    class Config:
        json_encoders = {Decimal: str}
```

---

## `FireInputDetector`

```python
# backend/app/services/fire_detector.py

class FireDetectionResult(BaseModel):
    income_streams: list[IncomeStream]
    gross_income_annual: Decimal
    total_expenses_annual: Decimal
    savings_rate: float
    current_portfolio_value: Decimal
    current_net_worth: Decimal
    detected_at: datetime
    trailing_months_used: int
    months_with_data: int
    warnings: list[str]

class FireInputDetector:
    PORTFOLIO_ACCOUNT_TYPES = {
        "investment_brokerage", "retirement_401k", "retirement_403b",
        "retirement_ira", "retirement_roth_ira", "pension", "hsa",
    }

    async def detect(
        self,
        ctx: VisibilityContext,
        trailing_months: int = 12,
    ) -> FireDetectionResult:
        cutoff = date.today() - relativedelta(months=trailing_months)

        # 1. Income: group transactions by category, is_income=TRUE
        income_by_category = await self._sum_by_category(
            ctx, is_income=True, since=cutoff
        )

        # 2. Expenses: sum of all non-income, non-transfer transactions
        total_expenses = await self._sum_expenses(ctx, since=cutoff)

        # 3. Months with data (may be < trailing_months for newer accounts)
        months_with_data = await self._count_months_with_data(ctx, since=cutoff)

        # 4. Annualize (scale from actual months to 12)
        scale = 12 / max(months_with_data, 1)

        # 5. Build income streams (one per income category with transactions)
        income_streams = []
        gross_income_annual = Decimal(0)
        for cat_id, cat_name, cat_type, amount in income_by_category:
            annual = amount * Decimal(str(scale))
            gross_income_annual += annual
            income_streams.append(IncomeStream(
                id=str(uuid4()),
                label=cat_name,
                type=_map_category_to_stream_type(cat_name),
                amount_annual=annual.quantize(Decimal("0.01")),
                growth_rate_annual=0.03,        # conservative default
                start_year=date.today().year,
                end_year=None,
                is_pre_retirement=True,
                auto_detected=True,
                detected_at=datetime.now(timezone.utc),
            ))

        # 6. Current portfolio value (latest snapshots for portfolio accounts)
        portfolio_value = await self._current_portfolio(ctx)

        expenses_annual = total_expenses * Decimal(str(scale))
        savings_rate = float(
            (gross_income_annual - expenses_annual) / gross_income_annual
        ) if gross_income_annual > 0 else 0.0

        warnings = []
        if months_with_data < 6:
            warnings.append(
                f"Only {months_with_data} months of transaction data available. "
                "Detected values may not reflect your typical financial picture."
            )

        return FireDetectionResult(
            income_streams=income_streams,
            gross_income_annual=gross_income_annual,
            total_expenses_annual=expenses_annual,
            savings_rate=savings_rate,
            current_portfolio_value=portfolio_value,
            current_net_worth=await self._net_worth(ctx),
            detected_at=datetime.now(timezone.utc),
            trailing_months_used=trailing_months,
            months_with_data=months_with_data,
            warnings=warnings,
        )
```

---

## `FireProjector`

```python
# backend/app/services/fire_projector.py

from dataclasses import dataclass
from decimal import Decimal

@dataclass
class YearProjection:
    year: int
    age: int | None           # primary member age if date_of_birth known
    portfolio: Decimal
    annual_income: Decimal    # from pre-retirement streams
    annual_spend: Decimal     # inflation-adjusted target spend
    annual_savings: Decimal   # income - spend
    supplemental_income: Decimal  # post-retirement streams active this year
    effective_withdrawal: Decimal # annual_spend - supplemental_income
    fire_number: Decimal
    is_fire_year: bool

def project(scenario: FireScenario, from_year: int, member_dob: date | None) -> list[YearProjection]:
    portfolio = scenario.detected_portfolio_value or Decimal(0)
    fire_number = scenario.target_annual_spend / scenario.safe_withdrawal_rate
    projections = []

    for year in range(from_year, from_year + 75):  # cap at 75 years
        age = (year - member_dob.year) if member_dob else None

        # Pre-retirement income streams active this year
        annual_income = sum(
            _stream_amount(s, year)
            for s in scenario.income_streams
            if s.is_pre_retirement and _stream_active(s, year)
        )

        # Inflation-adjusted spend target
        annual_spend = scenario.target_annual_spend * (
            (1 + scenario.expected_inflation_rate) ** (year - from_year)
        )

        annual_savings = annual_income - annual_spend

        # Grow portfolio and add savings
        portfolio = portfolio * (1 + scenario.expected_annual_return) + annual_savings

        # Post-retirement supplemental income streams (reduce withdrawal need)
        supplemental = sum(
            _stream_amount(s, year)
            for s in scenario.income_streams
            if not s.is_pre_retirement and _stream_active(s, year)
        )

        effective_withdrawal = max(annual_spend - supplemental, Decimal(0))
        is_fire_year = portfolio >= fire_number

        projections.append(YearProjection(
            year=year, age=age, portfolio=portfolio,
            annual_income=annual_income, annual_spend=annual_spend,
            annual_savings=annual_savings, supplemental_income=supplemental,
            effective_withdrawal=effective_withdrawal,
            fire_number=fire_number, is_fire_year=is_fire_year,
        ))

        if is_fire_year:
            break

    return projections


def _stream_amount(stream: IncomeStream, year: int) -> Decimal:
    years_elapsed = year - stream.start_year
    return stream.amount_annual * Decimal(
        str((1 + stream.growth_rate_annual) ** years_elapsed)
    )

def _stream_active(stream: IncomeStream, year: int) -> bool:
    return stream.start_year <= year and (
        stream.end_year is None or stream.end_year >= year
    )
```

---

## Debt payoff projector

Implements avalanche (highest interest rate first) and snowball
(lowest balance first) strategies.

```python
# backend/app/services/debt_projector.py

@dataclass
class DebtPayoffMonth:
    month: int                # months from today (1-based)
    date: date
    total_remaining: Decimal
    per_debt: dict[UUID, Decimal]  # debt_id → remaining balance

@dataclass
class DebtPayoffPlan:
    strategy: str             # 'avalanche' | 'snowball'
    months_to_payoff: int
    total_interest_paid: Decimal
    payoff_date: date
    monthly_series: list[DebtPayoffMonth]
    payoff_order: list[str]   # debt nicknames in payoff order

def project_payoff(
    debts: list[DebtWithAccount],
    extra_monthly_payment: Decimal,
    strategy: str,
) -> DebtPayoffPlan:
    """
    Standard debt payoff projection.
    All debts make their minimum payment each month.
    Extra payment applied to the target debt per strategy:
      avalanche → highest interest_rate first
      snowball  → lowest current_balance first
    When a debt is paid off, its minimum payment is rolled into extra.
    """
    ...
```

---

## API endpoints — Phase 4

### FIRE scenarios

```
GET    /api/v1/fire-scenarios
POST   /api/v1/fire-scenarios
  body: {name, target_annual_spend, safe_withdrawal_rate?,
         expected_annual_return?, expected_inflation_rate?,
         target_retirement_age?, additional_income_streams?}
GET    /api/v1/fire-scenarios/{id}
PATCH  /api/v1/fire-scenarios/{id}
DELETE /api/v1/fire-scenarios/{id}

POST   /api/v1/fire-scenarios/{id}/detect
  Runs FireInputDetector and merges results into the scenario.
  Does not overwrite manually-entered streams.
  Returns updated scenario with detection warnings.

GET    /api/v1/fire-scenarios/{id}/projection
  query: from_year? (default: current year)
  Returns list[YearProjection] + summary:
    { fire_year, fire_age, years_to_fire, fire_number, headline }
  headline: "FIRE in 14 years at age 52"
```

### Debt payoff

```
GET  /api/v1/reports/debt-payoff
  query: extra_monthly_payment (default 0), strategy (avalanche | snowball)
  Returns DebtPayoffPlan for both strategies side by side for comparison.
```

---

## Frontend — Phase 4 pages

### `/fire`

FIRE scenario list with "New scenario" button. Each scenario card shows
headline metric ("FIRE in 14 years") and target spend.

### `/fire/{id}`

Two-panel layout:

**Left — Scenario editor:**
- Target annual spend (with tooltip: "Enter your estimated annual retirement
  spending in today's dollars")
- Safe withdrawal rate (default 4%, with "What is this?" tooltip)
- Expected return / inflation rate sliders
- Target retirement age (optional)
- Income streams section:
  - List of streams with type badge, label, annual amount, years active
  - "Auto-detect from transactions" button (calls `/detect`; shows spinner)
  - Auto-detected streams have a "Detected" badge with date
  - "Add stream" opens modal form
  - Consulting/other streams show warning: "Variable income — review estimate"
  - Rental streams show "Link to property" dropdown
- Detection warnings surfaced as yellow alert banners

**Right — Projection chart:**
- Line chart: portfolio value over time + FIRE number horizontal line
- X-axis: years (or age if DOB known)
- Annotation at FIRE crossing year: "FIRE at age 52 (2039)"
- Below chart: year-by-year table (year, age, portfolio, income, savings)

### `/debt`

Debt list with current balance, interest rate, minimum payment, payoff date.
"Extra monthly payment" input field updates both projections in real time.
Side-by-side comparison: Avalanche vs Snowball.
- Total interest saved
- Months to payoff
- Payoff order
- Balance over time chart (stacked area by debt)

---

## Acceptance criteria

1. `POST /api/v1/fire-scenarios/{id}/detect` on a household with 12+ months
   of transaction data returns income streams matching the transaction
   category breakdown.
2. Detection with < 6 months of data returns a warning in `warnings[]`.
3. Running detection twice does not duplicate income streams (existing
   auto-detected streams are updated, not duplicated).
4. Manually-set `amount_annual` on a stream is preserved when detection
   is re-run.
5. Projection with a consulting stream ending in 2 years correctly removes
   that stream's income after `end_year`.
6. Post-retirement Social Security stream correctly reduces
   `effective_withdrawal` (not `annual_savings`) after the FIRE year.
7. Avalanche strategy pays the highest-rate debt first; snowball pays the
   lowest-balance debt first.
8. When a debt reaches $0, its minimum payment is correctly rolled into
   extra payment for the next target debt.
9. FIRE projection chart renders with correct FIRE year annotation.
10. Debt payoff comparison shows avalanche paying less total interest than
    snowball (always true when rates differ).
