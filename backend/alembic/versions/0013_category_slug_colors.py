"""Add category slug column and seed system category colors.

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_NAME_TO_SLUG = [
    ("Income", "income"),
    ("Salary & Wages", "salary"),
    ("Bonus & Commission", "bonus"),
    ("Business Income", "business_income"),
    ("Consulting Fees", "consulting_fees"),
    ("Distribution / Profit Share", "profit_distribution"),
    ("Investment Income", "investment_income"),
    ("Dividends", "dividends"),
    ("Capital Gains", "capital_gains"),
    ("Required Minimum Distribution", "rmd_distribution"),
    ("Rental Income", "rental_income"),
    ("Residential Rental", "residential_rental"),
    ("Short-Term Rental", "short_term_rental"),
    ("Other Income", "other_income"),
    ("Tax Refund", "tax_refund"),
    ("Gifts Received", "gifts_received"),
    ("Miscellaneous", "misc_income"),
    ("Social Security", "social_security_income"),
    ("Pension Income", "pension_income"),
    ("Housing", "housing"),
    ("HOA Fees", "hoa_fees"),
    ("Home Insurance", "home_insurance"),
    ("Home Maintenance & Repairs", "home_maintenance"),
    ("Lawn & Garden", "lawn_garden"),
    ("Cleaning Services", "cleaning_services"),
    ("Home Property Taxes", "home_property_tax"),
    ("Rent", "rent"),
    ("Renters Insurance", "renters_insurance"),
    ("Utilities", "utilities"),
    ("Electric", "electric"),
    ("Gas & Heating", "gas_heating"),
    ("Water & Sewer", "water_sewer"),
    ("Internet", "internet"),
    ("Cell Phone", "cell_phone"),
    ("Streaming Services", "streaming"),
    ("Transportation", "transportation"),
    ("Auto Insurance", "auto_insurance"),
    ("Gas & Fuel", "gas_fuel"),
    ("Car Maintenance", "car_maintenance"),
    ("Parking", "parking"),
    ("Rideshare", "rideshare"),
    ("EV Charging", "ev_charging"),
    ("Food & Dining", "food_dining"),
    ("Groceries", "groceries"),
    ("Restaurants & Takeout", "restaurants"),
    ("Coffee Shops", "coffee"),
    ("Food Delivery", "food_delivery"),
    ("Healthcare", "healthcare"),
    ("Health Insurance Premium", "health_insurance"),
    ("Doctor & Medical", "doctor_medical"),
    ("Dental", "dental"),
    ("Vision", "vision"),
    ("Prescriptions & Pharmacy", "pharmacy"),
    ("Fitness & Gym", "fitness"),
    ("Mental Health / Therapy", "therapy"),
    ("Medicare Part B", "medicare_part_b"),
    ("Medicare Part D", "medicare_part_d"),
    ("Medigap Supplement", "medigap_supplement"),
    ("ACA Marketplace Premium", "aca_premium"),
    ("Education & Childcare", "education"),
    ("Tuition & School Fees", "tuition"),
    ("School Supplies & Books", "school_supplies"),
    ("Tutoring & Lessons", "tutoring"),
    ("Childcare & After-School", "childcare"),
    ("Student Activities & Sports", "student_activities"),
    ("Personal & Shopping", "personal"),
    ("Clothing & Apparel", "clothing"),
    ("Personal Care & Beauty", "personal_care"),
    ("Electronics & Technology", "electronics"),
    ("Home Goods & Furnishings", "home_goods"),
    ("Gifts Given", "gifts_given"),
    ("Entertainment & Leisure", "entertainment"),
    ("Events & Tickets", "events_tickets"),
    ("Travel & Vacation", "travel"),
    ("Hobbies & Recreation", "hobbies"),
    ("Pet Care", "pet_care"),
    ("Subscriptions & Memberships", "subscriptions"),
    ("Rental Property Expenses", "property_expenses"),
    ("Rental Property Maintenance", "rental_maintenance"),
    ("Property Management Fees", "property_management"),
    ("Rental Property Insurance", "rental_insurance"),
    ("Rental Property Taxes", "rental_property_tax"),
    ("Business Expenses", "business_expenses"),
    ("Office & Supplies", "office_supplies"),
    ("Professional Development", "professional_dev"),
    ("Professional Services (CPA, Legal)", "professional_services"),
    ("Business Travel", "business_travel"),
    ("Marketing & Software", "marketing_software"),
    ("Financial Services", "financial_services"),
    ("Bank & Account Fees", "bank_fees"),
    ("Investment Advisory Fees", "advisory_fees"),
    ("Tax Preparation", "tax_prep"),
    ("Life & Umbrella Insurance", "life_insurance"),
    ("Transfers", "transfers"),
    ("Credit Card Payment", "cc_payment"),
    ("Auto / Personal Loan Payment", "loan_payment"),
    ("IRA Contribution", "ira_contribution"),
    ("Brokerage Contribution", "brokerage_contribution"),
    ("To / From Savings", "savings_transfer"),
    ("Between Own Accounts", "between_accounts"),
    ("Mortgage Payment", "mortgage_payment"),
    ("HELOC Payment", "heloc_payment"),
    ("RSU Vesting Income", "rsu_vest_income"),
    ("NSO Exercise Income", "nso_exercise_income"),
    ("ESPP Purchase Discount", "espp_purchase"),
    ("Capital Distribution", "capital_distribution"),
    ("CRT Unitrust Income", "crt_income"),
    ("Inherited IRA RMD", "inherited_ira_rmd"),
    ("Qualified Charitable Distribution", "qcd_note"),
    ("Insurance", "insurance"),
    ("Umbrella Liability Premium", "umbrella_premium"),
    ("Disability Insurance Premium", "disability_insurance_premium"),
    ("Long-Term Care Premium", "ltc_insurance_premium"),
    ("Permanent Life Premium", "permanent_life_premium"),
    ("Scheduled / Specialty Premium", "specialty_insurance_premium"),
    ("Interest Expense", "interest_expense"),
    ("SBLOC Interest", "sbloc_interest"),
    ("Margin Interest", "margin_interest"),
    ("Private School Tuition", "private_school_tuition"),
    ("Eldercare & Family Support", "eldercare"),
    ("Equity Sale (Diversification)", "equity_sale"),
    ("Capital Call", "capital_call"),
    ("Capital Distribution (Cash)", "capital_distribution_transfer"),
    ("SBLOC Draw", "sbloc_draw"),
    ("Margin Draw / Paydown", "margin_draw"),
    ("DAF Contribution", "daf_contribution"),
    ("Trust Funding", "trust_funding"),
    ("Gift to ILIT", "gift_to_ilit"),
    ("Annual Exclusion Gift", "annual_exclusion_gift"),
    ("Roth Conversion", "roth_conversion"),
    ("529 Superfunding", "529_superfund"),
]

_PARENT_COLORS = [
    ("income", "#22c55e"),
    ("business_income", "#10b981"),
    ("investment_income", "#3b82f6"),
    ("rental_income", "#f59e0b"),
    ("other_income", "#94a3b8"),
    ("housing", "#3b82f6"),
    ("utilities", "#06b6d4"),
    ("transportation", "#f97316"),
    ("food_dining", "#22c55e"),
    ("healthcare", "#a855f7"),
    ("education", "#0ea5e9"),
    ("personal", "#ec4899"),
    ("entertainment", "#14b8a6"),
    ("property_expenses", "#84cc16"),
    ("business_expenses", "#64748b"),
    ("financial_services", "#6366f1"),
    ("insurance", "#f59e0b"),
    ("interest_expense", "#ef4444"),
    ("eldercare", "#8b5cf6"),
    ("transfers", "#94a3b8"),
]


def upgrade() -> None:
    op.add_column("categories", sa.Column("slug", sa.String(100), nullable=True))

    slug_values = ", ".join(f"('{name}', '{slug}')" for name, slug in _NAME_TO_SLUG)
    op.execute(
        f"""
        WITH slug_map(nm, sl) AS (VALUES {slug_values})
        UPDATE categories c
        SET slug = sm.sl
        FROM slug_map sm
        WHERE c.name = sm.nm AND c.is_system = TRUE
        """
    )

    color_values = ", ".join(f"('{slug}', '{color}')" for slug, color in _PARENT_COLORS)
    op.execute(
        f"""
        WITH color_map(sl, clr) AS (VALUES {color_values})
        UPDATE categories c
        SET color_hex = cm.clr
        FROM color_map cm
        WHERE c.slug = cm.sl AND c.is_system = TRUE AND c.parent_category_id IS NULL
        """
    )

    op.create_index(
        "ix_categories_household_slug",
        "categories",
        ["household_id", "slug"],
        unique=True,
        postgresql_where=sa.text("slug IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_categories_household_slug", table_name="categories")
    op.execute(
        "UPDATE categories SET color_hex = '#888888' WHERE is_system = TRUE AND parent_category_id IS NULL"
    )
    op.drop_column("categories", "slug")
