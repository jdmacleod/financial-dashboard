from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    advisory_notes,
    audit_log,
    auth,
    backups,
    budgets,
    categories,
    debt,
    exports,
    fire,
    household,
    imports,
    insurance_policies,
    members,
    ownership_entities,
    pension,
    properties,
    reports,
    setup,
    snapshots,
    transactions,
    users,
)

router = APIRouter()

router.include_router(setup.router)
router.include_router(auth.router)
router.include_router(household.router)
router.include_router(members.router)
router.include_router(users.router)
router.include_router(accounts.router)
router.include_router(transactions.router)
router.include_router(categories.router)
router.include_router(snapshots.router)
router.include_router(imports.router)
router.include_router(budgets.router)
router.include_router(properties.router)
router.include_router(pension.router)
router.include_router(reports.router)
router.include_router(audit_log.router)
router.include_router(fire.router)
router.include_router(debt.router)
router.include_router(exports.router)
router.include_router(backups.router)
router.include_router(ownership_entities.router)
router.include_router(insurance_policies.router)
router.include_router(advisory_notes.router)
