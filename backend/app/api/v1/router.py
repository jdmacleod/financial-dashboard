from fastapi import APIRouter

from app.api.v1 import accounts, auth, household, members, setup, users

router = APIRouter()

router.include_router(setup.router)
router.include_router(auth.router)
router.include_router(household.router)
router.include_router(members.router)
router.include_router(users.router)
router.include_router(accounts.router)
