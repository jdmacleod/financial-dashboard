# Handoff: Household Wealth Dashboard

## Overview
A multi-tab personal-wealth dashboard for a household tracking net worth across banking, investments, retirement (401(k)/IRA/pension), and real estate, plus liabilities and cash flow. It includes a multi-user identity system with roles/permissions, light & dark themes, and full create/edit/delete of account records that recompute every total live.

The household used for sample data is "The Whitfield Household" — a two-income family, ~$7.0M net worth, two properties, two 401(k)s, a pension, and a $1M taxable portfolio.

## About the Design Files
The files in this bundle are **design references created in HTML** — an interactive prototype showing the intended look and behavior. They are **not production code to copy**. The task is to **recreate this design in the target React frontend** using its existing component library, data layer, and patterns. The prototype is a single self-contained "Design Component" (`Wealth Dashboard.dc.html`) that runs via `support.js`; open it in a browser to click through every tab, the theme toggle, member switching, and the CRUD drawer/confirm flows.

> **Read `INTEGRATION_BRIEF.md` alongside this file.** It lists the open API/backend questions (data model, which aggregates are server- vs client-computed, auth/permissions, sync, CRUD semantics) as searchable `TODO:` markers. Those must be resolved before wiring to the real service. This README documents the **visual + interaction spec**; the brief documents the **integration unknowns**.

## Fidelity
**High-fidelity.** Final colors, typography, spacing, and interactions are all specified below. Recreate the UI faithfully using the codebase's existing libraries — but map the prototype's inline CSS-variable tokens onto the app's design system rather than copying inline styles. Charts are hand-rolled SVG in the prototype; rebuild them with the app's charting library.

## Layout shell
- **Full-viewport flex row.** Left **sidebar** fixed `214px`; main area flexes.
- **Sidebar** (`--sidebar` bg): brand mark + "Whitfield / Wealth ledger"; nav list (Overview, Accounts, Investments, Retirement, Real estate, Cash flow), each `10px 12px`, `8px` radius, active item gets `--nav-active-bg` + accent text; footer shows live net worth.
- **Main**: a **header** row (household name + "As of …· N accounts linked" on the left; YTD/1Y/All range toggle, a divider, and the **identity widget** on the right), then a `24px 30px 40px` padded content area that swaps by tab.
- Card grids use CSS grid with `12px` gaps; cards are `--card` bg, `1px solid --bd`, `10px` radius, `~17–22px` padding.

## Screens / Views

### 1. Overview
- **KPI row** — 5 cards (`grid repeat(5,1fr)`): Net worth (accent gradient card `--grad` + `--accent-bd` border), Assets, Liabilities (value in `--liab`), Liquid, Saved/mo (value in gold). Each: 10px uppercase label, 26px/600 value, 12px sub.
- **Trend + donut row** (`grid 1.7fr 1fr`): net-worth area+line chart (12 mo) with range caption; **asset-allocation donut** (138px, 15px ring) with center total + legend (Real estate/Retirement/Investments/Cash with %).
- **Bottom row** (`grid 1fr 1fr 1.1fr`): 6-mo cash-flow bars (income green `#46b888` / spend `#3a5d50`), Liabilities breakdown bars, Largest holdings list.

### 2. Accounts (primary CRUD surface)
- `grid 1.5fr 1fr`. **Left:** ledger card — accounts grouped by the 5 categories, each group header shows live subtotal + a **`+` add** affordance (role-gated). Rows: color dot, name, `institution · type`, balance, change. Click selects.
- **Right:** sticky **detail panel** (accent gradient card) — category, name, institution·type, large balance, change, sparkline, notes, "Last synced", and **Edit / Delete** buttons (role-gated).

### 3. Investments
- Header "Taxable portfolio · {total} · liquid & unrestricted". Performance chart, Holdings mix bars, Top positions table, and Unrealized gains / TLH / fee stat cards. (Positions are illustrative — see brief §4.)

### 4. Retirement
- Header "{total} tax-advantaged · {%} of net worth". KPI row (tax-advantaged assets, contributions YTD, pension income/yr, projected at 65). **Retirement accounts** list with a **tax tag** per row (Tax-deferred / Tax-free / Guaranteed) + edit affordance + `+ Add`. **By-tax-treatment** bucket bars. **Pension card** (blue `--pgrad`) treated as guaranteed income, not a balance. Projection chart to age 65.

### 5. Real estate
- Header "{value} · {mortgages} · {equity}" + `+ Add property`. **Property cards** (sc-for): photo placeholder, name/address + edit, value, change, equity bar with %, linked mortgage line. Bottom stats: total equity, rental income/yr, blended LTV.

### 6. Cash flow
- 4 KPI cards (income/mo, spending/mo, net saved/mo, savings rate), 12-month income-vs-spending bars, and a "Where it goes" category breakdown. (Static in prototype — see brief.)

