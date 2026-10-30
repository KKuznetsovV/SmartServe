"""Menu service — all business logic for categories, items, and modifiers."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from smartserve_shared.money import money
from smartserve_shared.tenancy import verify_location_owned
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Location, MenuCategory, MenuItem, Modifier, ModifierGroup
from app.modules.catalog.schemas import (
    BulkPriceUpdate,
    MenuCategoryCreate,
    MenuCategoryUpdate,
    MenuItemCreate,
    MenuItemUpdate,
    ModifierCreate,
    ModifierGroupCreate,
    ModifierGroupUpdate,
    validate_group_select,
)


class MenuService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Categories ──────────────────────────────────────────────────────────

    async def list_categories(self, location_id: str, business_id: str | None = None) -> list[MenuCategory]:
        if business_id is not None:
            await verify_location_owned(self.db, location_id, business_id, Location)
        result = await self.db.execute(
            select(MenuCategory).where(MenuCategory.location_id == location_id).order_by(MenuCategory.sort_order)
        )
        return list(result.scalars().all())

    async def get_category(self, category_id: str, business_id: str | None = None) -> MenuCategory:
        q = select(MenuCategory).where(MenuCategory.id == category_id)
        if business_id is not None:
            q = q.join(Location, MenuCategory.location_id == Location.id).where(Location.business_id == business_id)
        result = await self.db.execute(q)
        cat = result.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        return cat

    async def create_category(self, data: MenuCategoryCreate, business_id: str | None = None) -> MenuCategory:
        if business_id is not None:
            await verify_location_owned(self.db, data.location_id, business_id, Location)
        if data.parent_id:
            await self._validate_parent(data.parent_id, data.location_id)
        cat = MenuCategory(**data.model_dump())
        self.db.add(cat)
        await self.db.flush()
        return cat

    async def update_category(
        self, category_id: str, data: MenuCategoryUpdate, business_id: str | None = None
    ) -> MenuCategory:
        cat = await self.get_category(category_id, business_id)
        updates = data.model_dump(exclude_unset=True)
        if "parent_id" in updates and updates["parent_id"] is not None:
            await self._reject_parent_cycle(category_id, updates["parent_id"])
            await self._validate_parent(updates["parent_id"], cat.location_id)
        for field, value in updates.items():
            setattr(cat, field, value)
        await self.db.flush()
        return cat

    async def _validate_parent(self, parent_id: str, location_id: str) -> None:
        parent = await self.get_category(parent_id)
        if parent.location_id != location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Parent category is not in this location"
            )

    async def _reject_parent_cycle(self, category_id: str, parent_id: str) -> None:
        if parent_id == category_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A category cannot be its own parent")
        current: str | None = parent_id
        seen: set[str] = set()
        while current:
            if current == category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A category cannot be nested under one of its descendants",
                )
            if current in seen:
                break
            seen.add(current)
            ancestor = await self.get_category(current)
            current = ancestor.parent_id

    async def delete_category(self, category_id: str, business_id: str | None = None) -> None:
        cat = await self.get_category(category_id, business_id)
        item_count = await self.db.scalar(
            select(func.count()).select_from(MenuItem).where(MenuItem.category_id == category_id)
        )
        child_count = await self.db.scalar(
            select(func.count()).select_from(MenuCategory).where(MenuCategory.parent_id == category_id)
        )
        if item_count or child_count:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category has items or subcategories")
        await self.db.delete(cat)

    async def reorder_categories(self, location_id: str, ids: list[str], business_id: str | None = None) -> None:
        if business_id is not None:
            await verify_location_owned(self.db, location_id, business_id, Location)
        for order, cat_id in enumerate(ids):
            await self.db.execute(
                update(MenuCategory)
                .where(MenuCategory.id == cat_id, MenuCategory.location_id == location_id)
                .values(sort_order=order)
            )

    # ── Items ────────────────────────────────────────────────────────────────

    async def list_items(self, category_id: str, business_id: str | None = None) -> list[MenuItem]:
        if business_id is not None:
            await self.get_category(category_id, business_id)
        result = await self.db.execute(
            select(MenuItem)
            .where(MenuItem.category_id == category_id, MenuItem.deleted_at.is_(None))
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
            .order_by(MenuItem.sort_order, MenuItem.name)
        )
        return list(result.scalars().all())

    async def list_trashed_items(self, location_id: str, business_id: str | None = None) -> list[MenuItem]:
        """Items currently in trash for a location — powers the menu editor's trash view."""
        if business_id is not None:
            await verify_location_owned(self.db, location_id, business_id, Location)
        result = await self.db.execute(
            select(MenuItem)
            .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
            .where(MenuCategory.location_id == location_id, MenuItem.deleted_at.is_not(None))
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
            .order_by(MenuItem.deleted_at.desc())
        )
        return list(result.scalars().all())

    async def get_item(
        self, item_id: str, business_id: str | None = None, *, include_trashed: bool = False
    ) -> MenuItem:
        q = (
            select(MenuItem)
            .where(MenuItem.id == item_id)
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
        )
        if not include_trashed:
            q = q.where(MenuItem.deleted_at.is_(None))
        if business_id is not None:
            q = (
                q.join(MenuCategory, MenuItem.category_id == MenuCategory.id)
                .join(Location, MenuCategory.location_id == Location.id)
                .where(Location.business_id == business_id)
            )
        result = await self.db.execute(q)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return item

    async def create_item(self, data: MenuItemCreate, business_id: str | None = None) -> MenuItem:
        # Verify category exists (and, when scoped, that it's in the caller's own business)
        await self.get_category(data.category_id, business_id)
        payload = data.model_dump()
        if payload.get("sort_order") is None:
            payload["sort_order"] = await self._next_sort_order(data.category_id)
        item = MenuItem(**payload)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        # Eagerly load relationships for response serialization
        result = await self.db.execute(
            select(MenuItem)
            .where(MenuItem.id == item.id)
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
        )
        return result.scalar_one()

    async def update_item(self, item_id: str, data: MenuItemUpdate, business_id: str | None = None) -> MenuItem:
        item = await self.get_item(item_id, business_id)
        updates = data.model_dump(exclude_none=True)
        # Moving to a different category with no explicit position: append to the end of it
        if updates.get("category_id") and updates["category_id"] != item.category_id:
            # A rename target category must also belong to the caller's own business —
            # otherwise an item could be relocated into another business's menu.
            await self.get_category(updates["category_id"], business_id)
            if "sort_order" not in updates:
                updates["sort_order"] = await self._next_sort_order(updates["category_id"])
        for field, value in updates.items():
            setattr(item, field, value)
        await self.db.flush()
        return await self.get_item(item_id)

    async def _next_sort_order(self, category_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(MenuItem).where(MenuItem.category_id == category_id)
        )
        return result.scalar_one()

    async def reorder_items(self, category_id: str, ids: list[str], business_id: str | None = None) -> None:
        if business_id is not None:
            await self.get_category(category_id, business_id)
        for order, item_id in enumerate(ids):
            await self.db.execute(
                update(MenuItem)
                .where(MenuItem.id == item_id, MenuItem.category_id == category_id)
                .values(sort_order=order)
            )

    async def delete_item(self, item_id: str, business_id: str | None = None) -> None:
        """Move an item to trash (soft-delete). Does not touch the row's DB identity —
        historical `OrderItem`/reporting records reference this id and snapshot their own
        name/price/category at the time they were created, so they are entirely unaffected.
        An already-trashed item is not found by `get_item`'s default (non-`include_trashed`)
        query, so re-trashing an already-trashed item correctly 404s instead of silently
        no-op'ing twice."""
        item = await self.get_item(item_id, business_id)
        item.deleted_at = datetime.now(UTC)
        await self.db.flush()

    async def restore_item(self, item_id: str, business_id: str | None = None) -> MenuItem:
        """Clear an item's trash state, making it visible again in every default listing."""
        item = await self.get_item(item_id, business_id, include_trashed=True)
        if item.deleted_at is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is not in trash")
        item.deleted_at = None
        await self.db.flush()
        return await self.get_item(item_id, business_id)

    async def permanently_delete_item(self, item_id: str, business_id: str | None = None) -> None:
        """Real, irreversible delete — only callable on an item that's already in trash, so an
        item can never go from 'active on the menu' straight to permanently gone without
        passing through the trash view first."""
        item = await self.get_item(item_id, business_id, include_trashed=True)
        if item.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item must be moved to trash before it can be permanently deleted",
            )
        await self.db.delete(item)

    async def bulk_price_update(self, data: BulkPriceUpdate, business_id: str | None = None) -> int:
        """Returns count of updated items."""
        if business_id is not None:
            if data.category_id:
                await self.get_category(data.category_id, business_id)
            else:
                await verify_location_owned(self.db, data.location_id, business_id, Location)

        q = (
            select(MenuItem)
            .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
            .where(MenuItem.deleted_at.is_(None))
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
        )
        if data.category_id:
            q = q.where(MenuItem.category_id == data.category_id)
        else:
            q = q.where(MenuCategory.location_id == data.location_id)

        result = await self.db.execute(q)
        items = result.scalars().all()

        for item in items:
            if data.change_pct is not None:
                next_price = money(money(item.price) * (Decimal("1") + Decimal(str(data.change_pct)) / Decimal("100")))
            else:
                next_price = money(money(item.price) + money(data.change_abs or 0))
            item.price = max(money(0), next_price)

        await self.db.flush()
        return len(items)

    async def set_stock(self, item_id: str, in_stock: bool, business_id: str | None = None) -> MenuItem:
        item = await self.get_item(item_id, business_id)
        item.in_stock = in_stock
        await self.db.flush()
        return await self.get_item(item_id)

    async def get_item_location_id(self, item: MenuItem) -> str:
        """Resolve the location an item belongs to via its category — used to scope
        real-time event broadcasts (MenuItem has no direct location_id column)."""
        result = await self.db.execute(select(MenuCategory.location_id).where(MenuCategory.id == item.category_id))
        return result.scalar_one()

    async def list_all_items(self, location_id: str, business_id: str | None = None) -> list[MenuItem]:
        if business_id is not None:
            await verify_location_owned(self.db, location_id, business_id, Location)
        result = await self.db.execute(
            select(MenuItem)
            .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
            .where(
                MenuCategory.location_id == location_id,
                MenuItem.active.is_(True),
                MenuItem.deleted_at.is_(None),
            )
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
            .order_by(MenuCategory.sort_order, MenuItem.sort_order, MenuItem.name)
        )
        return list(result.scalars().all())

    async def create_modifier_group(self, data: ModifierGroupCreate, business_id: str | None = None) -> ModifierGroup:
        await self.get_item(data.item_id, business_id)
        modifiers_data = data.modifiers
        group = ModifierGroup(**data.model_dump(exclude={"modifiers"}))
        self.db.add(group)
        await self.db.flush()

        for mod_data in modifiers_data:
            mod = Modifier(group_id=group.id, **mod_data.model_dump())
            self.db.add(mod)

        await self.db.flush()
        return await self.get_modifier_group(group.id)

    async def get_modifier_group(self, group_id: str, business_id: str | None = None) -> ModifierGroup:
        q = select(ModifierGroup).where(ModifierGroup.id == group_id).options(selectinload(ModifierGroup.modifiers))
        if business_id is not None:
            q = (
                q.join(MenuItem, ModifierGroup.item_id == MenuItem.id)
                .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
                .join(Location, MenuCategory.location_id == Location.id)
                .where(Location.business_id == business_id)
            )
        result = await self.db.execute(q)
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modifier group not found")
        return group

    async def update_modifier_group(
        self, group_id: str, data: ModifierGroupUpdate, business_id: str | None = None
    ) -> ModifierGroup:
        group = await self.get_modifier_group(group_id, business_id)
        updates = data.model_dump(exclude_unset=True)
        required = updates["required"] if "required" in updates else group.required
        min_select = updates["min_select"] if "min_select" in updates else group.min_select
        max_select = updates["max_select"] if "max_select" in updates else group.max_select
        try:
            validate_group_select(required, min_select, max_select)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        for field, value in updates.items():
            setattr(group, field, value)
        await self.db.flush()
        return group

    async def delete_modifier_group(self, group_id: str, business_id: str | None = None) -> None:
        group = await self.get_modifier_group(group_id, business_id)
        await self.db.delete(group)

    async def add_modifier(self, group_id: str, data: ModifierCreate, business_id: str | None = None) -> Modifier:
        await self.get_modifier_group(group_id, business_id)
        mod = Modifier(group_id=group_id, **data.model_dump())
        self.db.add(mod)
        await self.db.flush()
        return mod

    async def delete_modifier(self, modifier_id: str, business_id: str | None = None) -> None:
        q = select(Modifier).where(Modifier.id == modifier_id)
        if business_id is not None:
            q = (
                q.join(ModifierGroup, Modifier.group_id == ModifierGroup.id)
                .join(MenuItem, ModifierGroup.item_id == MenuItem.id)
                .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
                .join(Location, MenuCategory.location_id == Location.id)
                .where(Location.business_id == business_id)
            )
        result = await self.db.execute(q)
        mod = result.scalar_one_or_none()
        if not mod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modifier not found")
        await self.db.delete(mod)
