"""HTTP-backed client for services/reporting's read-only report endpoints — ai owns no DB
(see docs/microservices-plan.md §4), so report.query answers come straight from
`reporting`'s own tenant-scoped queries rather than any local aggregation.
"""

from typing import Any

from app.clients import reporting_client


class ReportingClient:
    def __init__(self, token: str):
        self._token = token

    async def sales(self, location_id: str, *, group_by: str, start_date: str, end_date: str) -> dict[str, Any]:
        resp = await reporting_client.get(
            f"/api/v1/locations/{location_id}/reports/sales",
            params={"group_by": group_by, "start_date": start_date, "end_date": end_date},
            forward_token=self._token,
        )
        return resp.json()

    async def sales_by_server(
        self,
        location_id: str,
        *,
        start_date: str,
        end_date: str,
        item_id: str | None = None,
        category_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {"start_date": start_date, "end_date": end_date}
        if item_id:
            params["item_id"] = item_id
        if category_id:
            params["category_id"] = category_id
        resp = await reporting_client.get(
            f"/api/v1/locations/{location_id}/reports/sales-by-server",
            params=params,
            forward_token=self._token,
        )
        return resp.json()

    async def closed_orders(
        self, location_id: str, *, start_date: str, end_date: str, status_filter: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, str] = {"start_date": start_date, "end_date": end_date}
        if status_filter:
            params["status"] = status_filter
        resp = await reporting_client.get(
            f"/api/v1/locations/{location_id}/reports/closed-orders",
            params=params,
            forward_token=self._token,
        )
        return resp.json()
