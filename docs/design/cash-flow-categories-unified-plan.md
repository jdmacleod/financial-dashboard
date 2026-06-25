# Cash Flow Categories — Unified Design Plan

**Date:** 2026-06-23
**Status:** Implemented — all tasks (T1–T15) shipped via PR #38 (backend: slug, colors, retirement lookup) and PR #39 (frontend: tree view, shared components, report colors, drill-down, tests)
**Reviewed by:** /plan-design-review

## Problem Statement

The Cash Flow tab's "Top spending categories" panel shows real, correctly-rolled-up
data but users can't understand *why* a category appears, *what* is in it, or how their
transaction categorization decisions connect to it. The system has all the right data —
the UI just doesn't expose it.

Three root causes:

1. **Flat transaction picker:** The category dropdown in transaction forms shows all
   170 categories in a flat `<select>` with no grouping. Users can't distinguish parents
   from children and may pick inconsistently (sometimes "Food & Dining", sometimes
   "Groceries").

2. **Colors are wired to nothing:** Each category has a `color_hex` field that is never
   used. Cash Flow bars render uniform `var(--liab)` red; Spending Report pie uses
   random position-based colors that change order every render.

3. **No path from Cash Flow to detail:** The Cash Flow category bars are non-interactive
   `<div>` elements. The drill-down logic already exists in ReportSpending.tsx — it just
   isn't connected.

---

## Architecture (Current — Do Not Change)

The backend is correct. Do not change it.

- `spending_by_category` rolls up child transaction amounts into parent totals ✓
- `has_children` flag on `SpendingCategoryItem` signals drillability ✓
- `parent_category_id` on `Category` model correctly establishes 2-level hierarchy ✓
- `reportsApi.spendingByCategory(from, to, parentCategoryId?)` supports drill-down ✓
- `CategoryResponse.color_hex` and `CategoryResponse.parent_category_id` already returned ✓

---

## Design Decisions

### D1 — Category picker format
**Grouped `<optgroup>` with parents selectable**

Replace the flat `<select>` with HTML `<optgroup>` grouping. Parents appear as
group headers AND as selectable options at the top of their group (labeled as
"Food & Dining — general" to distinguish from children). Children appear indented
below their parent.

Applies to: `TransactionForm.tsx`, `CategoryBadge` inline select in `Transactions.tsx`,
bulk categorize select in `Transactions.tsx`.

Implementation pattern:
```tsx
// Build grouped structure from categories prop
const parents = categories.filter(c => !c.parent_category_id && !c.is_income)
const children = categories.filter(c => c.parent_category_id && !c.is_income)
const childrenByParent = groupBy(children, c => c.parent_category_id)

// Render
<select>
  <option value="">Uncategorized</option>
  {incomeCategories.length > 0 && (
    <optgroup label="── Income ──">
      {incomeCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
    </optgroup>
  )}
  {parents.map(parent => (
    <optgroup key={parent.id} label={parent.name}>
      <option value={parent.id}>{parent.name} — general</option>
      {childrenByParent[parent.id]?.map(c =>
        <option key={c.id} value={c.id}>{c.name}</option>
      )}
    </optgroup>
  ))}
</select>
```

### D2 — Cash Flow panel footer
**"View full breakdown →" link**

Below the 8 category bars, add a small footer link that navigates to the Spending
Report with the same date range pre-filled:

```
/reports/spending?from=2026-01-01&to=2026-06-23
```

The link text: `"View full breakdown →"` in `var(--faint)` color, 11px, right-aligned.

### D3 — Cash Flow category bars: clickable drill-down
**Click bar → Spending Report pre-filtered**

`CategoryBar` becomes a `<button>` element. Clicking navigates to:
```
/reports/spending?category=<category_id>&from=<from>&to=<to>
```

The Spending Report's existing `drillCategory` state accepts a `category_id` via URL
search param. Add a `useEffect` in `ReportSpending.tsx` to initialize `drillCategory`
from the URL param on mount.

Visual affordance on the bar:
- `cursor: pointer`
- Hover: subtle background shift (`rgba(255,255,255,0.04)`)
- Hover: show a `›` chevron on the right end (replaces the percentage on hover)
- Focus ring: `outline: 2px solid var(--accent)` on focus-visible

### D4 — Category colors
**Use `category.color_hex` directly**

