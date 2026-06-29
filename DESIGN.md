# HearthLedger Design System

The design reference for HearthLedger's frontend. It documents the tokens,
typography, layout, and component vocabulary that actually ship, so UI work and
design reviews calibrate against HearthLedger conventions instead of generic
principles.

This document is **descriptive of the code**, not aspirational. Every token and
pattern below is sourced from a real file (cited inline). When the code and this
doc disagree, the code wins — update this doc in the same PR.

> **Tooling note:** gstack design-review skills auto-read a root-level
> `DESIGN.md`. Keeping this file accurate makes `/design-review` and the `/ship`
> lite design check HearthLedger-aware.

---

## 0. The two-system reality (read this first)

HearthLedger currently runs **two visual systems** side by side. This is known
drift, not intent. New work should use System A; report/form pages on System B
should converge onto it over time (see §8).

|         | **System A — "Hearth" (canonical)**                                                                   | **System B — Tailwind-utility (legacy)**                  |
| ------- | ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Palette | Green/gold/bronze on warm dark; theme-aware CSS variables (`var(--card)`, `var(--text)`, `var(--up)`) | `indigo-600` accent, `gray-200` borders, `bg-white`       |
| Styling | Inline `style={{…}}` with CSS variables                                                               | Tailwind utility classes                                  |
| Source  | `src/index.css` `:root` tokens + `components/ui/*` primitives                                         | hand-written classes per component                        |
| Theme   | Dark **default** + light override, switches live                                                      | Light-only (hard-coded white/gray)                        |
| Where   | Dashboard shell, Overview/Accounts/Investments/Retirement, the `ui/` primitives                       | Most `reports/*`, forms/modals, settings (~27 page files) |

**Rule of thumb for new code:** use the Hearth tokens and the `ui/` primitives.
Do not add new `indigo-600` / `gray-200` / `bg-white` surfaces.

---

## 1. Color tokens

Defined in `src/index.css`. The theme-aware set lives on `:root` (dark, the
default) with a `:root[data-theme="light"]` override and is consumed as
`var(--name)`. Dark mode is toggled by the `data-theme` attribute on `<html>`
(`@variant dark` in `index.css`).

### Surfaces & lines

| Token                | Dark                    | Light                 | Use                               |
| -------------------- | ----------------------- | --------------------- | --------------------------------- |
| `--bg`               | `#0a1712`               | `#eceee7`             | App background                    |
| `--sidebar`          | `#07120d`               | `#e6eae1`             | Sidebar background                |
| `--card`             | `#0f211a`               | `#ffffff`             | Card / panel surface              |
| `--bd`               | `rgba(255,255,255,.06)` | `rgba(20,40,30,.10)`  | Default hairline border / divider |
| `--bd2`              | `rgba(255,255,255,.10)` | `rgba(20,40,30,.16)`  | Stronger border                   |
| `--track` / `--grid` | `~.07` white            | `~.08` ink            | Progress tracks, chart gridlines  |
| `--row-active`       | `rgba(70,184,136,.12)`  | `rgba(47,143,99,.13)` | Active/selected row tint          |

### Text

| Token                 | Dark                  | Light                 | Use                                     |
| --------------------- | --------------------- | --------------------- | --------------------------------------- |
| `--text`              | `#f1f5f1`             | `#16271e`             | Primary values                          |
| `--text2` / `--text3` | `#e7ece7` / `#dfe7e1` | `#23362c` / `#2b3f34` | Body, row text                          |
| `--text-soft`         | `#cdd4cb`             | `#3a4d42`             | Secondary body                          |
| `--strong`            | `#f3eede`             | `#10201a`             | Emphasis / headline figures             |
| `--muted`             | `#9fb3a8`             | `#5f7268`             | Muted text                              |
| `--label`             | `#7fa392`             | `#5c7567`             | Field labels                            |
| `--faint`             | `#6f897c`             | `#7d8c83`             | Uppercase micro-labels, section headers |
| `--axis`              | `#5d7068`             | `#94a39a`             | Chart axis text                         |

### Accent & status

The product accent is **green** (a hearth/warmth palette), not blue/indigo.

| Token                  | Dark                                                 | Light                 | Use                           |
| ---------------------- | ---------------------------------------------------- | --------------------- | ----------------------------- |
| `--up`                 | `#46d39a`                                            | `#1c8a54`             | Positive / assets / gains     |
| `--liab`               | `#e0b48a`                                            | `#b06a32`             | Liabilities (warm tan)        |
| `--grad` / `--grad160` | green gradient                                       | light gradient        | Net-worth / accent card fills |
| `--accent-bd`          | `rgba(70,184,136,.28)`                               | `rgba(47,143,99,.32)` | Accent card border            |
| Nav                    | `--nav-text`, `--nav-active-text`, `--nav-active-bg` | —                     | Sidebar nav idle/active       |
| Toggle                 | `--toggle-on-bg/-text`, `--toggle-off-bg/-text`      | —                     | Segmented controls            |

