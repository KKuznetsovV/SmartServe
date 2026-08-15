"""HTTP-backed client for staff lookups/mutations — mirrors MenuClient's shape (see
menu_client.py). Unlike MenuClient, this one spans two downstream services: staff
LISTING lives on `auth` (owns the `users` table's business scoping — see
business_router.py's `list_staff`), while staff MUTATION (activate/deactivate) lives
on `staff` (owns write access to the same shared table, see staff/router.py's
`update_staff`).
"""

from typing import Any

from app.clients import auth_client, staff_client


class StaffClient:
    def __init__(self, token: str):
        self._token = token

    async def list_staff(self, business_id: str) -> list[dict[str, Any]]:
        resp = await auth_client.get(f"/api/v1/businesses/{business_id}/staff", forward_token=self._token)
        return resp.json()

    async def set_active(self, user_id: str, active: bool) -> dict[str, Any]:
        resp = await staff_client.patch(f"/api/v1/staff/{user_id}", json={"active": active}, forward_token=self._token)
        return resp.json()