The `spending_by_category` API returns `category_id`. The categories are loaded in
both `ReportCashFlow.tsx` (already queries the spending API) and `ReportSpending.tsx`.

In `ReportCashFlow.tsx`: Build a `categoryColorMap: Map<string, string>` from the
categories query, then pass `color={categoryColorMap.get(c.category_id) ?? '#888888'}`
to each `CategoryBar`. The bar fill changes from `var(--liab)` to the category color.

In `ReportSpending.tsx`: Replace `CHART_COLORS[i % CHART_COLORS.length]` with
`category.color_hex` (or fallback). The pie chart slices now have stable colors.

Note: `ReportCashFlow.tsx` must also load the categories list (it currently only loads
the spending report). Add a second `useQuery` for `categoriesApi.list`.

### D5 — Shared component library
**Create Card, DataRow, SectionHeader components**

Before rebuilding the Categories page, create shared components that work in both
the CSS-var system (Cash Flow) and Tailwind system (Categories):

```
frontend/src/components/ui/data-card.tsx    — Card with var(--card) bg
frontend/src/components/ui/data-row.tsx     — Row with label + value
frontend/src/components/ui/section-header.tsx — Uppercase label with optional action
```

These components use CSS custom properties so they work in both systems. The
Categories page is rewritten with these components as the first consumer.

### D6 — Mobile responsive + keyboard accessibility
**Stack Cash Flow grid on mobile; CategoryBar as `<button>`**

The Cash Flow 2-column grid (`gridTemplateColumns: "1fr 1.5fr"`) needs a breakpoint:
```css
@media (max-width: 768px) {
  grid-template-columns: 1fr;  /* single column */
}
```

Implement in React inline style with a `useWindowWidth` hook or use Tailwind's
`md:grid-cols-2` class.

All `CategoryBar` components that are interactive must be `<button>` elements with:
- `role` inherited from `<button>`
- `aria-label="View {name} spending detail"`
- `focus-visible:outline: 2px solid var(--accent)`

### D7 — Category seed colors
**Assign meaningful colors to parent categories in `shared_categories.py`**

Update the `_DEFS` list to include a color hex for each top-level parent:

```python
# (slug, display_name, parent_slug | None, is_income, color_hex)
("housing", "Housing", None, False, "#3b82f6"),        # blue
("utilities", "Utilities", None, False, "#06b6d4"),     # cyan
("transportation", "Transportation", None, False, "#f97316"),  # orange
("food_dining", "Food & Dining", None, False, "#22c55e"),      # green
("healthcare", "Healthcare", None, False, "#a855f7"),          # purple
("education", "Education & Childcare", None, False, "#0ea5e9"), # sky
("personal", "Personal & Shopping", None, False, "#ec4899"),   # pink
("entertainment", "Entertainment & Leisure", None, False, "#14b8a6"), # teal
("property_expenses", "Rental Property Expenses", None, False, "#84cc16"), # lime
("business_expenses", "Business Expenses", None, False, "#64748b"),   # slate
("financial_services", "Financial Services", None, False, "#6366f1"), # indigo
("insurance", "Insurance", None, False, "#f59e0b"),            # amber
("interest_expense", "Interest Expense", None, False, "#ef4444"), # red
("eldercare", "Eldercare & Family Support", None, False, "#8b5cf6"), # violet
("transfers", "Transfers", None, False, "#94a3b8"),            # gray
# Income parents
("income", "Income", None, True, "#22c55e"),
("business_income", "Business Income", None, True, "#10b981"),
("investment_income", "Investment Income", None, True, "#3b82f6"),
("rental_income", "Rental Income", None, True, "#f59e0b"),
("other_income", "Other Income", None, True, "#94a3b8"),
```

Child categories inherit parent color in the UI (look up parent's color_hex when the
child has no color of its own). The `seed_categories` function passes `color_hex` to
the `Category` model.

### D8 — Category slug column
**Add `slug` to Category model for stable backend lookup**

The `RETIREMENT_INCOME_CATEGORIES` map in `report.py` currently matches by category
name (`"Social Security"`, `"Pension Income"`, `"Required Minimum Distribution"`). If a
user renames a system category, the retirement income breakdown silently breaks.

