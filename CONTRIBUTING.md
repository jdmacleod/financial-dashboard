# Contributing to HearthLedger

Thanks for working on HearthLedger. This guide covers local development setup,
the pre-commit hooks every clone should install, and how to run the test suites.

For running the app itself (Docker stack, `.env`, seeding demo data), see
[docs/getting-started.md](docs/getting-started.md) and
[docs/demo-quickstart.md](docs/demo-quickstart.md).

---

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node 26 and npm
- [pre-commit](https://pre-commit.com/) (`uv tool install pre-commit`, or
  `pipx install pre-commit`)

## 1. Install dependencies

```bash
# Backend
cd backend && uv sync

# Frontend
cd frontend && npm install
```

## 2. Install the pre-commit hooks (required)

The repository ships a `.pre-commit-config.yaml` that runs the same lint,
format, type-check, and secret-detection checks as CI. **Every clone must
install the hooks once** so commits are checked locally before they reach CI:

```bash
pre-commit install
```

`default_install_hook_types` in the config is `[pre-commit, commit-msg]`, so a
single `pre-commit install` wires up both the file checks (on `git commit`) and
[Conventional Commits](https://www.conventionalcommits.org/) message linting (on
the commit message). You do **not** need to pass `-t commit-msg` separately.

What the hooks enforce on every commit:

| Hook               | Scope    | Checks                                        |
| ------------------ | -------- | --------------------------------------------- |
| ruff / ruff-format | backend  | lint + format Python                          |
| mypy `--strict`    | backend  | static types on `backend/app/`                |
| tsc `--noEmit`     | frontend | TypeScript type-check                         |
| eslint             | frontend | lint                                          |
| prettier `--check` | repo     | formatting                                    |
| detect-secrets     | repo     | no secrets committed (`.secrets.baseline`)    |
| commitlint         | message  | Conventional Commits, header ≤ 100 characters |

To run every hook across the whole repo without committing:

```bash
pre-commit run --all-files
```

## 3. (Optional) Install the pre-push test hook

The config also defines opt-in hooks that run the **full backend and frontend
test suites** before each `git push`. They are inert until you explicitly
install the `pre-push` hook type:

```bash
pre-commit install -t pre-push
```

Once installed, `git push` runs `pytest` (backend) and `vitest` (frontend) and
aborts the push if either suite fails. This is opt-in because the suites take
longer than a typical commit check; CI runs them regardless. To skip them for a
single push (e.g. a docs-only branch): `git push --no-verify`.

## Running tests manually

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npx vitest run
```

## Before opening a PR

- `pre-commit run --all-files` is clean.
- Both test suites pass.
- New DB columns have a reversible Alembic migration.
- New API endpoints have Pydantic request/response schemas and integration tests.

See the **Design review checklist** in [CLAUDE.md](CLAUDE.md) for the full list
of architectural constraints (account-visibility routing, `@audit` on mutations,
append-only audit log, no plaintext PII, `TIMESTAMPTZ`, no `float` for money).
