"""SQLAlchemy ORM models — ordering service owns Table/Order/OrderItem.

Business/Location/User/MenuItem/MenuCategory/ModifierGroup/Modifier/Discount are trimmed,
read-only mirrors of tables owned by `auth` and `catalog` respectively — same physical
Postgres instance, no schema separation (see docs/microservices-plan.md §4). Alembic
migrations for THIS service only manage tables ordering owns (`tables`/`orders`/`order_items`);
the mirror tables above must never be created/altered by ordering's migration chain — they
already exist as owned by the other services.
"""

import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal

from smartserve_shared.mirrors import ReadOnlyMirror
from smartserve_shared.money import MONEY_NUMERIC, RATE_NUMERIC
from smartserve_shared.outbox import declare_outbox, declare_processed_events
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# ─── Business / Location / User (owned by auth, trimmed mirror) ──────────────


class Business(ReadOnlyMirror, Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str] = mapped_column(String(2), default="IL")
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    vat_rate: Mapped[Decimal] = mapped_column(RATE_NUMERIC, default=Decimal("0.18"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    discounts: Mapped[list[Discount]] = relationship(
        back_populates="business",
        primaryjoin="Discount.business_id == Business.id",
        foreign_keys="[Discount.business_id]",
    )


class Location(ReadOnlyMirror, Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Jerusalem")
    business_day_cutoff: Mapped[time] = mapped_column(Time, default=time(5, 0), server_default="05:00:00")
    language: Mapped[str] = mapped_column(String(5), default="he")
    vat_rate: Mapped[Decimal | None] = mapped_column(RATE_NUMERIC, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    tables: Mapped[list[Table]] = relationship(
        back_populates="location",
        primaryjoin="Table.location_id == Location.id",
        foreign_keys="[Table.location_id]",
    )
    orders: Mapped[list[Order]] = relationship(
        back_populates="location",
        primaryjoin="Order.location_id == Location.id",
        foreign_keys="[Order.location_id]",
    )


class User(ReadOnlyMirror, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="waiter")
    language: Mapped[str] = mapped_column(String(5), default="he")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ─── Catalog (owned by catalog, trimmed mirror) ───────────────────────────────


class MenuCategory(ReadOnlyMirror, Base):
    __tablename__ = "menu_categories"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class MenuItem(ReadOnlyMirror, Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, nullable=False)
    # Deprecated: VAT is location/business-level and snapshotted on the order. Kept for
    # existing rows; ordering no longer reads this column when computing totals.
    tax_rate: Mapped[Decimal] = mapped_column(RATE_NUMERIC, default=Decimal("0.17"))
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

    modifier_groups: Mapped[list[ModifierGroup]] = relationship(
        back_populates="item",
        primaryjoin="ModifierGroup.item_id == MenuItem.id",
        foreign_keys="[ModifierGroup.item_id]",
    )


class ModifierGroup(ReadOnlyMirror, Base):
    """Read-only mirror of catalog.modifier_groups — ordering never writes this table."""

    __tablename__ = "modifier_groups"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0)
    max_select: Mapped[int] = mapped_column(Integer, default=1)

    item: Mapped[MenuItem] = relationship(
        back_populates="modifier_groups",
        primaryjoin="ModifierGroup.item_id == MenuItem.id",
        foreign_keys=[item_id],
    )
    modifiers: Mapped[list[Modifier]] = relationship(
        back_populates="group",
        primaryjoin="Modifier.group_id == ModifierGroup.id",
        foreign_keys="[Modifier.group_id]",
    )


class Modifier(ReadOnlyMirror, Base):
    """Read-only mirror of catalog.modifiers — ordering never writes this table."""

    __tablename__ = "modifiers"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_delta: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, default=Decimal("0.00"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped[ModifierGroup] = relationship(
        back_populates="modifiers",
        primaryjoin="Modifier.group_id == ModifierGroup.id",
        foreign_keys=[group_id],
    )


class Discount(ReadOnlyMirror, Base):
    __tablename__ = "discounts"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="percent")
    value: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, nullable=False)
    min_order_amount: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, default=Decimal("0.00"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    business: Mapped[Business] = relationship(
        back_populates="discounts",
        primaryjoin="Discount.business_id == Business.id",
        foreign_keys=[business_id],
    )
    orders: Mapped[list[Order]] = relationship(
        back_populates="discount",
        primaryjoin="Order.discount_id == Discount.id",
        foreign_keys="[Order.discount_id]",
    )


# ─── Ordering (owned here) ────────────────────────────────────────────────────


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    section: Mapped[str | None] = mapped_column(String(100))
    pos_x: Mapped[float] = mapped_column(Float, default=0.0)
    pos_y: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped[Location] = relationship(
        back_populates="tables",
        primaryjoin="Table.location_id == Location.id",
        foreign_keys=[location_id],
    )
    orders: Mapped[list[Order]] = relationship(back_populates="table")


class OrderNumberCounter(Base):
    __tablename__ = "order_number_counters"

    location_id: Mapped[str] = mapped_column(String(), primary_key=True)
    business_date: Mapped[date] = mapped_column(Date, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_location_status", "location_id", "status"),
        Index("ix_orders_location_created", "location_id", "created_at"),
        UniqueConstraint(
            "location_id",
            "business_date",
            "order_number",
            name="uq_orders_location_business_date_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    table_id: Mapped[str | None] = mapped_column(ForeignKey("tables.id"))
    discount_id: Mapped[str | None] = mapped_column(String(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="dine_in")
    status: Mapped[str] = mapped_column(String(50), default="open")
    guest_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fired_courses: Mapped[list] = mapped_column(JSON, default=list)
    subtotal: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, default=Decimal("0.00"))
    vat_rate: Mapped[Decimal] = mapped_column(RATE_NUMERIC, default=Decimal("0.18"))
    order_number: Mapped[int] = mapped_column(Integer, nullable=False)
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    location: Mapped[Location] = relationship(
        back_populates="orders",
        primaryjoin="Order.location_id == Location.id",
        foreign_keys=[location_id],
    )
    table: Mapped[Table] = relationship(back_populates="orders")

    @property
    def table_name(self) -> str | None:
        """Denormalized for API responses; takeaway orders have no table."""
        if "table" in inspect(self).unloaded:
            return None
        return self.table.name if self.table is not None else None

    discount: Mapped[Discount | None] = relationship(
        back_populates="orders",
        primaryjoin="Order.discount_id == Discount.id",
        foreign_keys=[discount_id],
    )
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", order_by="OrderItem.sort_order")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (Index("ix_order_items_order_id", "order_id"),)

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[str] = mapped_column(String(), nullable=False)
    menu_item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(), nullable=True)
    category_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, nullable=False)
    modifiers: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    fire_course: Mapped[int] = mapped_column(Integer, default=1)
    fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    guest_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discount_value: Mapped[Decimal | None] = mapped_column(MONEY_NUMERIC, nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, default=Decimal("0.00"))
    is_comped: Mapped[bool] = mapped_column(Boolean, default=False)
    comped_by: Mapped[str | None] = mapped_column(String(), nullable=True)

    order: Mapped[Order] = relationship(back_populates="items")


Outbox = declare_outbox(Base, "ordering_outbox")
ProcessedEvent = declare_processed_events(Base, "ordering_processed_events")
