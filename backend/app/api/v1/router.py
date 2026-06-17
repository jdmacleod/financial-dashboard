from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    audit_log,
    auth,
    budgets,
    categories,
    debt,
    exports,
    fire,
    household,
    imports,
    members,
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
router.include_router(reports.router)
router.include_router(audit_log.router)
router.include_router(fire.router)
router.include_router(debt.router)
router.include_router(exports.router)