A secondary **blue/pension** cluster (`--pgrad`, `--ptext`, `--pmuted`,
`--plabel`, `--pbd`) styles pension/guaranteed-income surfaces. `--photo` is a
diagonal hatch placeholder for missing property imagery.

### Chart palette (`@theme`, dark-only)

The `@theme` block in `index.css` exposes a fixed chart palette as Tailwind
color utilities and JS-readable values: `--color-up #46d39a`, `--color-green
#46b888`, `--color-gold #d9b96a`, `--color-bronze #a9743f`, `--color-blue
#6c97c4`, `--color-liab #e0b48a`, plus `--color-muted/label/axis` for chart text.
**These are dark-only** — they do not have light-theme variants, so use them for
Recharts series colors, not for theme-aware page chrome (use `var(--…)` for that).

---

## 2. Typography

Loaded via `@fontsource` in `src/main.tsx`; no external font CDN.

- **Archivo** — the workhorse. Weights **400 / 500 / 600 / 700**. Set as the
  global `body` font in `index.css` (`font-family: "Archivo", sans-serif`).
- **Spectral** — **weight 600 only**, used in exactly one place: the brand
  wordmark (household name) in `AppLayout.tsx`. It is the serif brand accent, not
  a body font. Do not use Spectral for content.
- **Tabular numerals are global** — `body { font-variant-numeric: tabular-nums }`
  so currency columns align. Keep figures in Archivo; never override this.

### Type scale (observed)

| Size / weight                                           | Role                             | Example source             |
| ------------------------------------------------------- | -------------------------------- | -------------------------- |
| 10px / 600, `letter-spacing .1em`, uppercase, `--faint` | Section micro-labels             | `ui/section-header.tsx`    |
| 12px / 500                                              | Controls, sub-text, range toggle | `AppLayout` range toggle   |
| 13px / 400–600                                          | Row label/value, brand wordmark  | `ui/data-row.tsx`, brand   |
| 22px / 700                                              | KPI / headline figures           | `pages/Dashboard.tsx`      |
| `text-2xl font-semibold` (Tailwind)                     | Report page `<h1>` (System B)    | `pages/ReportSpending.tsx` |

---

## 3. Spacing, radius, layout

### Radius scale

`7px` (segmented-control button) · `8px` (nav link `rounded-lg`, brand mark) ·
`9px` (segmented-control track) · `14px` (`DataCard`). System-B report cards use
Tailwind `rounded-xl` (12px) — converge these to 14px when touched.

### Spacing primitives

- Section header padding: `12px 16px`, bottom border `1px var(--bd)`.
- Data row padding: `8px 16px`, `8px` gap, bottom border `1px var(--bd)`.
- Card inner padding: ~`17–22px`. Card grids: CSS grid, `12px` gaps.
- Nav link: `px-3 py-2`, `gap-2.5`.

### Layout shell (`components/app/AppLayout.tsx`)

- **Full-viewport flex row.** Fixed left **sidebar `214px`**; main area flexes.
- **Sidebar:** brand mark (`--toggle-on-bg` rounded-8 tile + Spectral household
  name + uppercase "Wealth ledger" in `--faint`) → nav list → footer net worth.
- **Nav item:** `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm
transition-colors`; color/background from `--nav-text` ↔ `--nav-active-*`.
  Active = current path or path prefix. Each item carries a 15px inline SVG icon.
- **Header:** household name + "As of … · N accounts linked" on the left; range
  toggle + divider + identity widget on the right.
- Responsive: the sidebar collapses behind a toggle (`sidebarOpen`), closed on
  Escape / outside click.

---

## 4. Component vocabulary

The canonical primitives live in `src/components/ui/` and are pure
Hearth-token, inline-styled building blocks.

### `SectionHeader` (`ui/section-header.tsx`)

Row with `space-between`, `12px 16px` padding, bottom `1px var(--bd)`. Title is
a 10px/600 uppercase `0.1em`-tracked `--faint` label; optional right-aligned
`action` slot. Use to head every card/panel.

### `DataCard` (`ui/data-card.tsx`)

`background: var(--card)`, `1px var(--bd)` border, **`14px`** radius,
`overflow: hidden`. The standard panel container. Compose:
`<DataCard><SectionHeader>…</SectionHeader><DataRow…/></DataCard>`.

