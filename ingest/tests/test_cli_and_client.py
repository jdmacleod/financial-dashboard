"""Unit tests for the CLI argument handling and the client (mocked transport)."""

from typing import Any

import httpx

from hearthledger_ingest.cli import run
from hearthledger_ingest.client import IngestClient


def _mock_client(captured: dict[str, Any]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = request.read().decode()
        return httpx.Response(
            201,
            json={
                "batch_id": "11111111-1111-1111-1111-111111111111",
                "staged": 1,
                "skipped_duplicate": 0,
                "failed": 0,
                "errors": [],
            },
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_client_posts_to_staging_with_token() -> None:
    captured: dict[str, Any] = {}
    with IngestClient("http://host", "hl_pat_a.b", http_client=_mock_client(captured)) as client:
        result = client.stage("acct-1", [{"transaction_date": "2026-01-01", "amount": "1.00"}])
    assert result["staged"] == 1
    assert captured["url"].endswith("/api/v1/accounts/acct-1/import/staging")
    assert captured["auth"] == "Bearer hl_pat_a.b"
    assert "batch_id" in captured["body"]


def test_cli_dry_run_parses_without_token(tmp_path: Any, capsys: Any) -> None:
    f = tmp_path / "s.csv"
    f.write_text("Date,Amount,Description\n2026-01-05,-5.00,Bus\n")
    code = run(["--account-id", "a", "--dry-run", str(f)])
    assert code == 0
    assert "Parsed 1 row" in capsys.readouterr().out


def test_cli_requires_token_without_dry_run(tmp_path: Any, capsys: Any) -> None:
    f = tmp_path / "s.csv"
    f.write_text("Date,Amount\n2026-01-05,-5.00\n")
    code = run(["--account-id", "a", str(f)])
    assert code == 2
    assert "token is required" in capsys.readouterr().err


def test_cli_reports_bad_file(tmp_path: Any, capsys: Any) -> None:
    f = tmp_path / "s.pdf"
    f.write_text("nope")
    code = run(["--account-id", "a", "--dry-run", str(f)])
    assert code == 1
    assert "Unsupported file type" in capsys.readouterr().err
