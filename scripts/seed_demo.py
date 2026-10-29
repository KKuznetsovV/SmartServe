"""Create demo catalog, floor, printers and discount through the public API.

Expects auth seed to have already created owner@demo.com. Idempotent: skips when
the demo location already has categories.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

GATEWAY = "http://localhost:8080"
OWNER_EMAIL = "owner@demo.com"
OWNER_PASSWORD = "demo1234"

CATEGORIES = [
    {"name": "Starters", "nameHe": "ראשונות", "sortOrder": 0},
    {"name": "Mains", "nameHe": "עיקריות", "sortOrder": 1},
    {"name": "Drinks", "nameHe": "שתייה", "sortOrder": 2},
]
ITEMS = [
    ("Starters", {"name": "Hummus", "nameHe": "חומוס", "price": 28.0}),
    ("Starters", {"name": "Falafel Plate", "nameHe": "פלאפל", "price": 32.0}),
    ("Mains", {"name": "Burger", "nameHe": "המבורגר", "price": 68.0, "preparationTimeMin": 15}),
    ("Mains", {"name": "Schnitzel", "nameHe": "שניצל", "price": 62.0, "preparationTimeMin": 12}),
    ("Mains", {"name": "Salmon Fillet", "nameHe": "פילה סלמון", "price": 94.0, "preparationTimeMin": 18}),
    ("Drinks", {"name": "Cola", "nameHe": "קולה", "price": 12.0, "preparationTimeMin": 1}),
    ("Drinks", {"name": "Lemonade", "nameHe": "לימונדה", "price": 14.0, "preparationTimeMin": 2}),
]


def _request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{GATEWAY}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise SystemExit(f"{method} {path} -> {exc.code}: {detail}") from exc


def main() -> None:
    login = _request("POST", "/api/v1/auth/login", body={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    token = login["accessToken"]
    me = _request("GET", "/api/v1/auth/me", token=token)
    business_id = me["businessId"]
    locations = _request("GET", f"/api/v1/businesses/{business_id}/locations", token=token)
    if not locations:
        raise SystemExit("demo location missing; run python -m app.db.seed in auth first")
    location_id = locations[0]["id"]

    existing = _request("GET", f"/api/v1/menu/locations/{location_id}/categories", token=token)
    if existing:
        print("Demo catalog already present, skipping.")
        return

    categories: dict[str, str] = {}
    for cat in CATEGORIES:
        created = _request(
            "POST",
            "/api/v1/menu/categories",
            token=token,
            body={"locationId": location_id, **cat},
        )
        categories[cat["name"]] = created["id"]

    items_by_name: dict[str, str] = {}
    for category_name, payload in ITEMS:
        created = _request(
            "POST",
            "/api/v1/menu/items",
            token=token,
            body={"categoryId": categories[category_name], **payload},
        )
        items_by_name[payload["name"]] = created["id"]

    _request(
        "POST",
        "/api/v1/menu/modifier-groups",
        token=token,
        body={
            "itemId": items_by_name["Burger"],
            "name": "Doneness",
            "nameHe": "רמת צלייה",
            "required": False,
            "minSelect": 0,
            "maxSelect": 1,
            "modifiers": [
                {"name": "Medium", "nameHe": "מדיום", "priceDelta": 0},
                {"name": "Well done", "nameHe": "עשוי", "priceDelta": 0},
            ],
        },
    )

    for i in range(1, 9):
        _request(
            "POST",
            "/api/v1/tables",
            token=token,
            body={"locationId": location_id, "name": f"T{i}", "capacity": 4},
        )

    kitchen = _request(
        "POST",
        "/api/v1/printers",
        token=token,
        body={"locationId": location_id, "name": "Kitchen", "type": "kitchen"},
    )
    bar = _request(
        "POST",
        "/api/v1/printers",
        token=token,
        body={"locationId": location_id, "name": "Bar", "type": "receipt"},
    )
    for name in ("Hummus", "Falafel Plate", "Burger", "Schnitzel", "Salmon Fillet"):
        _request(
            "POST",
            "/api/v1/printer-routes",
            token=token,
            body={"printerId": kitchen["id"], "itemId": items_by_name[name]},
        )
    for name in ("Cola", "Lemonade"):
        _request(
            "POST",
            "/api/v1/printer-routes",
            token=token,
            body={"printerId": bar["id"], "itemId": items_by_name[name]},
        )

    _request(
        "POST",
        "/api/v1/discounts",
        token=token,
        body={"businessId": business_id, "code": "HAPPY10", "name": "Happy hour 10%", "type": "percent", "value": 10},
    )
    print("Demo catalog, tables, printers and HAPPY10 seeded.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
