# Phase 6 — Polish

Implements the backup service UI, real estate valuation management,
dashboard customization, and import history. These features refine the
system after core functionality is complete and verified.

## Status

**Complete** — v0.6.0.0 — 2026-06-18

---

## Deliverables

- [x] Settings > Backups page (history, manual trigger, download)
- [x] Real estate valuation provider configuration in Settings
- [x] Manual valuation entry on property detail page
- [x] Backup ARQ task registered and scheduled
- [x] Valuation refresh ARQ task registered and scheduled
- [x] Dashboard widget layout persistence
- [x] Dark mode (Tailwind `dark:` classes throughout)
- [x] Import history page

---

## Backup service

### ARQ task

```python
# backend/app/worker/tasks/backup_tasks.py

import subprocess, os, shutil
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import settings
from app.core.encryption import encrypt_file

async def run_backup(ctx) -> None:
    started_at = datetime.now(timezone.utc)
    ts = started_at.strftime("%Y-%m-%dT%H-%M-%SZ")  # colons → hyphens
    filename = f"hearthledger_backup_{ts}.dump.enc"
    tmp_path = Path(f"/tmp/hearthledger_dump_{ts}.pgdump")
    out_path = Path(settings.backup_path) / filename

    job = await create_backup_job(triggered_by="scheduled", started_at=started_at)

    try:
        # 1. pg_dump
        subprocess.run(
            ["pg_dump", "--format=custom", "--file", str(tmp_path),
             settings.database_url.replace("+asyncpg", "")],
            check=True, capture_output=True,
        )

        # 2. Encrypt
        encrypt_file(tmp_path, out_path)  # AES-256-GCM, key from settings

        # 3. Verify
        decrypt_file_to_devnull(out_path)  # raises on failure

        # 4. Prune
        prune_old_backups(settings.backup_path, settings.backup_retention_days)

        file_size = out_path.stat().st_size
        await complete_backup_job(job, filename=filename, file_size_bytes=file_size)
        await audit_repo.write(action="backup.completed", ...)

    except Exception as e:
        await fail_backup_job(job, error_message=str(e))
        await audit_repo.write(action="backup.failed", ...)
    finally:
        tmp_path.unlink(missing_ok=True)


def prune_old_backups(backup_path: str, retention_days: int) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
    for f in Path(backup_path).glob("hearthledger_backup_*.dump.enc"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
```

`encrypt_file` and `decrypt_file_to_devnull` use the same AES-256-GCM
key as field encryption (`SECRET_ENCRYPTION_KEY`), applied to the file
as a stream (chunk by chunk to handle large dumps).

### APScheduler wiring (inside ARQ worker startup)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

async def startup(ctx):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: arq_pool.enqueue_job("run_backup"),
        CronTrigger.from_crontab(settings.backup_schedule),
    )
    scheduler.add_job(
        lambda: arq_pool.enqueue_job("refresh_valuations"),
        CronTrigger.from_crontab(settings.re_valuation_refresh_schedule),
    )
    scheduler.start()
    ctx["scheduler"] = scheduler
```

### API endpoints

```
GET  /api/v1/backups              list backup_jobs (requires: primary)
POST /api/v1/backups              trigger manual backup (requires: primary)
GET  /api/v1/backups/{id}/download  streams encrypted .dump.enc file
```

Download streams the raw encrypted file. The user is responsible for
decryption. `SETUP.md` documents the restore procedure.

### Frontend: Settings > Backups

- Summary bar: "Last backup: Jan 15, 2025 at 2:00am · 4.2 MB · Successful"
  or "Warning: No successful backup in 48 hours" (amber alert banner).
- "Run backup now" button → POST → shows spinner → updates status.
- Table: timestamp, trigger (Scheduled / Manual), status badge, size, Download button.
- Retention notice: "Keeping backups for 30 days. Oldest: Dec 16, 2024."
- "How to restore" collapsible with CLI instructions copied from SETUP.md.

---

## Real estate valuation

### Valuation refresh ARQ task

```python
async def refresh_valuations(ctx) -> None:
    provider = get_valuation_provider(settings.re_valuation_provider)
    properties = await get_all_active_properties()
    for prop in properties:
        try:
            address = decrypt(prop.address_enc)
            result = await provider.get_estimate(address)
            await create_property_valuation(prop.id, result)
        except Exception as e:
            # Log warning; fall back silently to last known value
            logger.warning(f"Valuation refresh failed for {prop.id}: {e}")