Fix: add a nullable `slug` column to `categories` table. System categories get their
slug from the seed data's slug key. The `report.py` lookup uses slug instead of name.

```python
# Alembic migration (new):
op.add_column('categories', sa.Column('slug', sa.String(100), nullable=True))
op.create_index('ix_categories_household_slug', 'categories',
                ['household_id', 'slug'], unique=False)

# Category model addition:
slug: Mapped[str | None] = mapped_column(String(100), nullable=True)

# report.py — change lookup:
RETIREMENT_INCOME_SLUGS = {
    "social_security_income": "social_security",
    "pension_income": "pension",
    "rmd_distribution": "rmd",
}
# In cash_flow():
bucket = category and RETIREMENT_INCOME_SLUGS.get(category.slug)
```

The seed data's `seed_categories` function must also write `slug=slug_key` when
creating categories.

---

## Categories Page Redesign

The `Categories.tsx` page needs a tree view that shows the hierarchy:

```
Housing                          [color dot] [#3b82f6]
  ├ HOA Fees
  ├ Home Insurance
  ├ Home Maintenance & Repairs
  └ ...

Food & Dining                    [color dot] [#22c55e]
  ├ Groceries
  ├ Restaurants & Takeout
  └ ...
```

Each parent row is collapsible (expanded by default). The color dot next to the parent
is editable inline (color picker). System categories show a "System" badge and allow
color editing but not rename/delete.

The "Add category" form appears at the parent level with a parent selector.

---

## Spending Report — URL-param initialization

Add to `ReportSpending.tsx`:

```tsx
const search = useSearch({ from: '/reports/spending' })

// Initialize drill state from URL
const [drillCategory, setDrillCategory] = useState<string | null>(
  search.category ?? null
)
// Initialize range from URL
const [preset, setPreset] = useState<Preset>(
  search.range ?? "this_month"
)
```

When Cash Flow navigates with `?category=<id>&from=<date>&to=<date>`, the Spending
Report opens already drilled into that category with the matching date range.

---

## Design Decisions (Engineering Review additions)

### D2-eng — Cash Flow footer link date params
**Pass only `?category=<id>` from Cash Flow bars, no date params**

The Cash Flow date range uses YTD/1Y/All presets; the Spending Report uses
this_month/3m/6m/12m presets. The date models don't map cleanly. T7 and T8
pass only `?category=<category_id>` — no `?from=` or `?to=`. The Spending
Report opens with its default preset. A follow-on task (TODOS.md) will add
a "Custom" date mode to Spending Report for full coherence.

### D3-eng — validateSearch on reportsSpendingRoute
**Add validateSearch to reportsSpendingRoute in router.tsx**

TanStack Router requires `validateSearch` on any route that reads URL params
via `useSearch`. The child route's result is merged (not overriding) the parent's
result. Add:
```ts
validateSearch: (search: Record<string, unknown>) => ({
  category: typeof search.category === "string" ? search.category : undefined,
})
```

### D4-eng — Slug index uniqueness
**Partial unique index: `UNIQUE WHERE slug IS NOT NULL`**

The slug column is nullable (user-created categories have no slug). A full unique
constraint would prevent two households from both having `NULL` slugs. Use:
```python
op.create_index(
    "ix_categories_household_slug",
    "categories",
    ["household_id", "slug"],
    unique=True,
    postgresql_where=sa.text("slug IS NOT NULL"),
)
```

### D5-eng — Color rollout to existing households
**Bundle color data migration into the Alembic migration 0013**

The Alembic migration adds the slug column AND updates existing system parent
categories' color_hex values in a single `op.execute()` UPDATE statement per
category (keyed by slug after slugs are set). No separate migration needed.

### D6-eng — groupBy utility
**Use inline Array.prototype.reduce at each of 3 call sites**

`tsconfig.app.json` targets ES2023; `Object.groupBy` is ES2024. No `groupBy`
utility exists in `frontend/src/lib/utils.ts`. Use inline `reduce` at the 3
call sites (TransactionForm, Transactions bulk select, ReportCashFlow categories
optgroup builder).

### D7-eng — Migration downgrade()
**T2 migration must include downgrade(): drop index, drop column, reset colors**

```python
def downgrade() -> None:
    op.execute("UPDATE categories SET color_hex = '#888888' WHERE is_system = TRUE AND parent_category_id IS NULL")
    op.drop_index("ix_categories_household_slug", table_name="categories")
    op.drop_column("categories", "slug")
```