### `DataRow` (`ui/data-row.tsx`)

Flex row, `8px` gap, `8px 16px` padding, bottom `1px var(--bd)`. `label` is 13px
`--text3` and flexes; value is 13px `--text`, right-aligned.

### Range toggle (segmented control) — `AppLayout.tsx`

Track: `var(--toggle-off-bg)`, `3px` padding, `9px` radius. Buttons: `4px 10px`,
`7px` radius, 12px/500; active = `--toggle-on-bg` / `--toggle-on-text`, idle =
transparent / `--toggle-off-text`; `transition: background .1s, color .1s`.
**This is the canonical pill/toggle.** Note the drift: `pages/ReportSpending.tsx`
uses a different pill (`rounded-full px-3 py-1 text-xs … bg-indigo-600`) — that
is System B and should move to this pattern.

### Modal / drawer — **two patterns exist (drift)**

- **Hearth overlay** (`EditAccountModal.tsx`): `position: fixed` overlay,
  `background: var(--card)` panel, inline styles, labeled close button.
- **Native `<dialog>`** (`AddTransactionModal.tsx`): `w-full max-w-lg rounded-xl
shadow-xl p-6` with `backdrop:bg-black/30`, Tailwind utilities, `bg-white` card.

Pick one when you next touch modals. Recommended target: native `<dialog>` (free
focus-trap + Escape + backdrop) themed with `var(--card)` / `var(--bd)` instead of
`bg-white`. Slide-overs (`AddPersonSlideOver.tsx`) are the right-edge variant.

### Identity / role colors

Role ring colors (`AppLayout.tsx`): primary `#46b888` (green), partner `#6c97c4`
(blue), viewer `#9fb3a8` (muted). Role labels: "Full access" / "Partner" / "View
only".

---

## 5. Motion

Restrained. Color transitions only — no entrance animations on data.
`transition-colors` on nav links and interactive text; the range toggle animates
`background`/`color` over `0.1s`. Keep new interactions in this register; never
animate layout/position of financial figures.

---

## 6. Value formatting (`src/lib/formatters.ts`)

Formatting is part of the visual language — use these helpers, never ad-hoc.

- **Currency:** `formatCurrency` → `Intl.NumberFormat("en-US", { style:
"currency", currency: "USD" })`. USD only (v1). Pair with tabular-nums.
- **Null money:** `formatCurrencyOrDash` → em dash `—` for `null`. The em dash is
  the canonical "no value" glyph.
- **Dates:** `formatDate` → `en-US` `{year:"numeric", month:"short",
day:"numeric"}`, parsed at local midday to avoid the UTC day-rollback bug.
- **Masked account:** `formatMaskedAccountNumber` → `XXX...1234`.

---

## 7. Accessibility conventions

- Interactive targets ≥ 44px (Phase 7 spec).
- `font-variant-numeric: tabular-nums` keeps figures aligned for scanning.
- Focus indicators: use a 2px accent outline with `2px` offset
  (`:focus-visible`). Coverage is currently partial.
- **Open work:** a full WCAG 2.1 AA audit is tracked in `TODOS.md` (contrast,
  screen-reader labels for Recharts, keyboard order, focus visibility). The known
  contrast risk is `indigo-600` on white small text in System B pages — another
  reason to converge onto Hearth tokens.

---

## 8. Known drift & convergence guidance

These are the live inconsistencies a reviewer should flag and a contributor
should chip away at (never expand):

1. **Palette split** — System B (`indigo-600` / `gray-200` / `bg-white`) appears
   across most `reports/*`, forms, and settings pages. Target: Hearth `var(--…)`
   tokens. Highest-visibility offender: `ReportSpending.tsx` range pills and
   drill link (`text-indigo-600`).
2. **Styling method split** — inline-style + vars (dashboard) vs Tailwind
   utilities (reports). Either is acceptable _if it uses Hearth tokens_; the
   palette matters more than the mechanism.
3. **Two modal patterns** (§4) — standardize.
4. **`@theme` is dark-only** — Tailwind color classes generated from `@theme`
   (`bg-card`, `text-muted`, …) will not theme-switch. For theme-aware chrome use
   `var(--…)`; reserve `@theme` colors for charts.
5. **`src/App.css` is vestigial** — leftover Vite-starter CSS (`.hero`,
   `.counter`, `.vite`) referencing undefined `--accent*` vars. It is not part of
   the system and is safe to delete.

---

_Maintenance: this file is hand-derived from the code. When you change a token in
`index.css`, a primitive in `components/ui/`, or a formatter, update the matching
section here in the same PR. Re-run `/design-consultation` if the system is
overhauled wholesale._
