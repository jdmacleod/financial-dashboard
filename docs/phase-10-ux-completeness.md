# Phase 10 — UX Completeness

Closes two open gaps from the Phase 8 Accounts/Assets restructure: context-aware
add buttons on the Accounts page, and VERSION file drift left over from the rapid
Phase 8→9→7 shipping sequence.

## Status

**Complete** — v0.9.3.0 — 2026-06-20

---

## Deliverables

- [x] Context-aware "+" buttons on Accounts page category groups
- [x] VERSION file sync (0.9.0.0 → 0.9.2.1, matching pyproject.toml/package.json)
- [x] TODOS.md: mark WeasyPrint skip and AddAccountModal F6 as completed

---

## Context-aware category add buttons (F6 completion)

### Problem

After Phase 8 restructured the Accounts page into a split-panel ledger with
five category groups (Banking & Cash, Retirement, Investments, Real estate,
Liabilities), the "+" button in every group opened the same generic
`AddAccountModal` scoped to `ACCOUNTS_PAGE_TYPES`. That list excludes
retirement, investment, and real estate types — so clicking "+" in the
Retirement group produced a modal with no retirement options. Users had to
know to navigate to `/reports/retirement` or `/assets` to add those accounts.

### Fix

Each category group's "+" button now triggers a context-aware handler:

| Category       | "+" action                                                                           |
| -------------- | ------------------------------------------------------------------------------------ |
| Banking & Cash | Opens `AddAccountModal` filtered to `BANKING_TYPES` (checking, savings, other_asset) |
| Liabilities    | Opens `AddAccountModal` filtered to `LIABILITY_TYPES`                                |
| Retirement     | Navigates to `/reports/retirement`                                                   |
| Investments    | Navigates to `/reports/investments`                                                  |
| Real estate    | Navigates to `/assets`                                                               |

The header "+ Add account" button on the Accounts page retains its existing
behavior (opens `AddAccountModal` with `ACCOUNTS_PAGE_TYPES` — all transaction
types).

### Implementation

`frontend/src/pages/Accounts.tsx`:

- Added `useNavigate` import from `@tanstack/react-router`.
- Added `AddFilter = "banking" | "liabilities" | null` type.
- Added `addFilter` state that tracks which subset the modal should show.
- Added `categoryAddHandlers: Record<CategoryName, () => void>` map with per-
  category logic.
- `CategoryGroup` now receives the per-category handler via `onAdd`.
- `AddAccountModal` receives `allowedTypes` derived from `addFilter`; `addFilter`
  resets to `null` on modal close.

---

## VERSION file drift fix

The `VERSION` file was last written when Phase 8 shipped at v0.9.0.0. The
subsequent version bumps to 0.9.1.0, 0.9.2.0, and 0.9.2.1 updated
`backend/pyproject.toml` and `frontend/package.json` but not `VERSION`.

This caused `gstack-version-bump classify` to report `DRIFT_UNEXPECTED` (package.json
ahead of VERSION), which would cause any future `/ship` run to stop at Step 12 and
require manual resolution.

Fix: `VERSION` updated to `0.9.2.1` to match the package files.

---

## Acceptance criteria

1. On the Accounts page, clicking "+" in the Banking & Cash group opens
   `AddAccountModal` showing only checking, savings, other_asset options.
2. On the Accounts page, clicking "+" in the Liabilities group opens
   `AddAccountModal` showing only credit_card, mortgage, loans, heloc,
   other_liability options.
3. On the Accounts page, clicking "+" in the Retirement group navigates to
   `/reports/retirement`.
4. On the Accounts page, clicking "+" in the Investments group navigates to
   `/reports/investments`.
5. On the Accounts page, clicking "+" in the Real estate group navigates to
   `/assets`.
6. The header "+ Add account" button on the Accounts page still opens
   `AddAccountModal` with the full `ACCOUNTS_PAGE_TYPES` list.
7. `cat VERSION` returns `0.9.2.1` (matches `backend/pyproject.toml` and
   `frontend/package.json`).
