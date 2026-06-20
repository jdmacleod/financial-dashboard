"""Shared category taxonomy for all HearthLedger demo households."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.db.models.category import Category

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# (slug, display_name, parent_slug | None, is_income)
_DEFS: list[tuple[str, str, str | None, bool]] = [
    # ── Income ────────────────────────────────────────────────────────────────
    ("income",               "Income",                              None,              True),
    ("salary",               "Salary & Wages",                      "income",          True),
    ("bonus",                "Bonus & Commission",                   "income",          True),
    ("business_income",      "Business Income",                     None,              True),
    ("consulting_fees",      "Consulting Fees",                     "business_income", True),
    ("profit_distribution",  "Distribution / Profit Share",         "business_income", True),
    ("investment_income",    "Investment Income",                   None,              True),
    ("dividends",            "Dividends",                           "investment_income",True),
    ("capital_gains",        "Capital Gains",                       "investment_income",True),
    ("rental_income",        "Rental Income",                       None,              True),
    ("residential_rental",   "Residential Rental",                  "rental_income",   True),
    ("short_term_rental",    "Short-Term Rental",                   "rental_income",   True),
    ("other_income",         "Other Income",                        None,              True),
    ("tax_refund",           "Tax Refund",                          "other_income",    True),
    ("gifts_received",       "Gifts Received",                      "other_income",    True),
    ("misc_income",          "Miscellaneous",                       "other_income",    True),
    # ── Housing ───────────────────────────────────────────────────────────────
    ("housing",              "Housing",                             None,              False),
    ("hoa_fees",             "HOA Fees",                            "housing",         False),
    ("home_insurance",       "Home Insurance",                      "housing",         False),
    ("home_maintenance",     "Home Maintenance & Repairs",          "housing",         False),
    ("lawn_garden",          "Lawn & Garden",                       "housing",         False),
    ("cleaning_services",    "Cleaning Services",                   "housing",         False),
    # ── Utilities ─────────────────────────────────────────────────────────────
    ("utilities",            "Utilities",                           None,              False),
    ("electric",             "Electric",                            "utilities",       False),
    ("gas_heating",          "Gas & Heating",                       "utilities",       False),
    ("water_sewer",          "Water & Sewer",                       "utilities",       False),
    ("internet",             "Internet",                            "utilities",       False),
    ("cell_phone",           "Cell Phone",                          "utilities",       False),
    ("streaming",            "Streaming Services",                  "utilities",       False),
    # ── Transportation ────────────────────────────────────────────────────────
    ("transportation",       "Transportation",                      None,              False),
    ("auto_insurance",       "Auto Insurance",                      "transportation",  False),
    ("gas_fuel",             "Gas & Fuel",                          "transportation",  False),
    ("car_maintenance",      "Car Maintenance",                     "transportation",  False),
    ("parking",              "Parking",                             "transportation",  False),
    ("rideshare",            "Rideshare",                           "transportation",  False),
    ("ev_charging",          "EV Charging",                         "transportation",  False),
    # ── Food & Dining ─────────────────────────────────────────────────────────
    ("food_dining",          "Food & Dining",                       None,              False),
    ("groceries",            "Groceries",                           "food_dining",     False),
    ("restaurants",          "Restaurants & Takeout",               "food_dining",     False),
    ("coffee",               "Coffee Shops",                        "food_dining",     False),
    ("food_delivery",        "Food Delivery",                       "food_dining",     False),
    # ── Healthcare ────────────────────────────────────────────────────────────
    ("healthcare",           "Healthcare",                          None,              False),
    ("health_insurance",     "Health Insurance Premium",            "healthcare",      False),
    ("doctor_medical",       "Doctor & Medical",                    "healthcare",      False),
    ("dental",               "Dental",                              "healthcare",      False),
    ("vision",               "Vision",                              "healthcare",      False),
    ("pharmacy",             "Prescriptions & Pharmacy",            "healthcare",      False),
    ("fitness",              "Fitness & Gym",                       "healthcare",      False),
    ("therapy",              "Mental Health / Therapy",             "healthcare",      False),
    # ── Education ─────────────────────────────────────────────────────────────
    ("education",            "Education & Childcare",               None,              False),
    ("tuition",              "Tuition & School Fees",               "education",       False),
    ("school_supplies",      "School Supplies & Books",             "education",       False),
    ("tutoring",             "Tutoring & Lessons",                  "education",       False),
    ("childcare",            "Childcare & After-School",            "education",       False),
    ("student_activities",   "Student Activities & Sports",         "education",       False),
    # ── Personal ──────────────────────────────────────────────────────────────
    ("personal",             "Personal & Shopping",                 None,              False),
    ("clothing",             "Clothing & Apparel",                  "personal",        False),
    ("personal_care",        "Personal Care & Beauty",              "personal",        False),
    ("electronics",          "Electronics & Technology",            "personal",        False),
    ("home_goods",           "Home Goods & Furnishings",            "personal",        False),
    ("gifts_given",          "Gifts Given",                         "personal",        False),
    # ── Entertainment ─────────────────────────────────────────────────────────
    ("entertainment",        "Entertainment & Leisure",             None,              False),
    ("events_tickets",       "Events & Tickets",                    "entertainment",   False),
    ("travel",               "Travel & Vacation",                   "entertainment",   False),
    ("hobbies",              "Hobbies & Recreation",                "entertainment",   False),
    ("pet_care",             "Pet Care",                            "entertainment",   False),
    ("subscriptions",        "Subscriptions & Memberships",         "entertainment",   False),
    # ── Rental Property ───────────────────────────────────────────────────────
    ("property_expenses",    "Rental Property Expenses",            None,              False),
    ("rental_maintenance",   "Rental Property Maintenance",         "property_expenses",False),
    ("property_management",  "Property Management Fees",            "property_expenses",False),
    ("rental_insurance",     "Rental Property Insurance",           "property_expenses",False),
    ("rental_property_tax",  "Rental Property Taxes",               "property_expenses",False),
    # ── Business Expenses ─────────────────────────────────────────────────────
    ("business_expenses",    "Business Expenses",                   None,              False),
    ("office_supplies",      "Office & Supplies",                   "business_expenses",False),
    ("professional_dev",     "Professional Development",            "business_expenses",False),
    ("professional_services","Professional Services (CPA, Legal)",  "business_expenses",False),
    ("business_travel",      "Business Travel",                     "business_expenses",False),
    ("marketing_software",   "Marketing & Software",                "business_expenses",False),
    # ── Financial Services ────────────────────────────────────────────────────
    ("financial_services",   "Financial Services",                  None,              False),
    ("bank_fees",            "Bank & Account Fees",                 "financial_services",False),
    ("advisory_fees",        "Investment Advisory Fees",            "financial_services",False),
    ("tax_prep",             "Tax Preparation",                     "financial_services",False),
    ("life_insurance",       "Life & Umbrella Insurance",           "financial_services",False),
    # ── Transfers ─────────────────────────────────────────────────────────────
    ("transfers",            "Transfers",                           None,              False),
    ("cc_payment",           "Credit Card Payment",                 "transfers",       False),
    ("loan_payment",         "Auto / Personal Loan Payment",        "transfers",       False),
    ("ira_contribution",     "IRA Contribution",                    "transfers",       False),
    ("brokerage_contribution","Brokerage Contribution",             "transfers",       False),
    ("savings_transfer",     "To / From Savings",                   "transfers",       False),
    ("between_accounts",     "Between Own Accounts",                "transfers",       False),
    ("mortgage_payment",     "Mortgage Payment",                    "transfers",       False),
    ("heloc_payment",        "HELOC Payment",                       "transfers",       False),
]


async def seed_categories(
    session: AsyncSession,
    household_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Insert all categories for a household. Returns {slug: category_id}."""
    now = datetime.now(timezone.utc)
    cat_map: dict[str, uuid.UUID] = {}

    for slug, name, parent_slug, is_income in _DEFS:
        cat = Category(
            id=uuid.uuid4(),
            household_id=household_id,
            name=name,
            parent_category_id=cat_map.get(parent_slug) if parent_slug else None,
            is_income=is_income,
            is_system=True,
            created_at=now,
        )
        session.add(cat)
        cat_map[slug] = cat.id

    return cat_map
