from fastapi import Depends, Request
from smartserve_shared import mq
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import get_current_user, require_manager
from app.db.models import User
from app.db.session import DbSession
from app.modules.catalog.schemas import (
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
from app.modules.catalog.service import MenuService

router = APIRouter()


# ── Categories ────────────────────────────────────────────────────────────────


@router.get("/locations/{location_id}/categories", response_model=list[MenuCategoryOut])
async def list_categories(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return await MenuService(db).list_categories(location_id, current_user.business_id)


@router.post("/categories", response_model=MenuCategoryOut, status_code=201)
async def create_category(
    data: MenuCategoryCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await MenuService(db).create_category(data, current_user.business_id)


@router.patch("/categories/{category_id}", response_model=MenuCategoryOut)
async def update_category(
    category_id: str,
    data: MenuCategoryUpdate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await MenuService(db).update_category(category_id, data, current_user.business_id)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await MenuService(db).delete_category(category_id, current_user.business_id)


@router.post("/locations/{location_id}/categories/reorder", status_code=204)
async def reorder_categories(
    location_id: str,
    body: dict,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await MenuService(db).reorder_categories(location_id, body["ids"], current_user.business_id)


# ── Items ─────────────────────────────────────────────────────────────────────


@router.get("/categories/{category_id}/items", response_model=list[MenuItemOut])
async def list_items(
    category_id: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return await MenuService(db).list_items(category_id, current_user.business_id)


@router.get("/items/{item_id}", response_model=MenuItemOut)
async def get_item(
    item_id: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return await MenuService(db).get_item(item_id, current_user.business_id)


@router.post("/items", response_model=MenuItemOut, status_code=201)
async def create_item(
    data: MenuItemCreate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    item = await MenuService(db).create_item(data, current_user.business_id)
    location_id = await MenuService(db).get_item_location_id(item)
    await mq.publish(
        request.app.state.mq_connection,
        "catalog.item_updated",
        {
            "itemId": item.id,
            "categoryId": item.category_id,
            "locationId": location_id,
            "businessId": current_user.business_id,
            "name": item.name,
            "price": item.price,
            "inStock": item.in_stock,
        },
    )
    return item


@router.patch("/items/{item_id}", response_model=MenuItemOut)
async def update_item(
    item_id: str,
    data: MenuItemUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    item = await MenuService(db).update_item(item_id, data, current_user.business_id)
    location_id = await MenuService(db).get_item_location_id(item)
    await mq.publish(
        request.app.state.mq_connection,
        "catalog.item_updated",
        {
            "itemId": item.id,
            "categoryId": item.category_id,
            "locationId": location_id,
            "businessId": current_user.business_id,
            "name": item.name,
            "price": item.price,
            "inStock": item.in_stock,
        },
    )
    return item


@router.patch("/items/{item_id}/stock", response_model=MenuItemOut)
async def set_item_stock(
    item_id: str,
    data: StockUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    item = await MenuService(db).set_stock(item_id, data.in_stock, current_user.business_id)
    location_id = await MenuService(db).get_item_location_id(item)
    await mq.publish(
        request.app.state.mq_connection,
        "catalog.item_updated",
        {
            "itemId": item.id,
            "categoryId": item.category_id,
            "locationId": location_id,
            "businessId": current_user.business_id,
            "name": item.name,
            "price": item.price,
            "inStock": item.in_stock,
        },
    )
    return item


@router.get("/locations/{location_id}/stock", response_model=list[MenuItemOut])
async def list_location_stock(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return await MenuService(db).list_all_items(location_id, current_user.business_id)


@router.post("/categories/{category_id}/items/reorder", status_code=204)
async def reorder_items(
    category_id: str,
    body: dict,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await MenuService(db).reorder_items(category_id, body["ids"], current_user.business_id)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    """Moves the item to trash (soft-delete) — see `MenuService.delete_item`."""
    await MenuService(db).delete_item(item_id, current_user.business_id)
    await mq.publish(
        request.app.state.mq_connection,
        "catalog.item_updated",
        {"itemId": item_id, "trashed": True, "businessId": current_user.business_id},
    )


@router.get("/locations/{location_id}/trash", response_model=list[MenuItemOut])
async def list_trashed_items(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await MenuService(db).list_trashed_items(location_id, current_user.business_id)


@router.post("/items/{item_id}/restore", response_model=MenuItemOut)
async def restore_item(
    item_id: str,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    item = await MenuService(db).restore_item(item_id, current_user.business_id)
    location_id = await MenuService(db).get_item_location_id(item)
    await mq.publish(
        request.app.state.mq_connection,
        "catalog.item_updated",
        {
            "itemId": item.id,
            "categoryId": item.category_id,
            "locationId": location_id,
            "businessId": current_user.business_id,
            "name": item.name,
            "price": item.price,
            "inStock": item.in_stock,
        },
    )
    return item


@router.delete("/items/{item_id}/permanent", status_code=204)
async def permanently_delete_item(
    item_id: str,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await MenuService(db).permanently_delete_item(item_id, current_user.business_id)
    await mq.publish(
        request.app.state.mq_connection,
        "catalog.item_updated",
        {"itemId": item_id, "permanentlyDeleted": True, "businessId": current_user.business_id},
    )


@router.post("/items/bulk-price", response_model=dict)
async def bulk_price_update(
    data: BulkPriceUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    count = await MenuService(db).bulk_price_update(data, current_user.business_id)
    await mq.publish(
        request.app.state.mq_connection,
        "catalog.item_updated",
        {
            "bulk": True,
            "categoryId": data.category_id,
            "locationId": data.location_id,
            "businessId": current_user.business_id,
            "changePct": data.change_pct,
            "changeAbs": data.change_abs,
            "updated": count,
        },
    )
    return {"updated": count}


# ── Modifier Groups ───────────────────────────────────────────────────────────


@router.post("/modifier-groups", response_model=ModifierGroupOut, status_code=201)
async def create_modifier_group(
    data: ModifierGroupCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await MenuService(db).create_modifier_group(data, current_user.business_id)


@router.patch("/modifier-groups/{group_id}", response_model=ModifierGroupOut)
async def update_modifier_group(
    group_id: str,
    data: ModifierGroupUpdate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await MenuService(db).update_modifier_group(group_id, data, current_user.business_id)


@router.delete("/modifier-groups/{group_id}", status_code=204)
async def delete_modifier_group(
    group_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await MenuService(db).delete_modifier_group(group_id, current_user.business_id)


@router.post("/modifier-groups/{group_id}/modifiers", response_model=ModifierOut, status_code=201)
async def add_modifier(
    group_id: str,
    data: ModifierCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await MenuService(db).add_modifier(group_id, data, current_user.business_id)


@router.delete("/modifiers/{modifier_id}", status_code=204)
async def delete_modifier(
    modifier_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await MenuService(db).delete_modifier(modifier_id, current_user.business_id)
