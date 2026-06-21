# Phase 9 — Wealth Dashboard

Full UI redesign across seven screens. Replaces the initial per-section
layouts with a unified design system built on CSS custom-property tokens,
a persistent sidebar, and consistent visual patterns across all tabs.

## Status

**Complete** — v0.9.1.0 — 2026-06-20

---

## Deliverables

- [x] Design token system — complete migration to CSS custom properties
- [x] Sidebar shell — persistent navigation with SVG icons, dark/light/system mode toggle
- [x] Overview tab — 4-KPI row, net-worth trend chart (YTD/1Y/All), allocation donut, top-spending categories, budget alert row
- [x] Accounts tab — split-panel ledger with category groups (Assets/Liabilities) left, detail panel right
- [x] Investments tab — brokerage accounts with per-account balance history line charts
- [x] Retirement tab — tax-treatment groupings with KPI row (total, tax-deferred, tax-free)
- [x] Real estate tab — property cards with equity bar, YoY delta, latest valuation date
- [x] Cash flow tab — 4-KPI row (income, expenses, net, savings rate), 12-month bar chart, spending breakdown
- [x] EditAccountModal — inline edit for nickname, institution name, notes
- [x] Range toggle routing — TanStack Router `useNavigate()`, validated `range` search param

---

## Design system

Tokens defined in the root CSS and consumed across all pages:

| Token | Purpose |
|---|---|
| `--bg` | Page background |
| `--card` | Card surface |
| `--bd`, `--bd2` | Border colors (default / emphasis) |
| `--text`, `--text2`, `--text3` | Text hierarchy |
| `--muted`, `--faint`, `--label` | Secondary text |
| `--up` | Positive delta (green) |
| `--liab` | Liability/negative (red-orange) |
| `--grad`, `--pgrad` | Asset / liability gradient backgrounds |
| `--accent-bd`, `--pbd` | Gradient card borders |
| `--toggle-on-bg/text` | Primary action button |
| `--row-active` | Selected row background |
| `--track` | Progress bar track |

---

## Notable fixes

- **compactCurrency negative values** — compact formatter now prepends sign and uses `Math.abs`.
- **Retirement prefetch scope** — snapshot prefetch filtered to retirement account types only.
- **notes max-length validation** — `AccountCreate.notes` and `AccountUpdate.notes` enforce `max_length=2000`.
- **Range param allowlist** — validated against `["ytd", "1y", "all"]`; invalid values fall back to `"ytd"`.
- **Account number field** — masked last-4 display in the accounts ledger detail panel.

---

## Acceptance criteria

1. All seven tabs render without errors when accounts, transactions, and properties exist.
2. Dark mode toggle persists across navigation (localStorage or system preference).
3. Net-worth chart range toggle (YTD/1Y/All) updates the URL search param and re-fetches.
4. EditAccountModal saves nickname, institution name, and notes; account list reflects changes without full reload.
5. Allocation donut segments sum to 100% of total assets.
6. Budget alert row shows over-budget categories from the current month.