```

### Provider configuration in Settings

Settings > Properties panel:

- "Valuation provider" selector: Manual (default), ATTOM Data, Estated
- When non-manual selected: API key input field
- "Test connection" button → calls provider with a dummy address → shows success/error
- "Last refresh" timestamp and status per property

Changing the provider writes the new values to `.env` (via a settings
endpoint that updates the running config). Requires container restart to
take effect — UI shows notice: "Restart required for provider change to take effect."

Note: `.env` update endpoint writes only `RE_VALUATION_PROVIDER` and
`RE_VALUATION_API_KEY`. It does not expose or modify any other env vars.

### Property detail: manual valuation entry

On property detail page > Valuation tab:

- Current value card with source badge ("Manual · Jan 10" or "ATTOM · Jan 14")
  and confidence score if available ("Confidence: 87%")
- "Update manually" button → modal with date picker and value input →
  creates a `property_valuations` row with `source: manual`
- Valuation history chart (line) with source color-coding
  (manual = gray dots, API = colored dots)

---

## Dashboard customization

Users can reorder and hide dashboard widgets. Preference stored in
`household_members.settings` JSONB (per-member, not household-wide).

Widgets:

- Net worth summary card
- Cash flow MTD card
- Spending by category donut
- Budget alerts list
- Account balances list
- Recent transactions list

`PATCH /api/v1/members/{id}/dashboard-layout`

```json
{
  "widgets": [
    { "id": "net_worth", "visible": true, "order": 0 },
    { "id": "cash_flow", "visible": true, "order": 1 },
    { "id": "spending_category", "visible": true, "order": 2 },
    { "id": "budget_alerts", "visible": false, "order": 3 },
    { "id": "account_balances", "visible": true, "order": 4 },
    { "id": "recent_transactions", "visible": true, "order": 5 }
  ]
}
```

Frontend: drag-and-drop widget reordering (using `@dnd-kit/core`). Eye icon
to toggle visibility. "Reset to default" button.

---

## Dark mode

Tailwind `dark:` class implementation. No new API work — purely frontend.

- `tailwind.config.ts`: `darkMode: 'class'`
- Toggle stored in localStorage as `theme: 'light' | 'dark' | 'system'`
- `system` follows `prefers-color-scheme` media query
- `<html>` element gets `class="dark"` when dark mode active
- All components use semantic color pairs: `text-gray-900 dark:text-gray-100` etc.
- Charts (Recharts): pass theme-aware colors from a `useThemeColors()` hook

Settings > Appearance: Light / Dark / System toggle.

---

## Import history

`/settings/imports` — table of all import jobs:

- Date, account nickname, filename, format badge (CSV/OFX/QFX),
  status badge, records imported / skipped, triggered by.
- Filterable by account and date range.
- Failed imports show error message in expandable row.

No new API work — uses existing `GET /api/v1/import-jobs` endpoint.

---

## Acceptance criteria

1. `POST /api/v1/backups` triggers an ARQ task that produces an encrypted
   `.dump.enc` file in the backup volume within 60 seconds on a small DB.
2. The backup file decrypts correctly using the documented restore CLI command.
3. Backups older than `BACKUP_RETENTION_DAYS` are pruned after each run.
4. The backup download endpoint streams the correct file with
   `Content-Type: application/octet-stream`.
5. Settings > Backups shows an amber warning banner when the last successful
   backup is > 48 hours ago.
6. A valuation refresh task runs on schedule and creates new
   `property_valuations` rows without overwriting manual entries.
7. When the valuation provider API call fails, the last known value is
   used in net worth calculations without raising an error to the user
   (warning logged only).
8. Dashboard widget order persists across page reloads for each member independently.
9. Dark mode toggle in Settings > Appearance toggles the `dark` class on
   `<html>` and all charts re-render with dark-appropriate colors.
10. Import history page lists all past import jobs with correct status and counts.
