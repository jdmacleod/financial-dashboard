# Phase 2 — Transactions and Imports

Implements transaction CRUD, category management, CSV/OFX/QFX file import
with duplicate detection, and import job tracking.

---

## Status

**Complete** — v0.2.0.0 — 2026-06-18

---

## Deliverables

- [ ] Transaction CRUD endpoints
- [ ] Category CRUD (system categories non-deletable)
- [ ] Manual balance snapshot CRUD
- [ ] CSV import with interactive column mapping
- [ ] OFX/QFX import (auto-mapped fields)
- [ ] Duplicate detection (by `external_id` and amount+date+payee fuzzy match)
- [ ] Transfer detection and pairing
- [ ] Import job status polling endpoint
- [ ] ARQ import tasks registered in worker
- [ ] Property tag on transactions (Amendment 3)
- [ ] Frontend: transaction list, import flow, category management

---

## Transaction service

All mutations go through `TransactionService` and are decorated with `@audit`.

### Duplicate detection

On import, a transaction is considered a duplicate and skipped (counted in
`records_skipped`) if:

1. **Exact match** (primary check): `external_id` matches an existing row
   on the same account.
2. **Fuzzy match** (secondary check, only if no `external_id`): same account,
   same `transaction_date`, same `amount`, and `payee_raw` similarity > 80%
   (use Python `difflib.SequenceMatcher`).

Skipped duplicates are logged in the import job's `records_skipped` count
but do not produce an error.

### Transfer detection

After import, run transfer detection on all transactions in the import batch:

A pair of transactions is treated as a transfer when:

- They are in different accounts within the same household
- One is a debit (negative amount), one is a credit (positive amount)
- `abs(amount_a) == abs(amount_b)`
- `transaction_date` differs by at most 3 days

When a pair is detected:

- Set `is_transfer = TRUE` on both
- Set `transfer_pair_id` to the same new UUID on both
- Assign to a "Transfer" system category (seeded in Phase 0)

Transfers are excluded from income/expense totals in all reports.

---

## CSV importer

### Column mapping UI

CSV import is a two-step process:

**Step 1 — Upload and preview.** The frontend sends the CSV file to
`POST /api/v1/accounts/{id}/import/preview`. The backend parses the first
10 rows and returns:

```json
{
  "headers": ["Date", "Amount", "Description", "Balance"],
  "preview_rows": [["2025-01-15", "-84.23", "WHOLEFDS #123", "1204.56"]],
  "suggested_mapping": {
    "transaction_date": "Date",
    "amount": "Amount",
    "payee_raw": "Description"
  }
}
```

Suggested mapping uses fuzzy header name matching (case-insensitive substring
match against known field names: date, amount, debit, credit, description,
payee, memo, balance, id, reference).

**Step 2 — Confirm mapping and submit.** The frontend renders a mapping form
(one dropdown per required field). On confirm, `POST /api/v1/accounts/{id}/import`
is called with the mapping and file, which enqueues an ARQ import job and
returns the `import_job_id`.

### Required fields (must be mapped)

- `transaction_date` — parsed with `dateutil.parser.parse`
- `amount` — parsed as Decimal; handles parentheses for negatives, removes `$`

### Optional fields

- `payee_raw`
- `memo`
- `post_date`
- `external_id`

### Debit/credit split columns

Some bank exports have separate Debit and Credit columns instead of a signed
Amount. If the user maps both `debit_amount` and `credit_amount`, the importer
combines them: `amount = credit - debit` (both are positive in the CSV).

---

## OFX / QFX importer

Uses `ofxparse`. Field mapping is automatic:

| OFX field  | transactions column |
| ---------- | ------------------- |
| `DTPOSTED` | `post_date`         |
| `DTUSER`   | `transaction_date`  |
| `TRNAMT`   | `amount`            |
| `NAME`     | `payee_raw`         |
| `MEMO`     | `memo`              |
| `FITID`    | `external_id`       |

No column mapping UI required for OFX/QFX. Go straight to confirmation
("Import N transactions from [filename]?") then enqueue.

---

## Import job tracking