### D11-eng — System category color editing
**Relax is_system guard in CategoryService.update() for color_hex-only updates**

`CategoryService.update()` currently rejects all mutations to system categories.
Relax the guard: if the only field being changed is `color_hex`, allow the update
even when `is_system=True`. All other fields remain locked for system categories.
Add `backend/app/services/categories.py` to T4's file list.

---

## Implementation Tasks

Synthesized from design review (D1-D8) and engineering review (D2-eng through D11-eng,
outside voice). Each task references the finding that surfaced it.

### Backend

- [x] **T1 (P1, human: ~30min / CC: ~5min)** — `shared_categories.py` — Add color_hex to parent categories AND update seed_categories() function body
  - Surfaced by: D7 (design) + outside voice — _DEFS 5-tuple only works if function body also destructures `color_hex` and passes `color_hex=color_hex` to `Category()`
  - Files: `backend/scripts/seed_households/shared_categories.py`
  - Verify: Re-seed a household; categories endpoint returns non-gray color_hex for all parent categories

- [x] **T2 (P1, human: ~2.5h / CC: ~25min)** — `Category model + migration 0013` — Add slug column, color data migration, slug-based retirement lookup, relax CategoryService color guard
  - Surfaced by: D8 (design), D4-eng/D5-eng/D7-eng/D11-eng (eng review)
  - Files: `backend/app/db/models/category.py`, `backend/alembic/versions/0013_category_slug_colors.py`, `backend/app/services/report.py`, `backend/app/services/categories.py`
  - Notes: Slug index is partial unique (`WHERE slug IS NOT NULL`). Migration includes data UPDATE for parent category colors. `downgrade()` must drop index, drop column, reset colors to `#888888`.
  - Verify: Rename "Social Security" system category → cash flow retirement breakdown still correct. Run `alembic downgrade -1` → slug column gone, colors reset.

### Frontend — Shared Components

- [x] **T3 (P1, human: ~2h / CC: ~15min)** — `shared component library` — DataCard, DataRow, SectionHeader using CSS custom properties
  - Surfaced by: D5 (design) — prerequisite for T4
  - Files: `frontend/src/components/ui/data-card.tsx`, `frontend/src/components/ui/data-row.tsx`, `frontend/src/components/ui/section-header.tsx`
  - Verify: Import in Categories.tsx without visual regression

### Frontend — Categories Page

- [x] **T4 (P1, human: ~3h / CC: ~20min)** — `Categories.tsx` — Tree view with collapsible parents, editable color dots, system badge, parent selector in Add form
  - Surfaced by: Pass 1 (design) + D11-eng — flat list has no hierarchy; system color now editable
  - Files: `frontend/src/pages/Categories.tsx`
  - Verify: Parent categories show collapsible children; color dot opens color picker; system badge present; system categories show color picker but not rename/delete

### Frontend — Transaction Form

- [x] **T5 (P1, human: ~2h / CC: ~10min)** — `TransactionForm.tsx` + bulk select — Grouped optgroup picker
  - Surfaced by: D1 (design), D6-eng — 170-item flat select; use inline `reduce` not `Object.groupBy`
  - Files: `frontend/src/components/app/TransactionForm.tsx`, `frontend/src/pages/Transactions.tsx`
  - Notes: Use `Array.prototype.reduce` (not `Object.groupBy` — ES2024 only, target is ES2023) to build `childrenByParent` at all 3 picker call sites.
  - Verify: Select shows optgroup headers; parents selectable as "Foo — general"; children indented; no TypeScript errors

### Frontend — Cash Flow Report

- [x] **T6 (P1, human: ~1h / CC: ~10min)** — `ReportCashFlow.tsx` — Add categoriesApi.list query, build categoryColorMap, pass color to CategoryBar
  - Surfaced by: D4 (design), D10-eng — bars render uniform `var(--liab)` red
  - Files: `frontend/src/pages/ReportCashFlow.tsx`
  - Notes: Add `staleTime: 5 * 60 * 1000` to categories query. Build `useMemo` colorMap: `Map<string, string>`.
  - Verify: Each CategoryBar renders its category's color_hex; API called once per 5 minutes

