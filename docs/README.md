# HearthLedger — Spec Index

This directory contains the complete implementation spec for the HearthLedger
household financial tracking system. Read CLAUDE.md first — it contains the
project context, non-negotiable architectural rules, and coding conventions
that apply to every phase.

## Document map

| File | Purpose |
|---|---|
| `../CLAUDE.md` | Project context, rules, conventions — Claude Code reads this automatically |
| `docs/architecture.md` | System architecture, Docker Compose, nginx routing, RBAC summary |
| `docs/data-model.md` | Complete consolidated database schema (all amendments incorporated) |
| `docs/phase-0-infrastructure.md` | Docker Compose stack, DB init, Alembic baseline migration |
| `docs/phase-1-auth-and-core.md` | Auth, JWT, members, accounts, RBAC, audit log infrastructure |
| `docs/phase-2-transactions.md` | Transactions, categories, CSV/OFX import, duplicate detection |
| `docs/phase-3-analysis.md` | Reports, dashboards, budget vs actuals, property P&L, audit log UI |
| `docs/phase-4-fire-and-debt.md` | FIRE modeling, income streams, debt payoff projections |
| `docs/phase-5-exports.md` | PDF and Excel exports, executor re-auth gate |
| `docs/phase-6-polish.md` | Backup UI, valuation management, dark mode, dashboard customization |

## Design amendments (incorporated into spec above)

The phase docs and data model already incorporate all amendments.
These files document the design reasoning if needed for reference.

| Amendment | Topic |
|---|---|
| Amendment 1 | RBAC, USD-only, real estate API provider pattern, FIRE auto-detection, backup service |
| Amendment 2 | Audit log (table, event catalog, @audit decorator, UI surfaces) |
| Amendment 3 | Property-level P&L (real_estate_property_id on transactions), income stream schema |

## Build order

Phases are sequentially dependent. Each phase has a set of acceptance
criteria that must pass before the next phase begins.

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
Infra     Auth      Txns      Analysis   FIRE       Exports    Polish
```

## Key decisions (v1 scope)

- **USD only.** No multi-currency, no FX tables.
- **Single household per installation.** No multi-tenancy.
- **Balance snapshots only for investment/retirement.** No individual
  holdings or trade history.
- **No Plaid or direct bank connections.** CSV and OFX/QFX import only.
- **Gross salary deferred to v2.** FIRE income streams use gross annual
  amount as a manual input; net take-home is reflected in expenses.
- **No automated restore UI.** Restore is a documented CLI procedure.
- **Real estate provider defaults to `manual`.** ATTOM or Estated
  configurable via `.env` without code changes.
