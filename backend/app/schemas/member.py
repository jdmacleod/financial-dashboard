import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _reject_future_dob(value: date | None) -> date | None:
    """Date of birth must not be in the future. Shared by every schema that
    accepts a member DOB so the rule has one home."""
    if value is not None and value > date.today():
        raise ValueError("date_of_birth cannot be in the future")
    return value


# A nullable birth date that rejects future dates at the API boundary.
BirthDate = Annotated[date | None, AfterValidator(_reject_future_dob)]

# Planned retirement age. Bounds match FIRE's scenario-level target_retirement_age
# (18-100) so the two retirement-age fields share one validated domain.
RetirementTargetAge = Annotated[int | None, Field(ge=18, le=100)]

# Social Security claiming age (62-70) and the PIA (monthly benefit at FRA).
SocialSecurityClaimingAge = Annotated[int | None, Field(ge=62, le=70)]
SocialSecurityBenefit = Annotated[Decimal | None, Field(ge=0)]


class MemberCreate(BaseModel):
    display_name: str
    role: Literal["primary", "partner", "dependent"] = "partner"
    date_of_birth: BirthDate = None
    retirement_target_age: RetirementTargetAge = None
    ss_monthly_benefit_at_fra: SocialSecurityBenefit = None
    ss_claiming_age: SocialSecurityClaimingAge = None


class MemberUpdate(BaseModel):
    display_name: str | None = None
    role: Literal["primary", "partner", "dependent"] | None = None
    date_of_birth: BirthDate = None
    retirement_target_age: RetirementTargetAge = None
    ss_monthly_benefit_at_fra: SocialSecurityBenefit = None
    ss_claiming_age: SocialSecurityClaimingAge = None
    is_active: bool | None = None


class DashboardWidget(BaseModel):
    id: str
    visible: bool = True
    order: int


class DashboardLayoutUpdate(BaseModel):
    widgets: list[DashboardWidget]


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    display_name: str
    role: str
    date_of_birth: date | None
    retirement_target_age: int | None
    ss_monthly_benefit_at_fra: Decimal | None
    ss_claiming_age: int | None
    is_active: bool
    settings: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