- [x] **T7 (P1, human: ~1h / CC: ~10min)** — `ReportCashFlow.tsx CategoryBar` — Convert to `<button>`, click navigates to Spending Report
  - Surfaced by: D3 (design), D2-eng + null gap (outside voice) — bars non-interactive; null category_id unguarded
  - Files: `frontend/src/pages/ReportCashFlow.tsx`
  - Notes: Navigate to `/reports/spending?category=<id>` (no date params per D2-eng). When `c.category_id === null` (uncategorized bucket), do NOT set onClick — bar is non-clickable. Add `aria-label="View {name} spending detail"` and `focus-visible` outline.
  - Verify: Click "Housing" bar → /reports/spending?category=<housing-id>. Click uncategorized bar → no navigation. Focus ring visible on Tab.

- [x] **T8 (P1, human: ~30min / CC: ~5min)** — `ReportCashFlow.tsx` — "View full breakdown →" footer link
  - Surfaced by: D2 (design), D2-eng — panel is a dead end; passes no date params
  - Files: `frontend/src/pages/ReportCashFlow.tsx`
  - Notes: Link navigates to `/reports/spending` only (no `?from=` or `?to=`). Style: `var(--faint)`, 11px, right-aligned.
  - Verify: Link appears below category bars; navigates to Spending Report without date params

### Frontend — Spending Report

- [x] **T9 (P1, human: ~1h / CC: ~10min)** — `ReportSpending.tsx + router.tsx` — Add validateSearch, initialize drillCategory from URL
  - Surfaced by: D3 (design), D3-eng — no validateSearch on reportsSpendingRoute; URL params type-unsafe
  - Files: `frontend/src/pages/ReportSpending.tsx`, `frontend/src/router.tsx`
  - Notes: `validateSearch: (search) => ({ category: typeof search.category === "string" ? search.category : undefined })`. In ReportSpending, initialize `drillCategory` state from `useSearch({ from: '/reports/spending' }).category ?? null`.
  - Verify: Navigate to `/reports/spending?category=<housing-id>` → Spending Report opens drilled into Housing

- [x] **T10 (P1, human: ~1h / CC: ~10min)** — `ReportSpending.tsx` — Replace position-based CHART_COLORS with category color_hex
  - Surfaced by: D4 (design), D10-eng — `CHART_COLORS[i]` changes on re-render; SpendingCategoryItem has no color_hex
  - Files: `frontend/src/pages/ReportSpending.tsx`
  - Notes: Add `useQuery(categoriesApi.list)` with `staleTime: 5 * 60 * 1000`. Build colorMap from categories. Replace `CHART_COLORS[i % CHART_COLORS.length]` with `colorMap.get(c.category_id) ?? '#888888'`.
  - Verify: "Housing" pie slice is always blue regardless of sort order or date range

- [x] **T11 (P2, human: ~1h / CC: ~10min)** — `ReportCashFlow.tsx` — Mobile responsive grid + keyboard a11y
  - Surfaced by: D6 (design) — 2-column grid collapses to horizontal scroll at 375px
  - Files: `frontend/src/pages/ReportCashFlow.tsx`
  - Verify: At 375px, category bars and period table stack vertically; Tab cycles through clickable bars

### Tests

- [x] **T12 (P1, human: ~30min / CC: ~5min)** — `ReportCashFlow.test.tsx` — Add categories API mock (regression guard)
  - Surfaced by: test regression analysis — T6 adds `categoriesApi.list()` call; all 14 existing tests break without a mock
  - Files: `frontend/src/pages/__tests__/ReportCashFlow.test.tsx`
  - Notes: Add before existing mocks: `vi.mock("@/api/categories", () => ({ categoriesApi: { list: vi.fn(() => Promise.resolve([])) } }))`
  - Verify: All 14 existing tests still pass after T6 lands

- [x] **T13 (P1, human: ~1.5h / CC: ~10min)** — Create `ReportSpending.test.tsx`
  - Surfaced by: D8-eng — no test file exists; T9/T10 add significant new behavior with no tests
  - Files: `frontend/src/pages/__tests__/ReportSpending.test.tsx`
  - Cover: URL param `?category=<id>` initializes drillCategory; pie slices use category color_hex (not position-based colors); "← All categories" clears drill; empty state when no spending
  - Verify: vitest passes

