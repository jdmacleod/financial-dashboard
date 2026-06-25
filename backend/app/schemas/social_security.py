from decimal import Decimal

from pydantic import BaseModel


class SocialSecurityClaimingOption(BaseModel):
    claiming_age: int
    monthly_benefit: Decimal
    annual_benefit: Decimal
    pct_of_pia: float
    is_fra: bool


class SocialSecurityComparison(BaseModel):
    """Adjusted Social Security benefit at each whole claiming age 62-70.

    `pia_monthly` is the supplied Full Retirement Age benefit estimate;
    `fra_months` is the member's FRA in total months (e.g. 804 = 67y, 798 = 66y6m).
    """

    pia_monthly: Decimal
    fra_months: int
    options: list[SocialSecurityClaimingOption]
