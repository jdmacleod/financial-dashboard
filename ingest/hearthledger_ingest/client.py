"""Thin HTTP client for pushing canonical rows to the HearthLedger staging API."""

import uuid
from typing import Any

import httpx


class IngestClient:
    """Authenticates with a personal access token (hl_pat_...) and pushes a batch
    to POST /accounts/{id}/import/staging.

    ``http_client`` is injectable so tests can drive the API in-process via an
    ASGI transport; production passes nothing and a real httpx.Client is built.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        http_client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def stage(
        self,
        account_id: str,
        rows: list[dict[str, Any]],
        batch_id: str | None = None,
    ) -> dict[str, Any]:
        # Client-generated batch id so a retry of the same push is idempotent.
        payload: dict[str, Any] = {"batch_id": batch_id or str(uuid.uuid4()), "rows": rows}
        resp = self._client.post(
            f"{self._base_url}/api/v1/accounts/{account_id}/import/staging",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "IngestClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
