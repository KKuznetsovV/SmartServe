"""Menu service — all business logic for categories, items, and modifiers."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.db.models import MenuCategory, MenuItem, ModifierGroup, Modifier
from app.schemas.menu import (
    MenuCategoryCreate, MenuCategoryUpdate,
    MenuItemCreate, MenuItemUpdate,
    ModifierGroupCreate, ModifierGroupUpdate,
    ModifierCreate, BulkPriceUpdate,
)


class MenuService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Categories ──────────────────────────────────────────────────────────

    async def list_categories(self, location_id: str) -> list[MenuCategory]:
        result = await self.db.execute(
            select(MenuCategory)
            .where(MenuCategory.location_id == location_id)
            .order_by(MenuCategory.sort_order)
        )
        return list(result.scalars().all())

    async def get_category(self, category_id: str) -> MenuCategory:
        result = await self.db.execute(
            select(MenuCategory).where(MenuCategory.id == category_id)
        )
        cat = result.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        return cat

    async def create_category(self, data: MenuCategoryCreate) -> MenuCategory:
        cat = MenuCategory(**data.model_dump())
        self.db.add(cat)
        await self.db.flush()
        return cat

    async def update_category(self, category_id: str, data: MenuCategoryUpdate) -> MenuCategory:
        cat = await self.get_category(category_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(cat, field, value)
        await self.db.flush()
        return cat

    async def delete_category(self, category_id: str) -> None:
        cat = await self.get_category(category_id)
        await self.db.delete(cat)

    async def reorder_categories(self, location_id: str, ids: list[str]) -> None:
        for order, cat_id in enumerate(ids):
            await self.db.execute(
                update(MenuCategory)
                .where(MenuCategory.id == cat_id, MenuCategory.location_id == location_id)
                .values(sort_order=order)
            )

    # ── Items ────────────────────────────────────────────────────────────────

    async def list_items(self, category_id: str) -> list[MenuItem]:
        result = await self.db.execute(
            select(MenuItem).where(MenuItem.category_id == category_id)
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
        )
        return list(result.scalars().all())

    async def get_item(self, item_id: str) -> MenuItem:
        result = await self.db.execute(
            select(MenuItem).where(MenuItem.id == item_id)
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return item

    async def create_item(self, data: MenuItemCreate) -> MenuItem:
        # Verify category exists
        await self.get_category(data.category_id)
        item = MenuItem(**data.model_dump())
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        # Eagerly load relationships for response serialization
        result = await self.db.execute(
            select(MenuItem).where(MenuItem.id == item.id)
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
        )
        return result.scalar_one()

    async def update_item(self, item_id: str, data: MenuItemUpdate) -> MenuItem:
        item = await self.get_item(item_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(item, field, value)
        await self.db.flush()
        return await self.get_item(item_id)

    async def delete_item(self, item_id: str) -> None:
        item = await self.get_item(item_id)
        await self.db.delete(item)

    async def bulk_price_update(self, data: BulkPriceUpdate) -> int:
        """Returns count of updated items."""
        q = select(MenuItem).join(MenuCategory, MenuItem.category_id == MenuCategory.id)\
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
        if data.category_id:
            q = q.where(MenuItem.category_id == data.category_id)
        else:
            q = q.where(MenuCategory.location_id == data.location_id)

        result = await self.db.execute(q)
        items = result.scalars().all()

        for item in items:
            if data.change_pct is not None:
                item.price = round(item.price * (1 + data.change_pct / 100), 2)
            elif data.change_abs is not None:
                item.price = max(0.0, round(item.price + data.change_abs, 2))

        await self.db.flush()
        return len(items)

    # ── Modifier Groups ──────────────────────────────────────────────────────

    async def create_modifier_group(self, data: ModifierGroupCreate) -> ModifierGroup:
        await self.get_item(data.item_id)
        modifiers_data = data.modifiers
        group = ModifierGroup(**data.model_dump(exclude={"modifiers"}))
        self.db.add(group)
        await self.db.flush()

        for mod_data in modifiers_data:
            mod = Modifier(group_id=group.id, **mod_data.model_dump())
            self.db.add(mod)

        await self.db.flush()
        return group

    async def get_modifier_group(self, group_id: str) -> ModifierGroup:
        result = await self.db.execute(
            select(ModifierGroup).where(ModifierGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modifier group not found")
        return group

    async def update_modifier_group(self, group_id: str, data: ModifierGroupUpdate) -> ModifierGroup:
        group = await self.get_modifier_group(group_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(group, field, value)
        await self.db.flush()
        return group

    async def delete_modifier_group(self, group_id: str) -> None:
        group = await self.get_modifier_group(group_id)
        await self.db.delete(group)

    async def add_modifier(self, group_id: str, data: ModifierCreate) -> Modifier:
        await self.get_modifier_group(group_id)
        mod = Modifier(group_id=group_id, **data.model_dump())
        self.db.add(mod)
        await self.db.flush()
        return mod

    async def delete_modifier(self, modifier_id: str) -> None:
        result = await self.db.execute(select(Modifier).where(Modifier.id == modifier_id))
        mod = result.scalar_one_or_none()
        if not mod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modifier not found")
        await self.db.delete(mod)
