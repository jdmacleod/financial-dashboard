# Phase 8 — Accounts & Assets Restructure

Splits the single Accounts page into purpose-specific views: a ledger-style
Accounts page for transaction-based accounts, a dedicated Assets page for real
estate, and a Retirement page for tax-advantaged accounts. Adds pension present
value to the net worth calculation.

## Status

**Complete** — v0.9.0.0 — 2026-06-19

---

## Deliverables

- [x] Assets page (`/assets`) — real estate property cards with equity bar and YoY delta
- [x] Retirement page (`/reports/retirement`) — tax-treatment groupings with KPI row
- [x] Pension PV in net worth — simplified perpetuity (monthly × 12 / 4%)
- [x] Real estate balances from property valuations (not snapshot table)
- [x] Snapshot batch query — single DISTINCT ON replaces N+1 fan-out
- [x] Accounts page narrowed to transaction-based types (`ACCOUNTS_PAGE_TYPES`)
- [x] Update value modal — snapshot entry for investment/HSA accounts
- [x] Household name as Dashboard title

---

## Backend changes (B1, B2)

### B1 — Real estate balance in `list_accounts`

`AccountService.list_accounts()` pre-fetches property valuations in a
two-step batch (account_ids → property_ids → valuations) and attaches
`current_balance` from the latest valuation, matching the `real_estate`
branch in `ReportService._asset_value_at()`.

### B2 — Pension PV in report service

`ReportService._asset_value_at()` now handles `pension` accounts by reading
the linked `PensionAccount.monthly_benefit_estimate` and computing:

```python
pv = monthly_benefit * 12 / Decimal("0.04")
```

Returns 0 if `monthly_benefit_estimate` is null (unvested or unknown benefit).
`NetWorthReport` includes a `pension_annotations` list populated by
`PensionRepository.get_with_members_for_accounts()` for FIRE display.

---

## Frontend changes (F1–F5)

- **F1** — Assets page: `PropertyCard` with equity bar, YoY delta, property type label, and Archive action.
- **F2** — Retirement page: `RetirementRow` with balance-change indicator; tax-treatment grouping (Tax-deferred / Tax-free / Guaranteed).
- **F3** — Accounts page: narrowed to `ACCOUNTS_PAGE_TYPES`; header `+ Add account` opens modal filtered to those types.
- **F4** — EditAccountModal: inline edit for nickname, institution name, notes.
- **F5** — Notes field exposed in `AccountResponse`; `account_number_last4` shown in ledger.

---

## Deferred (F6)

Per-category "+" buttons on the Accounts page all opened the same modal regardless
of category. Addressed in Phase 10: context-aware handlers navigate to the
appropriate dedicated page for Retirement/Investments/Real estate categories.

---

## Acceptance criteria

1. `GET /accounts` returns `current_balance` from the latest property valuation for `real_estate` accounts.
2. `GET /reports/net-worth` includes pension PV in the `retirement` breakdown.
3. The Assets page shows a property card for each real estate account with equity bar and YoY delta.
4. The Retirement page groups accounts by tax treatment.
5. The `+ Add account` button on the Accounts page does not offer real estate, pension, or investment types.
