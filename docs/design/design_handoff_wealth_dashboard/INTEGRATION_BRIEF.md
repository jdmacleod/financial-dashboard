# Wealth Dashboard — Engineering Handoff Brief

**Design artifact:** `Wealth Dashboard.dc.html` (interactive prototype — open in a browser to click through tabs, theme toggle, member switch, and CRUD flows).
**Target:** apply this design to the existing React frontend backed by the established API.
**Status of this doc:** scaffold. Every `> TODO:` is an open question that must be answered (by the product/back-end owner) before implementation. Resolve them in-line, then this becomes the build spec.

> **How to read the TODOs:** anything marked `TODO` is *not* decided by the design. The prototype made a local assumption to be functional; that assumption is called out so it can be confirmed, corrected, or marked out-of-scope.

---

## 0. Prototype assumptions you must NOT take literally

The prototype is a self-contained mock. These are scaffolding decisions, not product decisions:

- All data lives in one in-memory array in component state; **no persistence** (reload resets).
- Net worth, allocation, subtotals, equity, LTV, and tax buckets are **recomputed client-side** from that array.
- Permissions are enforced **only in the UI** (buttons hidden). There is no server check.
- Theme is stored in `localStorage`. Member switching and "invite" are demo-only.
- Numbers (cash flow, contributions, pension income, projections, holdings/positions) are **hardcoded** where no account record backs them.

> **TODO (global):** For each of the above, decide: real backend feature, frontend-derived, or out-of-scope for v1?

---

## 1. Scope & intent

> **TODO:** Is this design the **target visual spec** (rebuild existing components to match) or **net-new screens** dropped into existing app chrome (nav, header, auth)?
> **TODO:** Which screens are in v1? (Overview, Accounts, Investments, Retirement, Real estate, Cash flow, Members & roles, theme.)
> **TODO:** Does the existing app already have a household/dashboard area this replaces, or is this additive?

---

## 2. Existing frontend conventions (fill in so CC matches, not reinvents)

> **TODO:** React version, TS or JS?
> **TODO:** Data/server-state layer — React Query / RTK Query / SWR / Apollo / custom hooks?
> **TODO:** Client state — Redux / Zustand / Context?
> **TODO:** Component library / design system in use (MUI, Chakra, internal DS)? The prototype uses inline-styled CSS variables; map its tokens (below) onto the real system rather than copying inline styles.
> **TODO:** Routing (React Router? file-based?) and where these tabs mount.
> **TODO:** Forms & validation lib (RHF, Formik, zod)? The CRUD drawer should use the house pattern.
> **TODO:** Charting lib (the mock hand-rolls SVG; real app likely has Recharts/visx/Nivo).
> **TODO:** Money handling util — integer cents vs decimal, formatting/locale helper.

