from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

_MAX_MONTHS = 600  # cap at 50 years


@dataclass
class DebtRecord:
    id: uuid.UUID
    nickname: str
    current_balance: Decimal
    interest_rate: Decimal  # e.g. 0.065 for 6.5%
    minimum_payment: Decimal


@dataclass
class DebtPayoffMonth:
    month: int
    date: date
    total_remaining: Decimal
    per_debt: dict[uuid.UUID, Decimal] = field(default_factory=dict)


@dataclass
class DebtPayoffPlan:
    strategy: str
    months_to_payoff: int
    total_interest_paid: Decimal
    payoff_date: date
    monthly_series: list[DebtPayoffMonth]
    payoff_order: list[str]


def project_payoff(
    debts: list[DebtRecord],
    extra_monthly_payment: Decimal,
    strategy: str,  # 'avalanche' | 'snowball'
) -> DebtPayoffPlan:
    """Standard debt payoff projection.

    Each month:
    1. Apply monthly interest: balance += balance * (rate / 12)
    2. Pay minimum on each debt (or balance if < minimum)
    3. Apply extra payment to target debt
       (avalanche: highest rate; snowball: lowest balance)
    4. When a debt reaches 0, roll its minimum into extra_monthly_payment
    """
    if not debts:
        return DebtPayoffPlan(
            strategy=strategy,
            months_to_payoff=0,
            total_interest_paid=Decimal(0),
            payoff_date=date.today(),
            monthly_series=[],
            payoff_order=[],
        )

    balances: dict[uuid.UUID, Decimal] = {d.id: d.current_balance for d in debts}
    debt_map: dict[uuid.UUID, DebtRecord] = {d.id: d for d in debts}
    active_ids: list[uuid.UUID] = [d.id for d in debts if d.current_balance > Decimal(0)]

    total_interest = Decimal(0)
    monthly_series: list[DebtPayoffMonth] = []
    payoff_order: list[str] = []
    available_extra = extra_monthly_payment
    start_date = date.today()

    for month in range(1, _MAX_MONTHS + 1):
        if not active_ids:
            break

        # Step 1: accrue interest
        for debt_id in active_ids:
            d = debt_map[debt_id]
            interest = balances[debt_id] * (d.interest_rate / Decimal(12))
            total_interest += interest
            balances[debt_id] += interest

        # Step 2: pay minimums
        for debt_id in active_ids:
            d = debt_map[debt_id]
            payment = min(balances[debt_id], d.minimum_payment)
            balances[debt_id] -= payment

        # Step 3: apply extra payment to target debt
        if active_ids and available_extra > Decimal(0):
            if strategy == "avalanche":
                target_id = max(active_ids, key=lambda did: debt_map[did].interest_rate)
            else:
                target_id = min(active_ids, key=lambda did: balances[did])

            extra_applied = min(balances[target_id], available_extra)
            balances[target_id] -= extra_applied

        # Clamp negatives
        for debt_id in list(active_ids):
            if balances[debt_id] < Decimal(0):
                balances[debt_id] = Decimal(0)

        # Record month
        month_date = start_date + relativedelta(months=month)
        per_debt = {debt_id: balances[debt_id] for debt_id in debt_map}
        total_remaining = sum((balances[debt_id] for debt_id in active_ids), Decimal(0))
        monthly_series.append(
            DebtPayoffMonth(
                month=month,
                date=month_date,
                total_remaining=total_remaining,
                per_debt=per_debt,
            )
        )

        # Step 4: retire paid-off debts and roll minimums
        newly_paid_off = [did for did in active_ids if balances[did] <= Decimal("0.01")]
        for debt_id in newly_paid_off:
            active_ids.remove(debt_id)
            payoff_order.append(debt_map[debt_id].nickname)
            available_extra += debt_map[debt_id].minimum_payment

    last_month = monthly_series[-1] if monthly_series else None
    payoff_date = last_month.date if last_month else start_date

    return DebtPayoffPlan(
        strategy=strategy,
        months_to_payoff=len(monthly_series),
        total_interest_paid=total_interest,
        payoff_date=payoff_date,
        monthly_series=monthly_series,
        payoff_order=payoff_order,
    )
