"""SQLAlchemy ORM models — ordering service owns Table/Order/OrderItem.

Business/Location/User/MenuItem/MenuCategory/ModifierGroup/Modifier/Discount are trimmed,
read-only mirrors of tables owned by `auth` and `catalog` respectively — same physical
Postgres instance, no schema separation (see docs/microservices-plan.md §4). Alembic
migrations for THIS service only manage tables ordering owns (`tables`/`orders`/`order_items`);
the mirror tables above must never be created/altered by ordering's migration chain — they
already exist as owned by the other services.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# ─── Business / Location / User (owned by auth, trimmed mirror) ──────────────


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str] = mapped_column(String(2), default="IL")
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    discounts: Mapped[list[Discount]] = relationship(back_populates="business")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Jerusalem")
    language: Mapped[str] = mapped_column(String(5), default="he")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    tables: Mapped[list[Table]] = relationship(back_populates="location")
    orders: Mapped[list[Order]] = relationship(back_populates="location")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="waiter")
    language: Mapped[str] = mapped_column(String(5), default="he")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ─── Catalog (owned by catalog, trimmed mirror) ───────────────────────────────


class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.17)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    default_fire_course: Mapped[int] = mapped_column(Integer, default=1)
    # Mirrors catalog's `menu_items.deleted_at` (trash state) — Python-side column only, no
    # migration needed here since catalog owns the physical ALTER TABLE for this shared
    # table; ordering only ever reads this column to keep a trashed item from being added to
    # a NEW order (see `add_item`). Never filtered on when looking up an item ALREADY on an
    # existing order (recalculating totals, removing an item, etc.) — those must keep
    # working regardless of the item's current trash state, since historical order data is
    # never retroactively affected by trashing/deleting a menu item.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    modifier_groups: Mapped[list[ModifierGroup]] = relationship(back_populates="item")


class ModifierGroup(Base):
    """Read-only mirror of catalog.modifier_groups — ordering never writes this table."""

    __tablename__ = "modifier_groups"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0)
    max_select: Mapped[int] = mapped_column(Integer, default=1)

    item: Mapped[MenuItem] = relationship(back_populates="modifier_groups")
    modifiers: Mapped[list[Modifier]] = relationship(back_populates="group")


class Modifier(Base):
    """Read-only mirror of catalog.modifiers — ordering never writes this table."""

    __tablename__ = "modifiers"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(ForeignKey("modifier_groups.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_delta: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped[ModifierGroup] = relationship(back_populates="modifiers")


class Discount(Base):
    __tablename__ = "discounts"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="percent")
    value: Mapped[float] = mapped_column(Float, nullable=False)
    min_order_amount: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    business: Mapped[Business] = relationship(back_populates="discounts")
    orders: Mapped[list[Order]] = relationship(back_populates="discount")


# ─── Ordering (owned here) ────────────────────────────────────────────────────


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    section: Mapped[str | None] = mapped_column(String(100))
    pos_x: Mapped[float] = mapped_column(Float, default=0.0)
    pos_y: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped[Location] = relationship(back_populates="tables")
    orders: Mapped[list[Order]] = relationship(back_populates="table")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_location_status", "location_id", "status"),
        Index("ix_orders_location_created", "location_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    table_id: Mapped[str | None] = mapped_column(ForeignKey("tables.id"))
    discount_id: Mapped[str | None] = mapped_column(ForeignKey("discounts.id"))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="dine_in")
    status: Mapped[str] = mapped_column(String(50), default="open")
    guest_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fired_courses: Mapped[list] = mapped_column(JSON, default=list)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    location: Mapped[Location] = relationship(back_populates="orders")
    table: Mapped[Table] = relationship(back_populates="orders")
    discount: Mapped[Discount | None] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", order_by="OrderItem.sort_order")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (Index("ix_order_items_order_id", "order_id"),)

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    menu_item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(), nullable=True)
    category_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    modifiers: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    fire_course: Mapped[int] = mapped_column(Integer, default=1)
    guest_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discount_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    is_comped: Mapped[bool] = mapped_column(Boolean, default=False)
    comped_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    order: Mapped[Order] = relationship(back_populates="items")
