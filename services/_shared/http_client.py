"""Thin httpx.AsyncClient wrapper for service-to-service REST calls.

Base URL comes from an env var per downstream service (e.g. `AUTH_SERVICE_URL`,
`CATALOG_SERVICE_URL`) so each service's location is configured, not hard-coded.
The caller's JWT is forwarded so the downstream service can re-verify the same
identity/authorization locally (see security.py) rather than trusting the caller blindly.
"""

from __future__ import annotations

from typing import Any

import httpx


class ServiceClient:
    """A small REST client scoped to one downstream service base URL."""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def request(
        self,
        method: str,
        path: str,
        *,
        forward_token: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = kwargs.pop("headers", {}) or {}
        if forward_token:
            headers["Authorization"] = f"Bearer {forward_token}"

        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            response = await client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response

    async def get(self, path: str, *, forward_token: str | None = None, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, forward_token=forward_token, **kwargs)

    async def post(self, path: str, *, forward_token: str | None = None, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, forward_token=forward_token, **kwargs)