- [x] **T14 (P1, human: ~2h / CC: ~15min)** — Create `Categories.test.tsx`
  - Surfaced by: D8-eng — no test file exists; T4 is a full page redesign with no tests
  - Files: `frontend/src/pages/__tests__/Categories.test.tsx`
  - Cover: Tree view renders parent/child hierarchy; clicking parent row expands/collapses children; system badge present on system categories; color picker opens on dot click; Add form shows parent selector; system category rename/delete inputs absent
  - Verify: vitest passes

- [x] **T15 (P1, human: ~1h / CC: ~10min)** — Backend unit test for RETIREMENT_INCOME_SLUGS
  - Surfaced by: D9-eng — T2 changes name-based lookup to slug-based; no test verifies the mapping works
  - Files: `backend/tests/unit/test_service_category.py`
  - Cover: Categories with slugs `social_security_income`, `pension_income`, `rmd_distribution` map to correct retirement income buckets; category with unrecognized slug maps to None; category with null slug maps to None
  - Verify: pytest passes

---

## NOT in Scope

- Multi-level hierarchy (3+ levels) — 2-level model is sufficient
- Category import/export — separate feature
- Budget rollup to parent categories — budgets stay at specific category level
- Auto-categorization / ML rules — separate feature
- Spending report trend line overlay — future feature
- Date range harmonization between Cash Flow and Spending Report — deferred to TODOS.md
- CSS-var migration for Transactions.tsx and Budgets.tsx — deferred to TODOS.md
- color_hex on `SpendingCategoryItem` backend schema — not needed; frontend categories query is the solution

## What Already Exists (Reuse)

- `spending_by_category` backend with correct parent rollup and `has_children` flag ✓
- `reportsApi.spendingByCategory(from, to, parentCategoryId?)` drill-down ✓
- `color_hex` and `parent_category_id` on `CategoryResponse` ✓
- `drillCategory` state in `ReportSpending.tsx` — only needs URL initialization ✓
- `categoriesApi.list()` already called in `Transactions.tsx` — same call T5, T6, T10 use ✓
- `CategoryService.update()` backend — needs only color-only guard relaxed ✓
- `appLayoutRoute.validateSearch({ range? })` — child route adds only `category?` ✓

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests | 1 | CLEAR (PLAN) | 12 decisions, 15 tasks, 4 new tasks added |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAR (PLAN) | score 4/10 → 8/10, 9 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**ENG REVIEW VERDICT (2026-06-23): CLEAR — ready for implementation**

All 12 decisions resolved. Key findings incorporated:

| ID | Finding | Resolution |
|----|---------|------------|
| D2-eng | Cash Flow bar click + footer: date param mismatch | Pass only `?category=<id>`, no date params |
| D3-eng | `reportsSpendingRoute` missing `validateSearch` | Add to router.tsx for `{ category?: string }` |
| D4-eng | Slug uniqueness: NULL rows would collide | Partial unique index `WHERE slug IS NOT NULL` |
| D5-eng | Existing households won't get category colors | Bundle UPDATE data migration into Alembic 0013 |
| D6-eng | `Object.groupBy` unavailable (ES2024 target) | Inline `reduce` at all 3 call sites |
| D7-eng | T2 migration missing `downgrade()` | Add: drop index, drop column, reset colors |
| D8-eng | No test files for ReportSpending or Categories | T13 + T14 added |
| D9-eng | No test for RETIREMENT_INCOME_SLUGS lookup | T15 added |
| D10-eng | `SpendingCategoryItem` has no `color_hex` | Add `categoriesApi.list` query in T10 |
| D11-eng | `CategoryService.update()` blocks system color edits | Relax guard for color_hex-only updates |
| T1-clarify | seed_categories() body not updated for 5-tuple | Updated T1 to include function body change |
| D12-eng | Date range mismatch is deferred | TODO added to TODOS.md |

**New tasks added by eng review:** T12 (categories mock regression), T13 (ReportSpending tests), T14 (Categories tests), T15 (backend slug test). Total: 15 tasks.

**Failure mode caught:** T7 null category_id click — `c.category_id === null` for uncategorized bucket must not trigger navigation. Added null guard to T7.

NO UNRESOLVED DECISIONS — IMPLEMENTATION MAY BEGIN