**Design tokens to map** (defined in the prototype's `:root` / `[data-theme="light"]`):
`--bg, --sidebar, --card, --text/--text2/--text3, --muted, --label, --faint, --strong, --up (positive), --liab (negative), --grad (accent card), --pgrad (pension), accents: green `#46b888`, gold `#d9b96a`, bronze `#a9743f`, blue `#6c97c4`.`
> **TODO:** Are dark **and** light both required, or pick one? Is theme a persisted per-user pref (server) or local only?

---

## 3. Data model

The prototype's account record (single unified collection):

```
Account {
  id: string
  name: string
  inst: string              // institution / address
  type: string              // free text ("Checking", "401(k)", "30yr fixed · 3.1%")
  group: "Banking & cash" | "Retirement" | "Investments" | "Real estate" | "Liabilities"
  bal: number               // SIGNED — liabilities negative
  chg: string               // free-text change/rate ("+4.4% APY", "3.10% APR")
  note: string
  tax?: "deferred" | "free" | "guaranteed"   // retirement only
  mortId?: string           // real-estate → linked liability id
  re?: boolean              // liability that is a property mortgage
}
```

> **TODO:** Is there really one `/accounts` collection, or separate resources per type (`/banking-accounts`, `/investment-accounts`, `/retirement-accounts`, `/properties`, `/liabilities`)? This changes every CRUD call below.
> **TODO:** Are balances signed, or positive + a `direction`/`isLiability` flag?
> **TODO:** Is `group`/`category` a server field or frontend-derived from account type?
> **TODO:** Is `tax` (deferred/free/guaranteed) a real server classification or UI-only?
> **TODO:** Is the **property ↔ mortgage** relationship (`mortId`/`re`) modeled server-side, or invented by the prototype? How does the API associate a loan with a property?
> **TODO:** Currency: single or multi? Precision (cents vs float)? Rounding rules for the `$X.XXM` displays?
> **TODO:** Real fields the design omits (account number/mask, opened date, owner/member, status, external sync id)?

---

## 4. Endpoint → widget map

Fill the **Endpoint** and **Source** columns. "Source" = `server` (API returns it) or `derived` (frontend computes from accounts).

| Widget (screen) | Data needed | Endpoint | Source |
|---|---|---|---|
| Overview KPIs (net worth, assets, liabilities, liquid) | aggregates | `TODO` | `TODO server/derived` |
| Net-worth trend + YTD/1Y/All | time series by range | `TODO` | `TODO` |
| "+$892,100 · +14.6%" change | period delta | `TODO` | `TODO` |
| Allocation donut + legend | category totals & % | `TODO` | `TODO` |
| Largest holdings | top-N accounts by value | `TODO` | `derived?` |
| Accounts ledger + subtotals | accounts list grouped | `TODO` | `TODO` |
| Account detail panel (sparkline, "Last synced") | per-account history + sync ts | `TODO` | `TODO` |
| Investments — taxable total | category total | `TODO` | `TODO` |
| Investments — holdings mix | asset-class breakdown | `TODO` | `TODO` |
| Investments — **top positions** (VTI, NVDA…) | per-position holdings | `TODO` | `TODO` |
| Investments — unrealized gains / TLH / fee | tax lots, fees | `TODO` | `TODO` |
| Retirement — tax buckets (deferred/free/guaranteed) | sums by tax type | `TODO` | `derived?` |
| Retirement — contributions YTD / employer match | contributions feed | `TODO` | `TODO` |
| Retirement — pension income $/yr, "projected at 65" | pension terms + projection | `TODO` | `TODO` |
| Real estate — cards (value, equity, mortgage, LTV) | property + linked loan | `TODO` | `TODO` |
| Real estate — rental income / yr | property income | `TODO` | `TODO` |
| Cash flow — income/spend/savings rate, 12-mo bars | transactions/budget | `TODO` | `TODO` |
| Cash flow — category breakdown | categorized spend | `TODO` | `TODO` |
| Header — "22 accounts linked", "Last synced" | aggregation status | `TODO` | `TODO` |
| Members & roles list | household members | `TODO` | `server` |

> **TODO (the pivotal decision):** Are aggregates **server-authoritative** (frontend just renders, refetch after mutation) or **client-computed** (frontend keeps doing the math)? Pick one and apply consistently — mixing causes drift.

---

## 5. Computed-client vs. server-authoritative matrix

For each, mark the authority. If `server`, give the endpoint. If `client`, confirm the inputs are all available.

| Value | Prototype does | Should be |
|---|---|---|
| Net worth | client sum | `TODO` |
| Total assets / liabilities | client sum | `TODO` |
| Liquid (cash) | client sum | `TODO` |
| Allocation % | client | `TODO` |
| Category subtotals | client | `TODO` |
| Retirement tax-bucket split | client (by `tax` field) | `TODO` |
| Real-estate equity / LTV | client (value − linked loan) | `TODO` |
| Net-worth % change over range | hardcoded | `TODO server` |

---

## 6. Time-series / history

The trend chart and range toggles need historical snapshots.

> **TODO:** History endpoint + range/granularity params? (daily vs monthly snapshots)
> **TODO:** Are per-account sparklines real history or decorative? (prototype's are decorative)
> **TODO:** Is the range delta ("+14.6% trailing year") server-computed per range?

---

## 7. Account aggregation / sync

> **TODO:** Are accounts manually entered, synced via an aggregator (Plaid/MX/Yodlee), or both?
> **TODO:** Can a **synced** account's balance be hand-edited, or is it read-only/refresh-only? (affects whether the Edit drawer applies to all accounts)
> **TODO:** What feeds "Last synced" and "N accounts linked"? Is there a manual "refresh" action to add?

---

## 8. CRUD semantics

Prototype behavior → confirm/replace:

- **Create:** drawer with name, institution, type, category, balance, change/rate, notes; new id client-side; liabilities stored negative.
- **Update:** same drawer prefilled; preserves `tax`/`re`/`mortId`.
- **Delete:** confirm modal, removes from list, reselects first account.

> **TODO:** Real create/update/delete endpoints + request/response shapes.
> **TODO:** Validation rules (required fields, balance format, category constraints, which fields are editable per account type).
> **TODO:** Optimistic update with rollback on error, or pessimistic (await server)? Existing app's convention?
> **TODO:** **Delete = hard or soft?** Financial data usually wants soft-delete + audit history. Undo expected?
> **TODO:** Concurrency — multiple members editing: last-write-wins, ETags/If-Match, conflict UI?
> **TODO:** When category changes on edit (e.g. moving an account between groups), is that a valid operation server-side?
> **TODO:** Adding a **property** — does it require creating/linking a mortgage in the same flow? The prototype treats them as separate records.
> **TODO:** Error, empty, and loading states — none exist in the mock; specify per surface.

---

## 9. Identity, auth & permissions

Prototype roles: **Owner**, **Co-owner** (full), **Advisor** (edit, no delete), **Accountant** / **Viewer** (read-only). Gating: add/edit/delete affordances hidden when not permitted.

> **TODO:** How is the current user + household established (session, JWT, household id in path)?
> **TODO:** Are these the real roles and capability mappings? Confirm the edit-vs-delete split for Advisor.
> **TODO:** **Permissions must be enforced server-side** — the UI gating is cosmetic. Does the API return the caller's capabilities (so UI mirrors them dynamically) or must they be hardcoded per role in the client?
> **TODO:** Are "Switch member" and "Invite a member" real flows (impersonation? invite endpoint + email?) or demo-only?
> **TODO:** Role change in the Members panel — real `PATCH /members/:id` (who's allowed)?

---

## 10. Cross-cutting / non-functional

> **TODO:** Pagination/virtualization if account or transaction counts grow.
> **TODO:** Number/date formatting, locale, i18n.
> **TODO:** Accessibility bar (keyboard nav for drawer/menus/modals, focus traps, ARIA, contrast in both themes).
> **TODO:** Analytics/telemetry events on CRUD and navigation?
> **TODO:** Performance budget / where heavy aggregation runs.

---

## 11. Suggested build order (once TODOs are resolved)

1. Map design tokens → existing design system; stand up the shell (sidebar, header, identity widget) as static.
2. Wire **read** paths: accounts list + Overview aggregates (decide server vs derived first — §4/§5).
3. Add CRUD against real endpoints with the house data layer; handle optimistic/error states.
4. Wire role capabilities from the API; gate UI from server-provided permissions.
5. Fill analytics surfaces that have real data (history, cash flow, retirement, investments positions); stub or hide the rest behind flags.
6. Theme + persistence; a11y pass; empty/loading/error states.

---

### Appendix — open-question count
Search this file for `TODO:` — each is a decision needed. Resolve top-to-bottom; §3 (data model) and §4/§5 (authority of aggregates) unblock the most downstream work.
