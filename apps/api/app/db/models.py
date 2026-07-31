"""SQLAlchemy ORM models — all core entities for SmartServe."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Business & Location ──────────────────────────────────────────────────────

class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str] = mapped_column(String(2), default="IL")
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    locations: Mapped[list["Location"]] = relationship(back_populates="business")
    users: Mapped[list["User"]] = relationship(back_populates="business")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Jerusalem")
    language: Mapped[str] = mapped_column(String(5), default="he")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    business: Mapped["Business"] = relationship(back_populates="locations")
    menu_categories: Mapped[list["MenuCategory"]] = relationship(back_populates="location")
    tables: Mapped[list["Table"]] = relationship(back_populates="location")
    orders: Mapped[list["Order"]] = relationship(back_populates="location")
    printers: Mapped[list["Printer"]] = relationship(back_populates="location")


# ─── Users ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="waiter")
    language: Mapped[str] = mapped_column(String(5), default="he")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    business: Mapped["Business"] = relationship(back_populates="users")


# ─── Menu ─────────────────────────────────────────────────────────────────────

class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped["Location"] = relationship(back_populates="menu_categories")
    items: Mapped[list["MenuItem"]] = relationship(back_populates="category")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(ForeignKey("menu_categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    description_he: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.17)
    image_url: Mapped[str | None] = mapped_column(Text)
    preparation_time_min: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["MenuCategory"] = relationship(back_populates="items")
    modifier_groups: Mapped[list["ModifierGroup"]] = relationship(back_populates="item")


class ModifierGroup(Base):
    __tablename__ = "modifier_groups"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0)
    max_select: Mapped[int] = mapped_column(Integer, default=1)

    item: Mapped["MenuItem"] = relationship(back_populates="modifier_groups")
    modifiers: Mapped[list["Modifier"]] = relationship(back_populates="group")


class Modifier(Base):
    __tablename__ = "modifiers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(ForeignKey("modifier_groups.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_he: Mapped[str | None] = mapped_column(String(255))
    price_delta: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped["ModifierGroup"] = relationship(back_populates="modifiers")


# ─── Tables ───────────────────────────────────────────────────────────────────

class Table(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    section: Mapped[str | None] = mapped_column(String(100))
    pos_x: Mapped[float] = mapped_column(Float, default=0.0)
    pos_y: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped["Location"] = relationship(back_populates="tables")
    orders: Mapped[list["Order"]] = relationship(back_populates="table")


# ─── Orders ───────────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    table_id: Mapped[str | None] = mapped_column(ForeignKey("tables.id"))
    channel: Mapped[str] = mapped_column(String(50), default="dine_in")
    status: Mapped[str] = mapped_column(String(50), default="open")
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    location: Mapped["Location"] = relationship(back_populates="orders")
    table: Mapped["Table"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    menu_item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    modifiers: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    order: Mapped["Order"] = relationship(back_populates="items")


# ─── Payments ────────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    gateway_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    order: Mapped["Order"] = relationship(back_populates="payments")


# ─── Printers ────────────────────────────────────────────────────────────────

class Printer(Base):
    __tablename__ = "printers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="receipt")
    ip: Mapped[str | None] = mapped_column(String(45))
    port: Mapped[int] = mapped_column(Integer, default=9100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped["Location"] = relationship(back_populates="printers")
    routes: Mapped[list["PrinterRoute"]] = relationship(back_populates="printer")


class PrinterRoute(Base):
    """Routes a menu category's orders to a specific printer."""
    __tablename__ = "printer_routes"
    __table_args__ = (UniqueConstraint("printer_id", "category_id"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    printer_id: Mapped[str] = mapped_column(ForeignKey("printers.id"), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("menu_categories.id"), nullable=False)

    printer: Mapped["Printer"] = relationship(back_populates="routes")