### Identity widget + Members & roles
- Header pill: avatar (initials, role-tinted ring), name, "Role · access". Click → **dropdown**: current-user card, **Switch member** list, **Appearance** Dark/Light toggle, Profile & settings, Members & roles, Sign out.
- **Members & roles slide-over**: member list with live **role selects** (Owner / Co-owner / Advisor / Accountant / Viewer), "Invite a member", and a role-capability legend.

### CRUD drawer + delete confirm
- Right **slide-over drawer** for add/edit: Account name, Institution, Type, Category (select of the 5 groups), Current balance / "Amount owed" (label flips for liabilities), Change/rate, Notes; Cancel / Save footer.
- **Delete** opens a centered confirm modal ("Keep" / "Delete").

## Interactions & Behavior
- **Tab nav** swaps content via active-tab state; sidebar active styling follows.
- **Range toggle** (YTD/1Y/All) updates the trend caption (prototype swaps a string; real app refetches a range — brief §6).
- **Member switch** changes the active identity and therefore **permissions** (see below). Reload defaults to the Owner.
- **Theme toggle** flips `data-theme` on `<html>`; persisted in `localStorage` (`wd-theme`).
- **CRUD**: create/edit via the drawer, delete via confirm modal. On save/delete the prototype **recomputes net worth, assets, liabilities, liquid, the allocation donut + legend, subtotals, largest holdings, and the retirement/real-estate totals instantly** from one in-memory source of truth. In production these are API calls — decide server- vs client-computed (brief §4/§5).
- Drawers/menus close on overlay click; menus use hover states.

## Permissions (role-gated UI)
| Role | Edit | Delete |
|---|---|---|
| Owner, Co-owner | yes | yes |
| Advisor | yes | no |
| Accountant, Viewer | no | no |

When not permitted, all `+`/Edit/Delete affordances are **hidden**. ⚠️ In the prototype this is UI-only — **must be enforced server-side** (brief §9).

## State Management
Prototype state (single `Component`): `tab`, `range`, `selAcct`, `theme`, `activeMember`, `members[]`, `accounts[]` (the source of truth), `drawerOpen`/`drawerNew`/`draft`, `confirmId`. All dashboard figures are **derived** from `accounts` each render. In the target app, replace `accounts[]` with server data via the house data layer; keep `selAcct`/`tab`/`drawer`/`confirm` as local UI state.

## Design Tokens
Defined as CSS custom properties for both themes (`:root` and `:root[data-theme="light"]` in the prototype `<head>`).

- **Neutrals (dark / light):** bg `#0a1712`/`#eceee7`, sidebar `#07120d`/`#e6eae1`, card `#0f211a`/`#ffffff`, border `--bd`, text `#f1f5f1`/`#16271e`, muted `#9fb3a8`/`#5f7268`, label `#7fa392`/`#5c7567`.
- **Accents (shared):** green `#46b888`, gold `#d9b96a`, bronze `#a9743f`, blue `#6c97c4`; positive `--up` `#46d39a`/`#1c8a54`; liability `--liab` `#e0b48a`/`#b06a32`.
- **Type:** Archivo (UI), Spectral (brand mark) — Google Fonts. Tabular numerals throughout (`font-variant-numeric: tabular-nums`). Sizes: KPI value 26px/600, section title 14px/600, body 13–13.5px, labels 10–11px uppercase `~.14em` tracking.
- **Radius:** cards 10px, controls 6–8px, pills/avatars round. **Shadows:** drawers `-30px 0 80px rgba(0,0,0,.5)`, menus `0 24px 60px rgba(0,0,0,.55)`.
- Full token list (gradients, pension palette, toggle states) is in the prototype `:root` blocks — port these to the app's theme system.

## Assets
- **Fonts:** Archivo + Spectral (Google Fonts) — swap to the app's font stack if it has one.
- **Icons:** simple inline SVG line icons (nav, menu, caret) — replace with the app's icon set.
- **Property photos:** striped placeholders labeled `[ PROPERTY PHOTO ]` — the app should drop in real images.
- **Charts:** hand-rolled SVG — rebuild with the app's charting library.
- No raster/brand assets included.

## Screenshots
Rendered reference images are in `screenshots/` (PNG). Fonts fall back in the capture environment, so treat these as layout/color reference — the live prototype uses Archivo/Spectral.
- `01-dark.png` … `06-dark.png` — dark theme: Overview, Accounts, Investments, Retirement, Real estate, Cash flow (in that order).
- `01-light.png`, `02-light.png` — light theme: Overview, Accounts.
- `03-light.png` — Add/Edit CRUD drawer (light).
- `04-light.png` — identity dropdown: switch member, role/access, Appearance toggle (light).

## Files
- `Wealth Dashboard.dc.html` — the full interactive prototype (all screens, theming, CRUD, roles).
- `support.js` — runtime required to open the prototype in a browser.
- `INTEGRATION_BRIEF.md` — open API/backend questions as `TODO:` markers; resolve before wiring to the service.
- (Earlier exploration `Household Wealth Dashboard.dc.html` — three visual directions — remains in the project root if the alternate looks are useful; not included here.)
