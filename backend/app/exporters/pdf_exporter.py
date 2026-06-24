from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.debt import Debt
from app.db.models.export_job import ExportJob
from app.db.models.fire import FireScenario
from app.db.models.household import Household
from app.db.models.insurance_policy import InsurancePolicy
from app.db.models.real_estate import RealEstateProperty
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.repositories.real_estate import RealEstateRepository
from app.services.report import ReportService

_INSURANCE_TYPE_LABELS: dict[str, str] = {
    "term_life": "Term Life",
    "permanent_life": "Permanent Life",
    "umbrella_liability": "Umbrella Liability",
    "disability": "Disability",
    "long_term_care": "Long-Term Care",
    "scheduled_specialty": "Scheduled / Specialty",
    "homeowners": "Homeowners",
    "renters": "Renters",
}

try:
    from importlib.metadata import version as _pkg_version

    _APP_VERSION = _pkg_version("hearthledger-backend")
except Exception:
    _APP_VERSION = "0.7.0"

# Account types whose display balance comes from SUM(transaction.amount) when
# no AccountSnapshot exists (matches the routing in account.py).
_TXN_DISPLAY_TYPES: frozenset[str] = frozenset(
    {
        "checking",
        "savings",
        "credit_card",
        "mortgage",
        "auto_loan",
        "personal_loan",
        "student_loan",
        "other_asset",
        "other_liability",
        "heloc",
    }
)


def _fmt_usd(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _fmt_date(d: date) -> str:
    return d.strftime("%B %d, %Y")


def _mask_account_number(account_number_enc: bytes | None, anonymized: bool) -> str:
    if account_number_enc is None:
        return "N/A"
    try:
        full = decrypt(account_number_enc)
    except Exception:
        return "••••••••"
    if anonymized:
        last4 = full[-4:] if len(full) >= 4 else full
        return f"••••{last4}"
    return full


def _mask_institution(institution_name_enc: bytes | None, anonymized: bool) -> str:
    if institution_name_enc is None:
        return "N/A"
    try:
        return decrypt(institution_name_enc)
    except Exception:
        return "N/A"


def _mask_policy_number(policy_number: str | None, anonymized: bool) -> str:
    if policy_number is None:
        return "N/A"
    if anonymized:
        last4 = policy_number[-4:] if len(policy_number) >= 4 else policy_number
        return f"••••{last4}"
    return policy_number


async def _fetch_insurance_policies(
    session: AsyncSession, household_id: uuid.UUID
) -> list[InsurancePolicy]:
    result = await session.execute(
        select(InsurancePolicy)
        .where(InsurancePolicy.household_id == household_id)
        .order_by(InsurancePolicy.policy_type)
    )
    return list(result.scalars().all())


async def _fetch_accounts(session: AsyncSession, ctx: VisibilityContext) -> list[Account]:
    repo = AccountRepository(session)
    return await repo.get_visible(ctx, is_active=True)


async def _fetch_categories(
    session: AsyncSession, household_id: uuid.UUID
) -> dict[uuid.UUID, Category]:
    result = await session.execute(select(Category).where(Category.household_id == household_id))
    return {c.id: c for c in result.scalars().all()}


async def _fetch_transactions(
    session: AsyncSession,
    account_ids: list[uuid.UUID],
    from_date: date,
    to_date: date,
) -> list[Transaction]:
    if not account_ids:
        return []
    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.account_id.in_(account_ids),
            Transaction.transaction_date >= from_date,
            Transaction.transaction_date <= to_date,
        )
        .order_by(Transaction.transaction_date.desc())
        .limit(5000)
    )
    return list(result.scalars().all())


