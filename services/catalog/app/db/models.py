"""SQLAlchemy ORM models — catalog service owns MenuCategory/MenuItem/Modifier(Group)/Discount.

Business/Location/User are trimmed, read-only mirrors of tables owned by `auth`
(services/auth) — same physical Postgres instance, schema-per-service mapping only
(see docs/microservices-plan.md §4).
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from smartserve_shared.mirrors import ReadOnlyMirror
from smartserve_shared.money import MONEY_NUMERIC, RATE_NUMERIC
from smartserve_shared.outbox import declare_outbox
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
    language: Mapped[str] = mapped_column(String(5), default="he")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    menu_categories: Mapped[list[MenuCategory]] = relationship(
        back_populates="location",
        primaryjoin="MenuCategory.location_id == Location.id",
        foreign_keys="[MenuCategory.location_id]",
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


# ─── Catalog (owned here) ─────────────────────────────────────────────────────


class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("menu_categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped[Location] = relationship(
        back_populates="menu_categories",
        primaryjoin="MenuCategory.location_id == Location.id",
        foreign_keys=[location_id],
    )
    items: Mapped[list[MenuItem]] = relationship(back_populates="category")
    parent: Mapped[MenuCategory | None] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list[MenuCategory]] = relationship(back_populates="parent")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(ForeignKey("menu_categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    description_he: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(RATE_NUMERIC, default=Decimal("0.17"))
    image_url: Mapped[str | None] = mapped_column(Text)
    preparation_time_min: Mapped[int] = mapped_column(Integer, default=10)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    default_fire_course: Mapped[int] = mapped_column(Integer, default=1)
    # Soft-delete (trash) timestamp — deliberately separate from `active`/`in_stock`, which
    # control order-grid visibility for the existing "toggle availability" feature and are a
    # different concept. NULL means "not trashed"; a non-null value is when it was trashed.
    # Excluded by default from every listing query (list_items/list_all_items/bulk_price_update);
    # a real `db.delete()` only ever happens via `permanently_delete_item`, and only on an
    # already-trashed item.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    category: Mapped[MenuCategory] = relationship(back_populates="items")
    modifier_groups: Mapped[list[ModifierGroup]] = relationship(
        back_populates="item", cascade="all, delete-orphan", passive_deletes=True
    )


class ModifierGroup(Base):
    __tablename__ = "modifier_groups"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0)
    max_select: Mapped[int] = mapped_column(Integer, default=1)

    item: Mapped[MenuItem] = relationship(back_populates="modifier_groups")
    modifiers: Mapped[list[Modifier]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )


class Modifier(Base):
    __tablename__ = "modifiers"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(ForeignKey("modifier_groups.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    price_delta: Mapped[Decimal] = mapped_column(MONEY_NUMERIC, default=Decimal("0.00"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped[ModifierGroup] = relationship(back_populates="modifiers")


class Discount(Base):
    __tablename__ = "discounts"
    __table_args__ = (UniqueConstraint("business_id", "code"),)

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # "percent" applies value as a percentage of order total; "fixed" subtracts a flat amount
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


Outbox = declare_outbox(Base, "catalog_outbox")
