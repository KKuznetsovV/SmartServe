from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_manager
from app.api.v1.router_base import APIRouter
from app.db.models import User
from app.db.session import get_db
from app.schemas.menu import (
    BulkPriceUpdate,
    MenuCategoryCreate,
    MenuCategoryOut,
    MenuCategoryUpdate,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    ModifierCreate,
    ModifierGroupCreate,
    ModifierGroupOut,
    ModifierGroupUpdate,
    ModifierOut,
    StockUpdate,
)
from app.services.menu import MenuService

router = APIRouter()


# ── Categories ────────────────────────────────────────────────────────────────


@router.get("/locations/{location_id}/categories", response_model=list[MenuCategoryOut])
async def list_categories(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await MenuService(db).list_categories(location_id)


@router.post("/categories", response_model=MenuCategoryOut, status_code=201)
async def create_category(
    data: MenuCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await MenuService(db).create_category(data)


@router.patch("/categories/{category_id}", response_model=MenuCategoryOut)
async def update_category(
    category_id: str,
    data: MenuCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await MenuService(db).update_category(category_id, data)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    await MenuService(db).delete_category(category_id)


@router.post("/locations/{location_id}/categories/reorder", status_code=204)
async def reorder_categories(
    location_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    await MenuService(db).reorder_categories(location_id, body["ids"])


# ── Items ─────────────────────────────────────────────────────────────────────


@router.get("/categories/{category_id}/items", response_model=list[MenuItemOut])
async def list_items(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await MenuService(db).list_items(category_id)


@router.get("/items/{item_id}", response_model=MenuItemOut)
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await MenuService(db).get_item(item_id)


@router.post("/items", response_model=MenuItemOut, status_code=201)
async def create_item(
    data: MenuItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await MenuService(db).create_item(data)


@router.patch("/items/{item_id}", response_model=MenuItemOut)
async def update_item(
    item_id: str,
    data: MenuItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await MenuService(db).update_item(item_id, data)


@router.patch("/items/{item_id}/stock", response_model=MenuItemOut)
async def set_item_stock(
    item_id: str,
    data: StockUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await MenuService(db).set_stock(item_id, data.in_stock)


@router.get("/locations/{location_id}/stock", response_model=list[MenuItemOut])
async def list_location_stock(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await MenuService(db).list_all_items(location_id)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    await MenuService(db).delete_item(item_id)


@router.post("/items/bulk-price", response_model=dict)
async def bulk_price_update(
    data: BulkPriceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    count = await MenuService(db).bulk_price_update(data)
    return {"updated": count}


# ── Modifier Groups ───────────────────────────────────────────────────────────


@router.post("/modifier-groups", response_model=ModifierGroupOut, status_code=201)
async def create_modifier_group(
    data: ModifierGroupCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await MenuService(db).create_modifier_group(data)


@router.patch("/modifier-groups/{group_id}", response_model=ModifierGroupOut)
async def update_modifier_group(
    group_id: str,
    data: ModifierGroupUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await MenuService(db).update_modifier_group(group_id, data)


@router.delete("/modifier-groups/{group_id}", status_code=204)
async def delete_modifier_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    await MenuService(db).delete_modifier_group(group_id)


@router.post("/modifier-groups/{group_id}/modifiers", response_model=ModifierOut, status_code=201)
async def add_modifier(
    group_id: str,
    data: ModifierCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await MenuService(db).add_modifier(group_id, data)


@router.delete("/modifiers/{modifier_id}", status_code=204)
async def delete_modifier(
    modifier_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    await MenuService(db).delete_modifier(modifier_id)