`GET /api/v1/import-jobs/{id}` — poll for status.

Frontend polls every 2 seconds while `status == 'processing'`.
On `complete`, shows summary: "Imported 47 transactions. 3 duplicates skipped."
On `failed`, shows `error_message`.

---

## API endpoints — Phase 2

### Transactions

```
GET    /api/v1/accounts/{id}/transactions
  query params: from, to, category_id, is_reviewed, is_transfer,
                real_estate_property_id, search (payee substring),
                page, page_size (default 50)
  response: paginated list

POST   /api/v1/accounts/{id}/transactions
  body: {transaction_date, amount, payee_normalized, memo?,
         category_id?, is_transfer?, real_estate_property_id?}

GET    /api/v1/transactions/{id}
PATCH  /api/v1/transactions/{id}
  audited fields: category_id, amount, payee_normalized,
                  is_transfer, real_estate_property_id
DELETE /api/v1/transactions/{id}

PATCH  /api/v1/accounts/{id}/transactions/bulk-categorize
  body: {transaction_ids: [uuid], category_id: uuid}
  Sets category on all listed transactions in one operation.
  Emits one audit event per transaction.
```

### Categories

```
GET    /api/v1/categories              all categories for household
POST   /api/v1/categories              requires: primary or partner
PATCH  /api/v1/categories/{id}        non-system categories only
DELETE /api/v1/categories/{id}        non-system categories only
                                       reassigns transactions to Uncategorized
```

### Snapshots

```
GET    /api/v1/accounts/{id}/snapshots
POST   /api/v1/accounts/{id}/snapshots
  body: {snapshot_date, balance, contributed_ytd?, employer_match_ytd?, memo?}
PATCH  /api/v1/accounts/{id}/snapshots/{sid}
DELETE /api/v1/accounts/{id}/snapshots/{sid}
```

### Import

```
POST   /api/v1/accounts/{id}/import/preview    returns headers + suggested mapping
POST   /api/v1/accounts/{id}/import            enqueues job; returns import_job_id
GET    /api/v1/import-jobs/{id}               poll status
GET    /api/v1/import-jobs                    list recent jobs for household
```

---

## Frontend — Phase 2 pages

### `/accounts/{id}/transactions`

Transaction list with:

- Date, payee, amount (color-coded: green credit / red debit), category badge
- Property tag badge (if set)
- "Unreviewed" filter chip (shows only `is_reviewed = false`)
- Inline category selector — clicking a category badge opens a dropdown;
  saving immediately PATCH-es the transaction and marks `is_reviewed = true`
- Bulk select (checkbox per row) with "Categorize selected" action
- "Import" button in header

### Import flow (modal)

Step 1: File picker (accept .csv, .ofx, .qfx)
Step 2 (CSV only): Column mapping form with preview rows
Step 3: Confirmation screen ("Import N transactions")
Step 4: Progress indicator (polling import job); completion summary

### `/categories`

Category tree (income / expense groups). Add / rename / delete (non-system).
Color picker and icon selector per category.

---

## Acceptance criteria

1. Importing a sample Chase CSV (include in `tests/fixtures/`) results in
   correct `records_imported`, correct amounts (signs), correct dates.
2. Importing the same CSV a second time results in `records_skipped == N`
   (all duplicates detected by `external_id`).
3. Importing a sample OFX file maps all fields correctly without column
   mapping UI.
4. A pair of transfer transactions (same amount, opposite signs, within 3 days,
   different accounts in same household) are auto-detected and linked.
5. `PATCH /api/v1/transactions/{id}` with `category_id` change writes a
   `transaction.category_changed` audit event with correct prev/new values.
6. `DELETE /api/v1/categories/{id}` on a system category returns 409.
7. `DELETE /api/v1/categories/{id}` on a user category with transactions
   reassigns those transactions to Uncategorized before deleting.
8. A `dependent` user calling `POST /api/v1/accounts/{id}/transactions`
   returns 403.
9. Transactions with `real_estate_property_id` set return the field in
   the response and are filterable by it.
10. Import job status endpoint returns `complete` with correct counts
    after the ARQ task finishes.
