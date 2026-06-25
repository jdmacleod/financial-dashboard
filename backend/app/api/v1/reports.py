import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.report import (
    AgeMilestonesReport,
    BudgetTrendReport,
    BudgetVsActualsReport,
    CashFlowReport,
    DashboardResponse,
    EstateExposureReport,
    NetWorthReport,
    PropertyPnLReport,
    RequiredDistributionsReport,
    SavingsRateReport,
    SpendingByCategoryReport,
)
from app.services.milestone import MilestoneService
from app.services.report import ReportService
from app.services.rmd import RmdService

router = APIRouter()


@router.get("/reports/required-distributions", response_model=RequiredDistributionsReport)
async def required_distributions_report(
    year: int | None = Query(None, description="Distribution year; defaults to the current year"),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> RequiredDistributionsReport:
    svc = RmdService(session)
    return await svc.required_distributions(ctx, year)


@router.get("/reports/age-milestones", response_model=AgeMilestonesReport)
async def age_milestones_report(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> AgeMilestonesReport:
    svc = MilestoneService(session)
    return await svc.age_milestones(ctx)


@router.get("/reports/net-worth", response_model=NetWorthReport)
async def net_worth_report(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    interval: Literal["monthly", "quarterly", "annual"] = Query("monthly"),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> NetWorthReport:
    svc = ReportService(session)
    return await svc.net_worth(ctx, from_, to, interval=interval)


@router.get("/reports/cash-flow", response_model=CashFlowReport)
async def cash_flow_report(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    group_by: Literal["month", "quarter"] = Query("month"),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> CashFlowReport:
    svc = ReportService(session)
    return await svc.cash_flow(ctx, from_, to, group_by=group_by)


@router.get("/reports/spending-by-category", response_model=SpendingByCategoryReport)
async def spending_by_category_report(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    parent_category_id: uuid.UUID | None = Query(None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> SpendingByCategoryReport:
    svc = ReportService(session)
    return await svc.spending_by_category(ctx, from_, to, parent_category_id=parent_category_id)


@router.get("/reports/budget-vs-actuals", response_model=BudgetVsActualsReport)
async def budget_vs_actuals_report(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> BudgetVsActualsReport:
    svc = ReportService(session)
    return await svc.budget_vs_actuals(ctx, month)


@router.get("/reports/savings-rate", response_model=SavingsRateReport)
async def savings_rate_report(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> SavingsRateReport:
    svc = ReportService(session)
    return await svc.savings_rate(ctx, from_, to)


@router.get("/reports/budget-trend", response_model=BudgetTrendReport)
async def budget_trend_report(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> BudgetTrendReport:
    svc = ReportService(session)
    return await svc.budget_vs_actuals_trend(ctx, from_, to)


@router.get("/reports/property-pnl", response_model=PropertyPnLReport)
async def property_pnl_report(
    property_id: uuid.UUID = Query(...),
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PropertyPnLReport:
    svc = ReportService(session)
    return await svc.property_pnl(ctx, property_id, from_, to)


@router.get("/reports/estate-exposure", response_model=EstateExposureReport)
async def estate_exposure_report(
    as_of: date = Query(default_factory=date.today),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> EstateExposureReport:
    svc = ReportService(session)
    return await svc.estate_exposure(ctx, as_of)


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> DashboardResponse:
    svc = ReportService(session)
    return await svc.dashboard(ctx)
