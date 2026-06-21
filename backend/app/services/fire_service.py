from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot
from app.core.visibility import VisibilityContext
from app.db.models.fire import FireScenario as FireScenarioModel
from app.db.models.member import HouseholdMember
from app.schemas.fire import (
    FireDetectionResponse,
    FireProjectionResponse,
    FireProjectionSummary,
    FireScenarioCreate,
    FireScenarioResponse,
    FireScenarioUpdate,
    IncomeStream,
    YearProjectionResponse,
)
from app.services.fire_detector import FireInputDetector
from app.services.fire_projector import FireScenario as FireScenarioDataclass
from app.services.fire_projector import project


def _to_response(row: FireScenarioModel) -> FireScenarioResponse:
    streams = [IncomeStream(**s) for s in (row.additional_income_streams or [])]
    return FireScenarioResponse(
        id=row.id,
        household_id=row.household_id,
        member_id=row.member_id,
        name=row.name,
        target_annual_spend=row.target_annual_spend,
        safe_withdrawal_rate=row.safe_withdrawal_rate,
        expected_annual_return=row.expected_annual_return,
        expected_inflation_rate=row.expected_inflation_rate,
        target_retirement_age=row.target_retirement_age,
        additional_income_streams=streams,
        detected_annual_income=row.detected_annual_income,
        detected_annual_expenses=row.detected_annual_expenses,
        detected_savings_rate=row.detected_savings_rate,
        detected_portfolio_value=row.detected_portfolio_value,
        detection_trailing_months=row.detection_trailing_months,
        detected_at=row.detected_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class FireScenarioService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    def _assert_writable(self, ctx: VisibilityContext) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    async def _assert_member_in_household(
        self, ctx: VisibilityContext, member_id: uuid.UUID | None
    ) -> None:
        if member_id is None:
            return
        result = await self.session.execute(
            select(HouseholdMember.id).where(
                HouseholdMember.id == member_id,
                HouseholdMember.household_id == ctx.household_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    async def _get_row(self, ctx: VisibilityContext, scenario_id: uuid.UUID) -> FireScenarioModel:
        result = await self.session.execute(
            select(FireScenarioModel).where(
                FireScenarioModel.id == scenario_id,
                FireScenarioModel.household_id == ctx.household_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="FIRE scenario not found"
            )
        return row

    async def list(self, ctx: VisibilityContext) -> list[FireScenarioResponse]:
        result = await self.session.execute(
            select(FireScenarioModel).where(FireScenarioModel.household_id == ctx.household_id)
        )
        rows = list(result.scalars().all())
        return [_to_response(r) for r in rows]

    async def create(
        self, ctx: VisibilityContext, data: FireScenarioCreate
    ) -> FireScenarioResponse:
        self._assert_writable(ctx)
        await self._assert_member_in_household(ctx, data.member_id)
        now = datetime.now(UTC)
        row = FireScenarioModel(
            household_id=ctx.household_id,
            member_id=data.member_id,
            name=data.name,
            target_annual_spend=data.target_annual_spend,
            safe_withdrawal_rate=data.safe_withdrawal_rate,
            expected_annual_return=data.expected_annual_return,
            expected_inflation_rate=data.expected_inflation_rate,
            target_retirement_age=data.target_retirement_age,
            additional_income_streams=[
                s.model_dump(mode="json") for s in data.additional_income_streams
            ],
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)

        await self.audit_repo.write(
            ctx=ctx,
            action="fire_scenario.created",
            entity_type="fire_scenario",
            entity_id=row.id,
            new_value=_snapshot(row, exclude=AUDIT_EXCLUDED_FIELDS),
        )
        return _to_response(row)

    async def get(self, ctx: VisibilityContext, scenario_id: uuid.UUID) -> FireScenarioResponse:
        row = await self._get_row(ctx, scenario_id)
        return _to_response(row)

    async def update(
        self,
        ctx: VisibilityContext,
        scenario_id: uuid.UUID,
        data: FireScenarioUpdate,
    ) -> FireScenarioResponse:
        self._assert_writable(ctx)
        row = await self._get_row(ctx, scenario_id)

        prev = _snapshot(row, exclude=AUDIT_EXCLUDED_FIELDS)

        if "member_id" in data.model_fields_set:
            await self._assert_member_in_household(ctx, data.member_id)
            row.member_id = data.member_id
        if data.name is not None:
            row.name = data.name
        if data.target_annual_spend is not None:
            row.target_annual_spend = data.target_annual_spend
        if data.safe_withdrawal_rate is not None:
            row.safe_withdrawal_rate = data.safe_withdrawal_rate
        if data.expected_annual_return is not None:
            row.expected_annual_return = data.expected_annual_return
        if data.expected_inflation_rate is not None:
            row.expected_inflation_rate = data.expected_inflation_rate
        if data.target_retirement_age is not None:
            row.target_retirement_age = data.target_retirement_age
        if data.additional_income_streams is not None:
            row.additional_income_streams = [
                s.model_dump(mode="json") for s in data.additional_income_streams
            ]
        if data.detection_trailing_months is not None:
            row.detection_trailing_months = data.detection_trailing_months

        row.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(row)

        curr = _snapshot(row, exclude=AUDIT_EXCLUDED_FIELDS)
        changed_keys = {k for k in set(prev) | set(curr) if prev.get(k) != curr.get(k)}
        await self.audit_repo.write(
            ctx=ctx,
            action="fire_scenario.updated",
            entity_type="fire_scenario",
            entity_id=row.id,
            previous_value={k: prev.get(k) for k in changed_keys},
            new_value={k: curr.get(k) for k in changed_keys},
        )
        return _to_response(row)

    async def delete(self, ctx: VisibilityContext, scenario_id: uuid.UUID) -> None:
        self._assert_writable(ctx)
        row = await self._get_row(ctx, scenario_id)

        prev = _snapshot(row, exclude=AUDIT_EXCLUDED_FIELDS)
        await self.session.delete(row)
        await self.session.flush()

        await self.audit_repo.write(
            ctx=ctx,
            action="fire_scenario.deleted",
            entity_type="fire_scenario",
            entity_id=scenario_id,
            previous_value=prev,
        )

    async def detect(
        self,
        ctx: VisibilityContext,
        scenario_id: uuid.UUID,
        trailing_months: int = 12,
    ) -> FireDetectionResponse:
        self._assert_writable(ctx)
        row = await self._get_row(ctx, scenario_id)

        detector = FireInputDetector(self.session)
        result = await detector.detect(ctx, trailing_months=trailing_months)

        # Preserve manually-entered streams; merge auto-detected streams
        existing_streams: list[IncomeStream] = [
            IncomeStream(**s) for s in (row.additional_income_streams or [])
        ]
        manual_streams = [s for s in existing_streams if not s.auto_detected]
        # Dual-dict: prefer source_account_id match; fall back to label match
        existing_auto_by_source = {
            str(s.source_account_id): s
            for s in existing_streams
            if s.auto_detected and s.source_account_id is not None
        }
        existing_auto_by_label = {
            s.label: s for s in existing_streams if s.auto_detected and s.source_account_id is None
        }

        merged: list[IncomeStream] = list(manual_streams)
        for detected_stream in result.income_streams:
            existing = existing_auto_by_source.get(
                str(detected_stream.source_account_id)
                if detected_stream.source_account_id is not None
                else ""
            ) or existing_auto_by_label.get(detected_stream.label)
            if existing is not None:
                updated = IncomeStream(
                    **{
                        **existing.model_dump(),
                        "amount_annual": detected_stream.amount_annual,
                        "detected_at": detected_stream.detected_at,
                    }
                )
                merged.append(updated)
            else:
                merged.append(detected_stream)

        row.additional_income_streams = [s.model_dump(mode="json") for s in merged]
        row.detected_annual_income = result.gross_income_annual
        row.detected_annual_expenses = result.total_expenses_annual
        row.detected_savings_rate = result.savings_rate
        row.detected_portfolio_value = result.current_portfolio_value
        row.detection_trailing_months = trailing_months
        row.detected_at = result.detected_at
        row.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(row)

        await self.audit_repo.write(
            ctx=ctx,
            action="fire_scenario.detected",
            entity_type="fire_scenario",
            entity_id=row.id,
            new_value={
                "detected_annual_income": str(result.gross_income_annual),
                "detected_annual_expenses": str(result.total_expenses_annual),
                "detected_savings_rate": str(result.savings_rate),
                "trailing_months": trailing_months,
            },
        )
        return FireDetectionResponse(scenario=_to_response(row), warnings=result.warnings)

    async def _get_primary_member_dob(self, ctx: VisibilityContext) -> date | None:
        result = await self.session.execute(
            select(HouseholdMember.date_of_birth)
            .where(
                HouseholdMember.household_id == ctx.household_id,
                HouseholdMember.role == "primary",
                HouseholdMember.is_active.is_(True),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_member_dob(self, member_id: uuid.UUID) -> date | None:
        result = await self.session.execute(
            select(HouseholdMember.date_of_birth).where(HouseholdMember.id == member_id)
        )
        return result.scalar_one_or_none()

    async def project(
        self,
        ctx: VisibilityContext,
        scenario_id: uuid.UUID,
        from_year: int | None = None,
    ) -> FireProjectionResponse:
        row = await self._get_row(ctx, scenario_id)

        if from_year is None:
            from_year = datetime.now(UTC).year

        if row.member_id is not None:
            dob = await self._get_member_dob(row.member_id)
        else:
            dob = await self._get_primary_member_dob(ctx)

        scenario = FireScenarioDataclass(
            id=row.id,
            target_annual_spend=row.target_annual_spend,
            safe_withdrawal_rate=row.safe_withdrawal_rate,
            expected_annual_return=row.expected_annual_return,
            expected_inflation_rate=row.expected_inflation_rate,
            income_streams=[IncomeStream(**s) for s in (row.additional_income_streams or [])],
            detected_portfolio_value=row.detected_portfolio_value,
        )

        year_projections = project(scenario, from_year, dob)

        fire_year: int | None = None
        fire_age: int | None = None
        for yp in year_projections:
            if yp.is_fire_year:
                fire_year = yp.year
                fire_age = yp.age
                break

        fire_number = (
            year_projections[0].fire_number
            if year_projections
            else (row.target_annual_spend / row.safe_withdrawal_rate)
        )

        years_to_fire = (fire_year - from_year) if fire_year is not None else None

        if fire_year is not None and fire_age is not None:
            headline = f"FIRE in {years_to_fire} years at age {fire_age}"
        elif fire_year is not None:
            headline = f"FIRE in {years_to_fire} years (year {fire_year})"
        else:
            headline = "FIRE number not reached within 75 years"

        summary = FireProjectionSummary(
            fire_year=fire_year,
            fire_age=fire_age,
            years_to_fire=years_to_fire,
            fire_number=fire_number,
            headline=headline,
        )

        projections = [
            YearProjectionResponse(
                year=yp.year,
                age=yp.age,
                portfolio=yp.portfolio,
                annual_income=yp.annual_income,
                annual_spend=yp.annual_spend,
                annual_savings=yp.annual_savings,
                supplemental_income=yp.supplemental_income,
                effective_withdrawal=yp.effective_withdrawal,
                fire_number=yp.fire_number,
                is_fire_year=yp.is_fire_year,
            )
            for yp in year_projections
        ]

        return FireProjectionResponse(summary=summary, projections=projections)
