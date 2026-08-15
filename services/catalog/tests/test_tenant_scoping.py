"""Cross-business authorization tests for catalog endpoints.

A manager/user from a DIFFERENT business must never be able to reach or modify another
business's categories, items, modifier groups/modifiers, or discounts via a guessed/known
id path param — every such attempt must 404 (not 403, to avoid leaking existence).
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import Business, Location, MenuCategory, MenuItem, ModifierGroup, User


@pytest_asyncio.fixture
async def other_business(db: AsyncSession) -> Business:
    biz = Business(name="Other Restaurant", country="IL", currency="ILS")
    db.add(biz)
    await db.flush()
    return biz


@pytest_asyncio.fixture
async def other_manager(db: AsyncSession, other_business: Business) -> tuple[User, str]:
    user = User(
        business_id=other_business.id,
        email="other-manager@test.com",
        name="Other Manager",
        role="manager",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token


@pytest_asyncio.fixture
async def category(db: AsyncSession, location: Location) -> MenuCategory:
    cat = MenuCategory(location_id=location.id, name="Drinks", sort_order=0)
    db.add(cat)
    await db.flush()
    return cat


@pytest_asyncio.fixture
async def modifier_group(db: AsyncSession, menu_item: MenuItem) -> ModifierGroup:
    group = ModifierGroup(item_id=menu_item.id, name="Size", min_select=0, max_select=1)
    db.add(group)
    await db.flush()
    return group


@pytest.mark.asyncio
async def test_get_category_rejects_other_business(
    client: AsyncClient, category: MenuCategory, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.patch(
        f"/api/v1/menu/categories/{category.id}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_rejects_other_business(
    client: AsyncClient, category: MenuCategory, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.delete(
        f"/api/v1/menu/categories/{category.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_categories_rejects_other_business(
    client: AsyncClient, location: Location, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.get(
        f"/api/v1/menu/locations/{location.id}/categories", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_item_rejects_other_business(
    client: AsyncClient, menu_item: MenuItem, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.get(f"/api/v1/menu/items/{menu_item.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_item_rejects_other_business(
    client: AsyncClient, menu_item: MenuItem, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.patch(
        f"/api/v1/menu/items/{menu_item.id}",
        json={"price": 1.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_item_rejects_other_business(
    client: AsyncClient, menu_item: MenuItem, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.delete(f"/api/v1/menu/items/{menu_item.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_modifier_group_rejects_other_business(
    client: AsyncClient, modifier_group: ModifierGroup, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.patch(
        f"/api/v1/menu/modifier-groups/{modifier_group.id}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_modifier_group_rejects_other_business(
    client: AsyncClient, modifier_group: ModifierGroup, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.delete(
        f"/api/v1/menu/modifier-groups/{modifier_group.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_discount_ignores_client_supplied_business_id(
    client: AsyncClient, owner_user: tuple[User, str], other_business: Business
):
    """A manager must never be able to plant a discount into ANOTHER business by setting
    business_id in the request body — the server must always derive it from the caller."""
    _, token = owner_user
    resp = await client.post(
        "/api/v1/discounts",
        json={
            "businessId": other_business.id,
            "code": "HIJACK10",
            "name": "Hijacked Discount",
            "type": "percent",
            "value": 10,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["businessId"] != other_business.id


@pytest.mark.asyncio
async def test_list_discounts_rejects_other_business(
    client: AsyncClient, business: Business, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.get(
        f"/api/v1/businesses/{business.id}/discounts", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_discount_rejects_other_business(
    client: AsyncClient, owner_user: tuple[User, str], other_manager: tuple[User, str]
):
    _, owner_token = owner_user
    create_resp = await client.post(
        "/api/v1/discounts",
        json={"businessId": "placeholder", "code": "SAVE10", "name": "Save 10", "type": "percent", "value": 10},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    discount_id = create_resp.json()["id"]

    _, other_token = other_manager
    resp = await client.patch(
        f"/api/v1/discounts/{discount_id}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_discount_rejects_other_business(
    client: AsyncClient, owner_user: tuple[User, str], other_manager: tuple[User, str]
):
    _, owner_token = owner_user
    create_resp = await client.post(
        "/api/v1/discounts",
        json={"businessId": "placeholder", "code": "SAVE20", "name": "Save 20", "type": "percent", "value": 20},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    discount_id = create_resp.json()["id"]

    _, other_token = other_manager
    resp = await client.delete(
        f"/api/v1/discounts/{discount_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 404
