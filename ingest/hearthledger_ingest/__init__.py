"""HearthLedger offline ingest CLI.

Parses exported statement documents locally and pushes canonical, deduped rows to
the HearthLedger REST API over a personal access token. Privacy-first: statement
files never leave the machine; only the parsed plaintext fields (date, amount,
payee, memo) are sent, and the SERVER re-redacts PII regardless — the local
redaction here is a UX hint, not the trust boundary.
"""

__version__ = "0.1.0"
