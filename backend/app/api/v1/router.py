from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    auth,
    categories,
    household,
    imports,
    members,
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
