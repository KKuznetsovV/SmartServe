from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import HTTPException

from app.clients import catalog_client, reporting_client
from app.modules.ai.services.report_dispatch import generate_report


async def test_generate_report_sales_defaults_group_by_item(monkeypatch):
    captured = {}

    async def fake_reporting_get(path, *, forward_token=None, **kwargs):
        captured["path"] = path
        captured["params"] = kwargs["params"]
        return httpx.Response(200, json={"rows": [], "totalQty": 0, "totalRevenue": 0.0})

    monkeypatch.setattr(reporting_client, "get", fake_reporting_get)

    result = await generate_report({"report_type": "sales", "start": "2026-01-01", "end": "2026-01-31"}, "loc-1", "tok")

    assert captured["path"] == "/api/v1/locations/loc-1/reports/sales"
    assert captured["params"]["group_by"] == "item"
    assert result["totalQty"] == 0


async def test_generate_report_rejects_unknown_report_type():
    with pytest.raises(HTTPException) as exc_info:
        await generate_report({"report_type": "bogus", "start": "2026-01-01", "end": "2026-01-31"}, "loc-1", "tok")
    assert exc_info.value.status_code == 400


async def test_generate_report_requires_start_and_end():
    with pytest.raises(HTTPException) as exc_info:
        await generate_report({"report_type": "sales"}, "loc-1", "tok")
    assert exc_info.value.status_code == 400


async def test_generate_report_sales_by_server_resolves_item_hint(monkeypatch):
    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        if path.endswith("/stock"):
            return httpx.Response(200, json=[{"id": "item-1", "name": "Burger"}])
        return httpx.Response(200, json=[])

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)

    captured = {}

    async def fake_reporting_get(path, *, forward_token=None, **kwargs):
        captured["params"] = kwargs["params"]
        return httpx.Response(200, json={"rows": []})

    monkeypatch.setattr(reporting_client, "get", fake_reporting_get)

    await generate_report(
        {
            "report_type": "sales_by_server",
            "item_hint": "burger",
            "start": "2026-01-01",
            "end": "2026-01-31",
        },
        "loc-1",
        "tok",
    )

    assert captured["params"]["item_id"] == "item-1"


async def test_generate_report_closed_orders_ignores_invalid_status(monkeypatch):
    captured = {}

    async def fake_reporting_get(path, *, forward_token=None, **kwargs):
        captured["params"] = kwargs["params"]
        return httpx.Response(200, json={"orders": []})

    monkeypatch.setattr(reporting_client, "get", fake_reporting_get)

    await generate_report(
        {"report_type": "closed_orders", "status": "bogus", "start": "2026-01-01", "end": "2026-01-31"},
        "loc-1",
        "tok",
    )

    assert "status" not in captured["params"]


async def test_generate_report_closed_orders_translates_404(monkeypatch):
    async def fake_reporting_get(path, *, forward_token=None, **kwargs):
        request = httpx.Request("GET", "http://reporting/x")
        response = httpx.Response(404, json={"detail": "Location not found"}, request=request)
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    monkeypatch.setattr(reporting_client, "get", fake_reporting_get)

    with pytest.raises(HTTPException) as exc_info:
        await generate_report(
            {"report_type": "closed_orders", "start": "2026-01-01", "end": "2026-01-31"}, "loc-1", "tok"
        )
    assert exc_info.value.status_code == 404


async def test_generate_report_today_before_cutoff_is_previous_business_day(monkeypatch):
    captured = {}

    async def fake_reporting_get(path, *, forward_token=None, **kwargs):
        captured["params"] = kwargs["params"]
        return httpx.Response(200, json={"rows": []})

    monkeypatch.setattr(reporting_client, "get", fake_reporting_get)

    now = datetime(2026, 11, 1, 3, 0, tzinfo=ZoneInfo("Asia/Jerusalem"))
    await generate_report(
        {"report_type": "sales", "start": "today", "end": "today"},
        "loc-1",
        "tok",
        location={"timezone": "Asia/Jerusalem", "businessDayCutoff": "05:00"},
        now=now,
    )
    assert captured["params"]["start_date"] == "2026-10-31"
    assert captured["params"]["end_date"] == "2026-10-31"
