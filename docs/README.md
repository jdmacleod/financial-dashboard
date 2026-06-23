# HearthLedger: Documentation Index

This directory contains all documentation for the HearthLedger household financial
tracking system.

## User documentation

| File                                                 | Purpose                                                                           |
| ---------------------------------------------------- | --------------------------------------------------------------------------------- |
| `docs/getting-started.md`                            | Install, configure, and run HearthLedger for the first time                       |
| `docs/demo-quickstart.md`                            | Seed demo data and log in with the six sample households                          |
| `docs/user-guide.md`                                 | Complete guide to every feature                                                   |
| `docs/howto-add-accounts.md`                         | How to add accounts across all five category groups                               |
| `docs/howto-view-investment-positions.md`            | How to read the Top positions table and Holdings mix on the Investments page      |
| `docs/howto-track-retirement-income.md`              | How to read the Social Security / pension / RMD breakdown on the Cash Flow report |
| `docs/howto-set-pension-present-value.md`            | How to record a pension benefit estimate and see its present value on net worth   |
| `docs/tutorial-portfolio-and-retirement-insights.md` | Hands-on walkthrough of positions, retirement income, and pension PV on demo data |
| `docs/explanation-pension-present-value.md`          | Why pensions are valued as a finite life annuity, and how estimate history works  |
| `docs/api-reference.md`                              | REST API reference: all endpoints, parameters, and response shapes                |
| `docs/security.md`                                   | Authentication, RBAC, encryption, audit log, and secrets management               |

## Implementation spec (developer reference)

Read CLAUDE.md first: it contains the project context, non-negotiable
architectural rules, and coding conventions that apply to every phase.

| File                                     | Purpose                                                                                                              |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `../CLAUDE.md`                           | Project context, rules, conventions: Claude Code reads this automatically                                            |
| `docs/architecture.md`                   | System architecture, Docker Compose, nginx routing, RBAC summary                                                     |
| `docs/data-model.md`                     | Complete consolidated database schema (all amendments incorporated)                                                  |
| `docs/phase-0-infrastructure.md`         | Docker Compose stack, DB init, Alembic baseline migration                                                            |
| `docs/phase-1-auth-and-core.md`          | Auth, JWT, members, accounts, RBAC, audit log infrastructure                                                         |
| `docs/phase-2-transactions.md`           | Transactions, categories, CSV/OFX import, duplicate detection                                                        |
| `docs/phase-3-analysis.md`               | Reports, dashboards, budget vs actuals, property P&L, audit log UI                                                   |
| `docs/phase-4-fire-and-debt.md`          | FIRE modeling, income streams, debt payoff projections                                                               |
| `docs/phase-5-exports.md`                | PDF and Excel exports, executor re-auth gate                                                                         |
| `docs/phase-6-polish.md`                 | Backup UI, valuation management, dark mode, dashboard customization                                                  |
| `docs/phase-7-demo-households.md`        | Demo seed script: three fictitious households (HELOC, FIRE member attribution)                                       |
| `docs/phase-8-accounts-assets.md`        | Accounts/Assets restructure: dedicated pages, pension PV, real estate balances                                       |
| `docs/phase-9-wealth-dashboard.md`       | Wealth dashboard full UI redesign: 7 tabs, design tokens, EditAccountModal                                           |
| `docs/phase-10-ux-completeness.md`       | Context-aware add buttons on Accounts page, VERSION drift fix                                                        |
| `docs/phase-11-demo-households-h4-h5.md` | Demo seed script: H4 Park-Cole (Nashville) and H5 Langford (Sarasota), additive seeding guard, SEED_DATE_END env var |
| `docs/test-plan.md`                      | Prioritized test list to reach ≥90% coverage; infra gaps to close first                                              |

## Design amendments (incorporated into spec above)

The phase docs and data model already incorporate all amendments.
These files document the design reasoning if needed for reference.

| Amendment   | Topic                                                                                 |
| ----------- | ------------------------------------------------------------------------------------- |
| Amendment 1 | RBAC, USD-only, real estate API provider pattern, FIRE auto-detection, backup service |
| Amendment 2 | Audit log (table, event catalog, @audit decorator, UI surfaces)                       |
| Amendment 3 | Property-level P&L (real_estate_property_id on transactions), income stream schema    |

## Build order

Phases are sequentially dependent. Each phase has a set of acceptance
criteria that must pass before the next phase begins.

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
Infra     Auth      Txns      Analysis   FIRE       Exports    Polish

Phase 7 → Phase 8 → Phase 9  → Phase 10 → Phase 11
Demo      Assets    Dashboard   UX polish   Demo H4+H5
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
