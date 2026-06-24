"""Shared category taxonomy for all HearthLedger demo households."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.db.models.category import Category

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# (slug, display_name, parent_slug | None, is_income, color_hex)
_DEFS: list[tuple[str, str, str | None, bool, str]] = [
    # ── Income ────────────────────────────────────────────────────────────────
    ("income", "Income", None, True, "#22c55e"),
    ("salary", "Salary & Wages", "income", True, "#888888"),
    ("bonus", "Bonus & Commission", "income", True, "#888888"),
    ("business_income", "Business Income", None, True, "#10b981"),
    ("consulting_fees", "Consulting Fees", "business_income", True, "#888888"),
    ("profit_distribution", "Distribution / Profit Share", "business_income", True, "#888888"),
    ("investment_income", "Investment Income", None, True, "#3b82f6"),
    ("dividends", "Dividends", "investment_income", True, "#888888"),
    ("capital_gains", "Capital Gains", "investment_income", True, "#888888"),
    ("rmd_distribution", "Required Minimum Distribution", "investment_income", True, "#888888"),
    ("rental_income", "Rental Income", None, True, "#f59e0b"),
    ("residential_rental", "Residential Rental", "rental_income", True, "#888888"),
    ("short_term_rental", "Short-Term Rental", "rental_income", True, "#888888"),
    ("other_income", "Other Income", None, True, "#94a3b8"),
    ("tax_refund", "Tax Refund", "other_income", True, "#888888"),
    ("gifts_received", "Gifts Received", "other_income", True, "#888888"),
    ("misc_income", "Miscellaneous", "other_income", True, "#888888"),
    ("social_security_income", "Social Security", "other_income", True, "#888888"),
    ("pension_income", "Pension Income", "other_income", True, "#888888"),
    # ── Housing ───────────────────────────────────────────────────────────────
    ("housing", "Housing", None, False, "#3b82f6"),
    ("hoa_fees", "HOA Fees", "housing", False, "#888888"),
    ("home_insurance", "Home Insurance", "housing", False, "#888888"),
    ("home_maintenance", "Home Maintenance & Repairs", "housing", False, "#888888"),
    ("lawn_garden", "Lawn & Garden", "housing", False, "#888888"),
    ("cleaning_services", "Cleaning Services", "housing", False, "#888888"),
    ("home_property_tax", "Home Property Taxes", "housing", False, "#888888"),
    ("rent", "Rent", "housing", False, "#888888"),
    ("renters_insurance", "Renters Insurance", "housing", False, "#888888"),
    # ── Utilities ─────────────────────────────────────────────────────────────
    ("utilities", "Utilities", None, False, "#06b6d4"),
    ("electric", "Electric", "utilities", False, "#888888"),
    ("gas_heating", "Gas & Heating", "utilities", False, "#888888"),
    ("water_sewer", "Water & Sewer", "utilities", False, "#888888"),
    ("internet", "Internet", "utilities", False, "#888888"),
    ("cell_phone", "Cell Phone", "utilities", False, "#888888"),
    ("streaming", "Streaming Services", "utilities", False, "#888888"),
    # ── Transportation ────────────────────────────────────────────────────────
    ("transportation", "Transportation", None, False, "#f97316"),
    ("auto_insurance", "Auto Insurance", "transportation", False, "#888888"),
    ("gas_fuel", "Gas & Fuel", "transportation", False, "#888888"),
    ("car_maintenance", "Car Maintenance", "transportation", False, "#888888"),
    ("parking", "Parking", "transportation", False, "#888888"),
    ("rideshare", "Rideshare", "transportation", False, "#888888"),
    ("ev_charging", "EV Charging", "transportation", False, "#888888"),
    # ── Food & Dining ─────────────────────────────────────────────────────────
    ("food_dining", "Food & Dining", None, False, "#22c55e"),
    ("groceries", "Groceries", "food_dining", False, "#888888"),
    ("restaurants", "Restaurants & Takeout", "food_dining", False, "#888888"),
    ("coffee", "Coffee Shops", "food_dining", False, "#888888"),
    ("food_delivery", "Food Delivery", "food_dining", False, "#888888"),
    # ── Healthcare ────────────────────────────────────────────────────────────
    ("healthcare", "Healthcare", None, False, "#a855f7"),
    ("health_insurance", "Health Insurance Premium", "healthcare", False, "#888888"),
    ("doctor_medical", "Doctor & Medical", "healthcare", False, "#888888"),
    ("dental", "Dental", "healthcare", False, "#888888"),
    ("vision", "Vision", "healthcare", False, "#888888"),
    ("pharmacy", "Prescriptions & Pharmacy", "healthcare", False, "#888888"),
    ("fitness", "Fitness & Gym", "healthcare", False, "#888888"),
    ("therapy", "Mental Health / Therapy", "healthcare", False, "#888888"),
    ("medicare_part_b", "Medicare Part B", "healthcare", False, "#888888"),
    ("medicare_part_d", "Medicare Part D", "healthcare", False, "#888888"),
    ("medigap_supplement", "Medigap Supplement", "healthcare", False, "#888888"),
    ("aca_premium", "ACA Marketplace Premium", "healthcare", False, "#888888"),
    # ── Education ─────────────────────────────────────────────────────────────
    ("education", "Education & Childcare", None, False, "#0ea5e9"),
    ("tuition", "Tuition & School Fees", "education", False, "#888888"),
    ("school_supplies", "School Supplies & Books", "education", False, "#888888"),
    ("tutoring", "Tutoring & Lessons", "education", False, "#888888"),
    ("childcare", "Childcare & After-School", "education", False, "#888888"),
    ("student_activities", "Student Activities & Sports", "education", False, "#888888"),
    # ── Personal ──────────────────────────────────────────────────────────────
    ("personal", "Personal & Shopping", None, False, "#ec4899"),
    ("clothing", "Clothing & Apparel", "personal", False, "#888888"),
    ("personal_care", "Personal Care & Beauty", "personal", False, "#888888"),
    ("electronics", "Electronics & Technology", "personal", False, "#888888"),
    ("home_goods", "Home Goods & Furnishings", "personal", False, "#888888"),
    ("gifts_given", "Gifts Given", "personal", False, "#888888"),
    # ── Entertainment ─────────────────────────────────────────────────────────
    ("entertainment", "Entertainment & Leisure", None, False, "#14b8a6"),
    ("events_tickets", "Events & Tickets", "entertainment", False, "#888888"),
    ("travel", "Travel & Vacation", "entertainment", False, "#888888"),
    ("hobbies", "Hobbies & Recreation", "entertainment", False, "#888888"),
    ("pet_care", "Pet Care", "entertainment", False, "#888888"),
    ("subscriptions", "Subscriptions & Memberships", "entertainment", False, "#888888"),
    # ── Rental Property ───────────────────────────────────────────────────────
    ("property_expenses", "Rental Property Expenses", None, False, "#84cc16"),
    ("rental_maintenance", "Rental Property Maintenance", "property_expenses", False, "#888888"),
    ("property_management", "Property Management Fees", "property_expenses", False, "#888888"),
    ("rental_insurance", "Rental Property Insurance", "property_expenses", False, "#888888"),
    ("rental_property_tax", "Rental Property Taxes", "property_expenses", False, "#888888"),
    # ── Business Expenses ─────────────────────────────────────────────────────
    ("business_expenses", "Business Expenses", None, False, "#64748b"),
    ("office_supplies", "Office & Supplies", "business_expenses", False, "#888888"),
    ("professional_dev", "Professional Development", "business_expenses", False, "#888888"),
    (
        "professional_services",
        "Professional Services (CPA, Legal)",
        "business_expenses",
        False,
        "#888888",
    ),
    ("business_travel", "Business Travel", "business_expenses", False, "#888888"),
    ("marketing_software", "Marketing & Software", "business_expenses", False, "#888888"),
    # ── Financial Services ────────────────────────────────────────────────────
    ("financial_services", "Financial Services", None, False, "#6366f1"),
    ("bank_fees", "Bank & Account Fees", "financial_services", False, "#888888"),
    ("advisory_fees", "Investment Advisory Fees", "financial_services", False, "#888888"),
    ("tax_prep", "Tax Preparation", "financial_services", False, "#888888"),
    ("life_insurance", "Life & Umbrella Insurance", "financial_services", False, "#888888"),
    # ── Transfers ─────────────────────────────────────────────────────────────
    ("transfers", "Transfers", None, False, "#94a3b8"),
    ("cc_payment", "Credit Card Payment", "transfers", False, "#888888"),
    ("loan_payment", "Auto / Personal Loan Payment", "transfers", False, "#888888"),
    ("ira_contribution", "IRA Contribution", "transfers", False, "#888888"),
    ("brokerage_contribution", "Brokerage Contribution", "transfers", False, "#888888"),
    ("savings_transfer", "To / From Savings", "transfers", False, "#888888"),
    ("between_accounts", "Between Own Accounts", "transfers", False, "#888888"),
    ("mortgage_payment", "Mortgage Payment", "transfers", False, "#888888"),
    ("heloc_payment", "HELOC Payment", "transfers", False, "#888888"),
    # ── Demo-data extension (Phase B) ───────────────────────────────────────────
    # Equity-compensation & investment income. No employment_income parent exists,
    # so equity income is grouped under the top-level income parent; distributions
    # and trust income under investment_income.
    ("rsu_vest_income", "RSU Vesting Income", "income", True, "#888888"),
    ("nso_exercise_income", "NSO Exercise Income", "income", True, "#888888"),
    ("espp_purchase", "ESPP Purchase Discount", "income", True, "#888888"),
    ("capital_distribution", "Capital Distribution", "investment_income", True, "#888888"),
    ("crt_income", "CRT Unitrust Income", "investment_income", True, "#888888"),
    ("inherited_ira_rmd", "Inherited IRA RMD", "investment_income", True, "#888888"),
    # QCD: an IRA outflow to charity, credited against the RMD but excluded from
    # taxable income — modeled as a non-income transfer, never ordinary income.
    ("qcd_note", "Qualified Charitable Distribution", "transfers", False, "#888888"),
    # Insurance premiums (new top-level parent; existing insurance lines stay under
    # their current parents to avoid disrupting H1-H5 history).
    ("insurance", "Insurance", None, False, "#f59e0b"),
    ("umbrella_premium", "Umbrella Liability Premium", "insurance", False, "#888888"),
    ("disability_insurance_premium", "Disability Insurance Premium", "insurance", False, "#888888"),
    ("ltc_insurance_premium", "Long-Term Care Premium", "insurance", False, "#888888"),
    ("permanent_life_premium", "Permanent Life Premium", "insurance", False, "#888888"),
    ("specialty_insurance_premium", "Scheduled / Specialty Premium", "insurance", False, "#888888"),
    # Interest expense (new top-level parent) — SBLOC / margin interest.
    ("interest_expense", "Interest Expense", None, False, "#ef4444"),
    ("sbloc_interest", "SBLOC Interest", "interest_expense", False, "#888888"),
    ("margin_interest", "Margin Interest", "interest_expense", False, "#888888"),
    # Education.
    ("private_school_tuition", "Private School Tuition", "education", False, "#888888"),
    # Family support — recurring eldercare for an aging parent (sandwich generation).
    ("eldercare", "Eldercare & Family Support", None, False, "#8b5cf6"),
    # Transfers: equity sales, capital flows, trust/charitable funding, gifting.
    ("equity_sale", "Equity Sale (Diversification)", "transfers", False, "#888888"),
    ("capital_call", "Capital Call", "transfers", False, "#888888"),
    ("capital_distribution_transfer", "Capital Distribution (Cash)", "transfers", False, "#888888"),
    ("sbloc_draw", "SBLOC Draw", "transfers", False, "#888888"),
    ("margin_draw", "Margin Draw / Paydown", "transfers", False, "#888888"),
    ("daf_contribution", "DAF Contribution", "transfers", False, "#888888"),
    ("trust_funding", "Trust Funding", "transfers", False, "#888888"),
    ("gift_to_ilit", "Gift to ILIT", "transfers", False, "#888888"),
    ("annual_exclusion_gift", "Annual Exclusion Gift", "transfers", False, "#888888"),
    ("roth_conversion", "Roth Conversion", "transfers", False, "#888888"),
    ("529_superfund", "529 Superfunding", "transfers", False, "#888888"),
]


async def seed_categories(
    session: AsyncSession,
    household_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Insert all categories for a household. Returns {slug: category_id}."""
    now = datetime.now(UTC)
    cat_map: dict[str, uuid.UUID] = {}

    for slug, name, parent_slug, is_income, color_hex in _DEFS:
        cat = Category(
            id=uuid.uuid4(),
            household_id=household_id,
            name=name,
            slug=slug,
            parent_category_id=cat_map.get(parent_slug) if parent_slug else None,
            color_hex=color_hex,
            is_income=is_income,
            is_system=True,
            created_at=now,
        )
        session.add(cat)
        cat_map[slug] = cat.id

    return cat_map
