# How to add accounts to HearthLedger

Add any account type (checking, credit card, retirement, investment, real
estate, or loan) using the category-aware "+" buttons on the Accounts page.

## Prerequisites

- HearthLedger running at `http://localhost`
- Logged in as Primary or Partner member

## Overview

The Accounts page organizes accounts into five category groups. Each group's
"+" button routes you to the right place:

| Category       | "+" action                          | Account types                                                                                       |
| -------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------- |
| Banking & Cash | Opens an add form                   | `checking`, `savings`, `other_asset`                                                                |
| Liabilities    | Opens an add form                   | `credit_card`, `mortgage`, `auto_loan`, `personal_loan`, `student_loan`, `heloc`, `other_liability` |
| Retirement     | Takes you to the Retirement report  | `retirement_401k`, `retirement_403b`, `retirement_ira`, `retirement_roth_ira`, `hsa`, `pension`     |
| Investments    | Takes you to the Investments report | `investment_brokerage`                                                                              |
| Real estate    | Takes you to the Assets page        | `real_estate`                                                                                       |

The page header also has a **+ Add account** button: it opens the same add
form as Banking & Cash / Liabilities, but with no pre-filtering.

---

## Adding a Banking & Cash account

1. Go to **Accounts** in the sidebar.
2. Click **+** on the **Banking & Cash** group.
3. Fill in the form:

   | Field               | Notes                                                       |
   | ------------------- | ----------------------------------------------------------- |
   | **Nickname**        | e.g. "Chase Checking"                                       |
   | **Type**            | `checking`, `savings`, or `other_asset`                     |
   | **Current balance** | Optional: the account opens with this balance instead of $0 |
   | **Institution**     | e.g. "Chase Bank": stored encrypted                         |
   | **Account number**  | Optional: stored encrypted                                  |

4. Click **Save**.

The account appears in the Banking & Cash group immediately. If you set a
current balance it opens with that figure (recorded as an opening entry that is
excluded from Cash Flow and Spending reports); otherwise it starts at $0.00.
Import a CSV or OFX/QFX file to populate transactions.

---

## Adding a Liability account

Liabilities include credit cards, mortgages, auto loans, student loans, and
HELOCs. All share the same add form.

1. Go to **Accounts** in the sidebar.
2. Click **+** on the **Liabilities** group.
3. Fill in the form:

   | Field              | Notes                                                                                                  |
   | ------------------ | ------------------------------------------------------------------------------------------------------ |
   | **Nickname**       | e.g. "Chase Sapphire" or "Primary Mortgage"                                                            |
   | **Type**           | `credit_card`, `mortgage`, `auto_loan`, `personal_loan`, `student_loan`, `heloc`, or `other_liability` |
   | **Balance owed**   | Optional: the amount currently owed. The account opens at this balance (stored as a negative)          |
   | **Institution**    | Lender or card issuer: stored encrypted                                                                |
   | **Account number** | Optional: stored encrypted                                                                             |

4. Click **Save**.

The account appears in the Liabilities group. Balances display as negative
numbers (money owed). If you entered a balance owed, it shows immediately
(recorded as an opening entry that stays out of Cash Flow and Spending reports);
otherwise the balance fills in as you import transactions. Setting the balance
owed on a mortgage also lets its equity show against a linked property right
away.

> **HELOC:** A home equity line of credit is a revolving credit line secured
> by your home's equity. Use type `heloc`. The drawn balance appears as a
> liability (negative), while the available credit is not tracked separately.

---

## Adding a Retirement account

Retirement accounts (401k, IRA, HSA, pension) are tracked on the Retirement
report page, not via transaction import.

1. Go to **Accounts** in the sidebar.
2. Click **+** on the **Retirement** group.

   You are navigated to **Reports → Retirement**.

3. Use the form there to add the account and record an initial balance snapshot.

For pension accounts specifically, see the [Pension accounts](user-guide.md#pension-accounts) section of the User Guide.

---

## Adding an Investment account

1. Go to **Accounts** in the sidebar.
2. Click **+** on the **Investments** group.

   You are navigated to **Reports → Investments**.

3. Use the form there to add the account (type `investment_brokerage`) and
   record a balance snapshot.

---

## Adding a Real estate account

1. Go to **Accounts** in the sidebar.
2. Click **+** on the **Real estate** group.

   You are navigated to the **Assets** page.

3. Use the **Add property** form to enter the address and current estimated value.

---

## Verification

After adding any account, confirm it appears in the correct category group on
the Accounts page. Banking & Cash and Liability accounts show the starting
balance you entered on the form, or $0.00 until transactions are imported if you
left it blank. Retirement, investment, and real estate accounts show the balance
from the first snapshot you recorded.

---

## Troubleshooting

**The "+" button is missing on a category group.**
Partner members need an access grant from the Primary member to create accounts.
If you're logged in as a Partner and don't see the "+", ask the Primary member
to grant you access.

**I used the header button and can't find my account type.**
The header **+ Add account** button shows only transaction account types
(Banking & Cash and Liabilities). For retirement, investment, and real estate
types, use the per-category "+" button: it navigates to the correct page.

**My account shows $0.00 balance after adding.**
If you left the balance field blank, that's expected — set a current balance (or
balance owed) on the add form to open the account with a figure. Otherwise, for
Banking & Cash and Liability accounts, import a transaction file (CSV or
OFX/QFX) from the account's transaction page. For retirement, investment, and
real estate accounts, record a balance snapshot from the Assets or Reports page.
