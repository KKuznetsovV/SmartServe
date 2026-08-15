import json
from types import SimpleNamespace

import httpx

from app.clients import auth_client, staff_client
from app.core.config import settings
from app.modules.ai import router as router_module
from app.modules.ai.services.dispatch import dispatch_intent
from app.modules.ai.services.menu_client import MenuClient, PrintingClient
from app.modules.ai.services.staff_client import StaffClient

STAFF = [
    {
        "id": "user-danny",
        "businessId": "biz-1",
        "name": "Danny Cohen",
        "email": "danny@biz1.com",
        "role": "waiter",
        "active": True,
    },
    {
        "id": "user-sarah",
        "businessId": "biz-1",
        "name": "Sarah Levi",
        "email": "sarah@biz1.com",
        "role": "waiter",
        "active": False,
    },
]


class FakeMessage:
    def __init__(self, data):
        self.content = [SimpleNamespace(text=json.dumps(data))]


def _seed_pending(execution_id, intent, params, location_id="loc-1"):
    router_module._pending[execution_id] = {
        "intent": intent,
        "params": params,
        "context": {"locationId": location_id},
    }


# ─── dispatch_intent unit tests ─────────────────────────────────────────────


async def test_dispatch_staff_deactivate_by_name(monkeypatch):
    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        assert path == "/api/v1/businesses/biz-1/staff"
        return httpx.Response(200, json=STAFF)

    patched: dict = {}

    async def fake_staff_patch(path, *, forward_token=None, **kwargs):
        patched["path"] = path
        patched["json"] = kwargs["json"]
        return httpx.Response(200, json={**STAFF[0], "active": False})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)
    monkeypatch.setattr(staff_client, "patch", fake_staff_patch)

    result = await dispatch_intent(
        "staff.deactivate",
        {"staff_hint": "Danny"},
        "loc-1",
        MenuClient("tok"),
        PrintingClient("tok"),
        staff=StaffClient("tok"),
        business_id="biz-1",
    )

    assert "Danny Cohen" in result
    assert patched["path"] == "/api/v1/staff/user-danny"
    assert patched["json"] == {"active": False}


async def test_dispatch_staff_reactivate_by_email(monkeypatch):
    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=STAFF)

    async def fake_staff_patch(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={**STAFF[1], "active": True})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)
    monkeypatch.setattr(staff_client, "patch", fake_staff_patch)

    result = await dispatch_intent(
        "staff.reactivate",
        {"staff_hint": "sarah@biz1.com"},
        "loc-1",
        MenuClient("tok"),
        PrintingClient("tok"),
        staff=StaffClient("tok"),
        business_id="biz-1",
    )

    assert "Reactivated" in result
    assert "Sarah Levi" in result


async def test_dispatch_staff_deactivate_no_match(monkeypatch):
    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=STAFF)

    monkeypatch.setattr(auth_client, "get", fake_auth_get)

    try:
        await dispatch_intent(
            "staff.deactivate",
            {"staff_hint": "Nobody"},
            "loc-1",
            MenuClient("tok"),
            PrintingClient("tok"),
            staff=StaffClient("tok"),
            business_id="biz-1",
        )
        raise AssertionError("expected dispatch_intent to raise")
    except Exception as exc:
        assert "404" in str(exc) or "No staff member" in str(exc)


async def test_dispatch_staff_deactivate_missing_hint():
    try:
        await dispatch_intent(
            "staff.deactivate",
            {},
            "loc-1",
            MenuClient("tok"),
            PrintingClient("tok"),
            staff=StaffClient("tok"),
            business_id="biz-1",
        )
        raise AssertionError("expected dispatch_intent to raise")
    except Exception as exc:
        assert "400" in str(exc) or "Could not determine" in str(exc)


async def test_dispatch_staff_deactivate_cross_business_rejected(monkeypatch):
    # Simulates a misconfigured/compromised downstream response returning a staff member
    # from a DIFFERENT business than the caller's own — dispatch must never trust
    # list_staff() alone and must independently re-check ownership before deactivating
    # anyone, exactly like report generation independently re-verifies location ownership.
    other_business_staff = [
        {"id": "user-other", "businessId": "other-biz", "name": "Danny Impostor", "email": "danny@other.com"}
    ]

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=other_business_staff)

    monkeypatch.setattr(auth_client, "get", fake_auth_get)

    try:
        await dispatch_intent(
            "staff.deactivate",
            {"staff_hint": "Danny"},
            "loc-1",
            MenuClient("tok"),
            PrintingClient("tok"),
            staff=StaffClient("tok"),
            business_id="biz-1",
        )
        raise AssertionError("expected dispatch_intent to raise")
    except Exception as exc:
        assert "404" in str(exc) or "No staff member" in str(exc)


# ─── full classify -> confirm -> dispatch path ─────────────────────────────


async def test_command_then_confirm_staff_deactivate(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        if path == "/api/v1/locations/loc-1":
            return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})
        return httpx.Response(200, json=STAFF)

    async def fake_create_message(client_obj, **kwargs):
        return FakeMessage(
            {
                "intent": "staff.deactivate",
                "confidence": 0.95,
                "params": {"staff_hint": "Danny"},
                "preview": "Deactivate Danny Cohen",
            }
        )

    async def fake_staff_patch(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={**STAFF[0], "active": False})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)
    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)
    monkeypatch.setattr(staff_client, "patch", fake_staff_patch)

    command_resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "Remove Danny from staff", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert command_resp.status_code == 200
    body = command_resp.json()
    assert body["requiresConfirmation"] is True
    execution_id = body["executionId"]

    confirm_resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": execution_id},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert confirm_resp.status_code == 200
    assert "Danny Cohen" in confirm_resp.json()["message"]


async def test_staff_deactivate_requires_confirm_not_bypassed(client, manager_token, monkeypatch):
    # staff.deactivate must NOT take the report.query-style shortcut that skips /confirm —
    # revoking access is a mutation, so /command should only ever return a pending
    # executionId for it, never dispatch immediately.
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    async def fake_create_message(client_obj, **kwargs):
        return FakeMessage(
            {
                "intent": "staff.deactivate",
                "confidence": 0.95,
                "params": {"staff_hint": "Danny"},
                "preview": "Deactivate Danny Cohen",
            }
        )

    monkeypatch.setattr(auth_client, "get", fake_auth_get)
    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "Remove Danny from staff", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["requiresConfirmation"] is True
    assert "executionId" in body
    assert "report" not in body


async def test_confirm_staff_deactivate_requires_manager(client, staff_token):
    _seed_pending("exec-staff-1", "staff.deactivate", {"staff_hint": "Danny"})

    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "exec-staff-1"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403