async def _latest_balance(
    session: AsyncSession, account_id: uuid.UUID, as_of: date
) -> Decimal | None:
    result = await session.execute(
        select(AccountSnapshot.balance)
        .where(
            AccountSnapshot.account_id == account_id,
            AccountSnapshot.snapshot_date <= as_of,
        )
        .order_by(AccountSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _fetch_debts(session: AsyncSession, account_ids: list[uuid.UUID]) -> list[Debt]:
    if not account_ids:
        return []
    result = await session.execute(select(Debt).where(Debt.account_id.in_(account_ids)))
    return list(result.scalars().all())


async def _fetch_properties(
    session: AsyncSession, account_ids: list[uuid.UUID]
) -> list[RealEstateProperty]:
    if not account_ids:
        return []
    result = await session.execute(
        select(RealEstateProperty).where(RealEstateProperty.account_id.in_(account_ids))
    )
    return list(result.scalars().all())


async def _fetch_fire_scenarios(
    session: AsyncSession, household_id: uuid.UUID
) -> list[FireScenario]:
    result = await session.execute(
        select(FireScenario).where(FireScenario.household_id == household_id)
    )
    return list(result.scalars().all())


async def _fetch_spending_by_category(
    session: AsyncSession,
    account_ids: list[uuid.UUID],
    cat_map: dict[uuid.UUID, Category],
    from_date: date,
    to_date: date,
) -> list[tuple[str, Decimal]]:
    if not account_ids:
        return []
    result = await session.execute(
        select(Transaction.category_id, func.sum(Transaction.amount))
        .where(
            Transaction.account_id.in_(account_ids),
            Transaction.is_transfer.is_(False),
            Transaction.amount < 0,
            Transaction.transaction_date >= from_date,
            Transaction.transaction_date <= to_date,
        )
        .group_by(Transaction.category_id)
        .order_by(func.sum(Transaction.amount).asc())
    )
    rows = result.all()
    items: list[tuple[str, Decimal]] = []
    for cat_id, total in rows:
        name = cat_map[cat_id].name if cat_id in cat_map else "Uncategorized"
        items.append((name, abs(Decimal(str(total)))))
    return sorted(items, key=lambda x: x[1], reverse=True)


def _html_header(title: str, generated_at: str, household_name: str = "HearthLedger") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<style>
  @page {{
    @bottom-center {{
      content: "Page " counter(page) " of " counter(pages) " — HearthLedger v{_APP_VERSION}";
      font-size: 9px;
      color: #999;
      border-top: 1px solid #e0e0e0;
      padding-top: 4px;
      width: 100%;
      text-align: center;
    }}
  }}
  body {{ font-family: Arial, sans-serif; font-size: 12px; color: #1a1a1a; margin: 40px; }}
  h1 {{ font-size: 24px; color: #1e3a5f; border-bottom: 2px solid #1e3a5f; padding-bottom: 8px; }}
  h2 {{ font-size: 16px; color: #1e3a5f; margin-top: 28px;
        border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
  h3 {{ font-size: 13px; color: #333; margin-top: 16px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th {{ background: #1e3a5f; color: white; padding: 6px 10px; text-align: left; font-size: 11px; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #e8e8e8; }}
  tr:nth-child(even) {{ background: #f7f9fc; }}
  .cover {{ margin-bottom: 40px; }}
  .cover p {{ color: #555; margin: 4px 0; }}
  .cover .report-type {{ font-size: 14px; color: #666; font-weight: normal; margin: 6px 0 2px 0; }}
  .kv {{ display: flex; gap: 40px; margin: 16px 0; }}
  .kv-item {{ background: #f0f4f9; padding: 12px 20px; border-radius: 6px; }}
  .kv-item .label {{ font-size: 10px; color: #666; text-transform: uppercase; }}
  .kv-item .value {{ font-size: 18px; font-weight: bold; color: #1e3a5f; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px;
            background: #e8f0fe; color: #1e3a5f; }}
  .warn {{ color: #b45309; }}
  .page-break {{ page-break-after: always; }}
</style>
</head>
<body>
<div class="cover">
  <h1>{household_name}</h1>
  <p class="report-type">HearthLedger — {title}</p>
  <p>Generated: {generated_at}</p>
</div>
"""


def _html_footer() -> str:
    return "</body></html>"


async def generate(job: ExportJob, session: AsyncSession, output_dir: str) -> str:
    """Generate a PDF export file. Returns the filename (not full path)."""
    from_date = date.fromisoformat(job.parameters["from_date"])
    to_date = date.fromisoformat(job.parameters["to_date"])
    anonymized = job.anonymized
    role = job.parameters.get("role", "primary")
    member_id_str = job.parameters.get("member_id")
    member_id = uuid.UUID(member_id_str) if member_id_str else None

    ctx = VisibilityContext(
        user_id=job.generated_by,
        member_id=member_id,
        role=role,
        household_id=job.household_id,
    )

    generated_at = datetime.now(UTC)
    ts = generated_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    suffix = "summary" if anonymized else "executor"
    filename = f"hearthledger_pdf_{suffix}_{ts}.pdf"
    output_path = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    title = "Summary Report" if anonymized else "Executor Report"
    generated_at_str = generated_at.strftime("%Y-%m-%d %H:%M UTC")

    # Fetch data
    accounts = await _fetch_accounts(session, ctx)
    account_ids = [a.id for a in accounts]
    cat_map = await _fetch_categories(session, job.household_id)

    # Household name for report header
    _hh_row = await session.execute(select(Household).where(Household.id == job.household_id))
    _hh = _hh_row.scalar_one_or_none()
    household_name = _hh.name if _hh else "HearthLedger"

    today = date.today()

    # Per-account display balances: snapshot-first, then transaction SUM, then RE valuation.
    # This matches the routing in AccountService.list_accounts().
    _snap_result = await session.execute(
        select(AccountSnapshot)
        .where(AccountSnapshot.account_id.in_(account_ids))
        .distinct(AccountSnapshot.account_id)
        .order_by(AccountSnapshot.account_id, AccountSnapshot.snapshot_date.desc())
    )
    account_balances: dict[uuid.UUID, Decimal] = {
        s.account_id: s.balance for s in _snap_result.scalars().all()
    }

    _needs_txn = [
        a.id
        for a in accounts
        if a.account_type in _TXN_DISPLAY_TYPES and a.id not in account_balances
    ]
    if _needs_txn:
        _txn_sums = await session.execute(
            select(Transaction.account_id, func.sum(Transaction.amount).label("total"))
            .where(Transaction.account_id.in_(_needs_txn))
            .group_by(Transaction.account_id)
        )
        for _row in _txn_sums.all():
            account_balances[_row.account_id] = Decimal(str(_row.total))

    _re_no_snap = [
        a.id for a in accounts if a.account_type == "real_estate" and a.id not in account_balances
    ]
    if _re_no_snap:
        _re_repo = RealEstateRepository(session)
        _re_props = await _re_repo.list_for_accounts(_re_no_snap)
        if _re_props:
            _acc_to_prop = {p.account_id: p.id for p in _re_props}
            _val_map = await _re_repo.batch_latest_valuations_as_of(
                [p.id for p in _re_props], today
            )
            for _acc_id, _prop_id in _acc_to_prop.items():
                account_balances[_acc_id] = _val_map.get(_prop_id, Decimal("0"))

    for _acc in accounts:
        account_balances.setdefault(_acc.id, Decimal("0"))

    # Net worth from ReportService — identical to the dashboard (respects
    # include_in_net_worth and pension present-value discount).
    _nw_point = await ReportService(session).current_net_worth(ctx, today)
    total_assets = _nw_point.total_assets
    total_liabilities = _nw_point.total_liabilities
    net_worth = _nw_point.net_worth

    # Spending by category
    spending = await _fetch_spending_by_category(session, account_ids, cat_map, from_date, to_date)

    # Transactions (income/expense summary)
    transactions = await _fetch_transactions(session, account_ids, from_date, to_date)
    total_income = sum(
        (
            t.amount
            for t in transactions
            if not t.is_transfer and t.category_id in cat_map and cat_map[t.category_id].is_income
        ),
        Decimal("0"),
    )
    total_expenses = sum(
        (-t.amount for t in transactions if not t.is_transfer and t.amount < 0),
        Decimal("0"),
    )

    # Build HTML
    html_parts: list[str] = [_html_header(title, generated_at_str, household_name)]

    # --- Net worth snapshot ---
    html_parts.append("<h2>Net Worth Snapshot</h2>")
    _ta = _fmt_usd(total_assets)
    _tl = _fmt_usd(total_liabilities)
    _nw = _fmt_usd(net_worth)
    html_parts.append(f"""
<div class="kv">
  <div class="kv-item">
    <div class="label">Total Assets</div><div class="value">{_ta}</div>
  </div>
  <div class="kv-item">
    <div class="label">Total Liabilities</div><div class="value">{_tl}</div>
  </div>
  <div class="kv-item">
    <div class="label">Net Worth</div><div class="value">{_nw}</div>
  </div>
</div>
<p>Report period: {_fmt_date(from_date)} to {_fmt_date(to_date)}</p>
""")

    # --- Cash flow summary ---
    html_parts.append("<h2>Cash Flow Summary</h2>")
    html_parts.append(f"""
<table>
  <tr><th>Metric</th><th>Amount</th></tr>
  <tr><td>Total Income</td><td>{_fmt_usd(total_income)}</td></tr>
  <tr><td>Total Expenses</td><td>{_fmt_usd(total_expenses)}</td></tr>
  <tr><td>Net Cash Flow</td><td>{_fmt_usd(total_income - total_expenses)}</td></tr>
</table>
""")

    # --- Spending by category ---
    if spending:
        html_parts.append("<h2>Spending by Category</h2>")
        html_parts.append("<table><tr><th>Category</th><th>Amount</th></tr>")
        for name, amount in spending[:20]:
            html_parts.append(f"<tr><td>{name}</td><td>{_fmt_usd(amount)}</td></tr>")
        html_parts.append("</table>")

    # --- Investment/retirement summary ---
    inv_types = {
        "investment_brokerage",
        "retirement_401k",
        "retirement_403b",
        "retirement_ira",
        "retirement_roth_ira",
        "pension",
        "hsa",
    }
    inv_accounts = [a for a in accounts if a.account_type in inv_types]
    if inv_accounts:
        html_parts.append("<h2>Investment &amp; Retirement Summary</h2>")
        html_parts.append("<table><tr><th>Account</th><th>Type</th><th>Balance</th></tr>")
        for acct in inv_accounts:
            bal = account_balances.get(acct.id, Decimal("0"))
            inst = _mask_institution(acct.institution_name_enc, anonymized)
            label = f"{acct.nickname} ({inst})"
            html_parts.append(
                f"<tr><td>{label}</td><td>{acct.account_type}</td><td>{_fmt_usd(bal)}</td></tr>"
            )
        html_parts.append("</table>")

    # ---- Executor-only sections ----
    if not anonymized:
        html_parts.append('<div class="page-break"></div>')

        # --- Full account directory ---
        html_parts.append("<h2>Account Directory</h2>")
        html_parts.append(
            "<table><tr><th>Nickname</th><th>Type</th><th>Institution</th>"
            "<th>Account Number</th><th>Balance</th></tr>"
        )
        for acct in accounts:
            bal = account_balances.get(acct.id, Decimal("0"))
            inst = _mask_institution(acct.institution_name_enc, anonymized)
            acct_num = _mask_account_number(acct.account_number_enc, anonymized)
            html_parts.append(
                f"<tr><td>{acct.nickname}</td><td>{acct.account_type}</td>"
                f"<td>{inst}</td><td>{acct_num}</td><td>{_fmt_usd(bal)}</td></tr>"
            )
        html_parts.append("</table>")

        # --- Real estate holdings ---
        properties = await _fetch_properties(session, account_ids)
        if properties:
            html_parts.append("<h2>Real Estate Holdings</h2>")
            html_parts.append(
                "<table><tr><th>Address</th><th>Purchase Date</th>"
                "<th>Purchase Price</th><th>Est. Value</th></tr>"
            )
            for prop in properties:
                try:
                    addr = decrypt(prop.address_enc)
                except Exception:
                    addr = "[encrypted]"
                pp = _fmt_usd(prop.purchase_price) if prop.purchase_price else "N/A"
                pdate = str(prop.purchase_date) if prop.purchase_date else "N/A"
                ev = "N/A"
                html_parts.append(
                    f"<tr><td>{addr}</td><td>{pdate}</td><td>{pp}</td><td>{ev}</td></tr>"
                )
            html_parts.append("</table>")

        # --- Debt schedule ---
        debts = await _fetch_debts(session, account_ids)
        if debts:
            html_parts.append("<h2>Debt Schedule</h2>")
            html_parts.append(
                "<table><tr><th>Account</th><th>Balance</th>"
                "<th>Interest Rate</th><th>Min Payment</th></tr>"
            )
            acct_map = {a.id: a for a in accounts}
            for debt in debts:
                debt_acct = acct_map.get(debt.account_id)
                nick = debt_acct.nickname if debt_acct else str(debt.account_id)
                rate = f"{debt.interest_rate * 100:.2f}%" if debt.interest_rate else "N/A"
                minp = _fmt_usd(debt.minimum_payment) if debt.minimum_payment else "N/A"
                html_parts.append(
                    f"<tr><td>{nick}</td><td>{_fmt_usd(debt.current_balance)}</td>"
                    f"<td>{rate}</td><td>{minp}</td></tr>"
                )
            html_parts.append("</table>")

        # --- FIRE scenario snapshot ---
        scenarios = await _fetch_fire_scenarios(session, job.household_id)
        if scenarios:
            html_parts.append("<h2>FIRE Scenario Snapshot</h2>")
            html_parts.append(
                "<table><tr><th>Scenario</th><th>Target Spend</th>"
                "<th>SWR</th><th>FIRE Year</th></tr>"
            )
            for sc in scenarios:
                swr = f"{float(sc.safe_withdrawal_rate) * 100:.1f}%"
                fire_year = (
                    str(sc.fire_year) if hasattr(sc, "fire_year") and sc.fire_year else "TBD"
                )
                html_parts.append(
                    f"<tr><td>{sc.name}</td>"
                    f"<td>{_fmt_usd(sc.target_annual_spend)}</td>"
                    f"<td>{swr}</td><td>{fire_year}</td></tr>"
                )
            html_parts.append("</table>")

        # --- Insurance policies ---
        policies = await _fetch_insurance_policies(session, job.household_id)
        if policies:
            # Build property_id → address map for the "Covered property" column
            _prop_addr: dict[uuid.UUID, str] = {}
            for _p in properties:
                try:
                    _prop_addr[_p.id] = decrypt(_p.address_enc)
                except Exception:
                    _prop_addr[_p.id] = "[encrypted]"

            html_parts.append("<h2>Insurance Policies</h2>")
            html_parts.append(
                "<table><tr><th>Type</th><th>Carrier</th><th>Policy Number</th>"
                "<th>Coverage</th><th>Premium</th><th>Covered Property</th></tr>"
            )
            _cadence_labels = {"monthly": "/mo", "quarterly": "/qtr", "annual": "/yr"}
            for pol in policies:
                type_label = _INSURANCE_TYPE_LABELS.get(pol.policy_type, pol.policy_type)
                carrier = pol.carrier or "N/A"
                pnum = _mask_policy_number(pol.policy_number, anonymized)
                coverage = _fmt_usd(pol.coverage_amount)
                cadence = _cadence_labels.get(pol.premium_cadence, "")
                premium = f"{_fmt_usd(pol.premium_amount)}{cadence}"
                prop_label = (
                    _prop_addr.get(pol.insured_real_estate_id, "—")
                    if pol.insured_real_estate_id
                    else "—"
                )
                html_parts.append(
                    f"<tr><td>{type_label}</td><td>{carrier}</td><td>{pnum}</td>"
                    f"<td>{coverage}</td><td>{premium}</td><td>{prop_label}</td></tr>"
                )
            html_parts.append("</table>")

        # --- Audit summary page ---
        html_parts.append('<div class="page-break"></div>')
        html_parts.append("<h2>Audit Summary</h2>")
        html_parts.append(f"""
<p>This executor report was generated on {generated_at_str} and contains full account details
for {household_name}.</p>
<p>Report covers transactions from {_fmt_date(from_date)} through {_fmt_date(to_date)}.</p>
<p>Total transactions in period: {len(transactions)}</p>
""")

    html_parts.append(_html_footer())
    html_str = "\n".join(html_parts)

    # WeasyPrint is synchronous — run in executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _write_pdf_sync, html_str, output_path)

    return filename


def _write_pdf_sync(html_str: str, output_path: str) -> None:
    from weasyprint import HTML  # type: ignore[import-untyped,unused-ignore]

    HTML(string=html_str).write_pdf(output_path)
