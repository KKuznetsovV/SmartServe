"""SQLAlchemy ORM models — all core entities for SmartServe."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
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


# ─── Business & Location ──────────────────────────────────────────────────────


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str] = mapped_column(String(2), default="IL")
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    locations: Mapped[list[Location]] = relationship(back_populates="business")
    users: Mapped[list[User]] = relationship(back_populates="business")
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

    business: Mapped[Business] = relationship(back_populates="locations")
    menu_categories: Mapped[list[MenuCategory]] = relationship(back_populates="location")
    tables: Mapped[list[Table]] = relationship(back_populates="location")
    printers: Mapped[list[Printer]] = relationship(back_populates="location")


# ─── Users ───────────────────────────────────────────────────────────────────


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

    business: Mapped[Business] = relationship(back_populates="users")


# ─── Menu ─────────────────────────────────────────────────────────────────────


class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("menu_categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped[Location] = relationship(back_populates="menu_categories")
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
    price: Mapped[float] = mapped_column(Float, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.17)
    image_url: Mapped[str | None] = mapped_column(Text)
    preparation_time_min: Mapped[int] = mapped_column(Integer, default=10)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    default_fire_course: Mapped[int] = mapped_column(Integer, default=1)

    category: Mapped[MenuCategory] = relationship(back_populates="items")
    modifier_groups: Mapped[list[ModifierGroup]] = relationship(back_populates="item")
    printer_routes: Mapped[list[PrinterRoute]] = relationship(back_populates="item")


class ModifierGroup(Base):
    __tablename__ = "modifier_groups"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0)
    max_select: Mapped[int] = mapped_column(Integer, default=1)

    item: Mapped[MenuItem] = relationship(back_populates="modifier_groups")
    modifiers: Mapped[list[Modifier]] = relationship(back_populates="group")


class Modifier(Base):
    __tablename__ = "modifiers"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(ForeignKey("modifier_groups.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    price_delta: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped[ModifierGroup] = relationship(back_populates="modifiers")


# ─── Tables ───────────────────────────────────────────────────────────────────


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


# ─── Discounts ────────────────────────────────────────────────────────────────


class Discount(Base):
    __tablename__ = "discounts"
    __table_args__ = (UniqueConstraint("business_id", "code"),)

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # "percent" applies value as a percentage of order total; "fixed" subtracts a flat amount
    type: Mapped[str] = mapped_column(String(20), default="percent")
    value: Mapped[float] = mapped_column(Float, nullable=False)
    min_order_amount: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    business: Mapped[Business] = relationship(back_populates="discounts")


# ─── Printers ────────────────────────────────────────────────────────────────


class Printer(Base):
    __tablename__ = "printers"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="receipt")
    ip: Mapped[str | None] = mapped_column(String(45))
    port: Mapped[int] = mapped_column(Integer, default=9100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped[Location] = relationship(back_populates="printers")
    routes: Mapped[list[PrinterRoute]] = relationship(back_populates="printer")


class PrinterRoute(Base):
    """Routes a menu item's orders to a specific printer — an item can route to several printers at once."""

    __tablename__ = "printer_routes"
    __table_args__ = (UniqueConstraint("printer_id", "item_id"),)

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    printer_id: Mapped[str] = mapped_column(ForeignKey("printers.id"), nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), nullable=False)

    printer: Mapped[Printer] = relationship(back_populates="routes")
    item: Mapped[MenuItem] = relationship(back_populates="printer_routes")
