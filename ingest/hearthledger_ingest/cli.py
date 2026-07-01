"""`hearthledger-ingest` command-line entry point.

Example:
    hearthledger-ingest \\
        --api-url http://localhost \\
        --token hl_pat_abc.def \\
        --account-id 00000000-0000-0000-0000-000000000000 \\
        statement.csv

The token can also come from the HEARTHLEDGER_TOKEN env var.
"""

import argparse
import os
import sys
from pathlib import Path

import httpx

from hearthledger_ingest.client import IngestClient
from hearthledger_ingest.parsers import parse_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hearthledger-ingest",
        description="Parse an exported statement and push rows to HearthLedger for review.",
    )
    parser.add_argument("file", help="Path to a .csv or .json statement export")
    parser.add_argument("--account-id", required=True, help="Target HearthLedger account UUID")
    parser.add_argument(
        "--api-url", default=os.environ.get("HEARTHLEDGER_API_URL", "http://localhost")
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("HEARTHLEDGER_TOKEN"),
        help="Personal access token (hl_pat_...). Falls back to HEARTHLEDGER_TOKEN.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print the row count without pushing.",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.token and not args.dry_run:
        print("error: a token is required (use --token or HEARTHLEDGER_TOKEN)", file=sys.stderr)
        return 2

    path = Path(args.file)
    try:
        content = path.read_bytes()
        rows = parse_file(str(path), content)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Parsed {len(rows)} row(s) from {path.name}")
    if args.dry_run:
        return 0

    try:
        with IngestClient(args.api_url, args.token) as client:
            result = client.stage(args.account_id, rows)
    except httpx.HTTPError as exc:
        print(f"error: push failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Staged {result['staged']}, skipped {result['skipped_duplicate']} duplicate(s), "
        f"{result['failed']} failed. Batch {result['batch_id']} — review and promote in the app."
    )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
