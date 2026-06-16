from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.schemas.account import SetupRequest
from app.schemas.auth import TokenResponse
from app.services.setup import SetupService

router = APIRouter()


@router.post("/setup", response_model=TokenResponse, status_code=201)
async def setup(data: SetupRequest, session: AsyncSession = Depends(get_session)):
    svc = SetupService(session)
    access_token, _ = await svc.run(
        household_name=data.household_name,
        member_name=data.member_name,
        email=data.email,
        password=data.password,
    )
    return TokenResponse(access_token=access_token)


@router.get("/setup/status")
async def setup_status(session: AsyncSession = Depends(get_session)):
    svc = SetupService(session)
    done = await svc.is_setup_done()
    return {"setup_complete": done}
