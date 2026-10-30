"""SQLAlchemy ORM models — printing service owns Printer + PrinterRoute. User, Location,
MenuCategory and MenuItem are trimmed mirrors (see docs/microservices-plan.md §4) used for
tenant checks: a printer through its location, a route through its printer, and the routed
item's category through that location's business.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# ─── User (owned by auth, trimmed mirror) ─────────────────────────────────────


class User(Base):
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


# ─── Location / catalog (owned elsewhere, trimmed mirrors) ────────────────────


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(String(), nullable=False)


# ─── Printers + routing (owned here) ───────────────────────────────────────────


class Printer(Base):
    __tablename__ = "printers"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="receipt")
    ip: Mapped[str | None] = mapped_column(String(45))
    port: Mapped[int] = mapped_column(Integer, default=9100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PrinterRoute(Base):
    """Routes a menu item's orders to a specific printer — an item can route to several printers at once."""

    __tablename__ = "printer_routes"
    __table_args__ = (UniqueConstraint("printer_id", "item_id"),)

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    printer_id: Mapped[str] = mapped_column(ForeignKey("printers.id"), nullable=False)
    item_id: Mapped[str] = mapped_column(String(), nullable=False)


class PrintJob(Base):
    """Audit trail of `order.item_fired` events fanned out to matching printer routes.

    No real physical printer driver exists yet — this table just records that a fired item
    was (or would be) routed to a printer, for visibility/debugging (see docs/microservices-plan.md §4).
    """

    __tablename__ = "print_jobs"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(), nullable=False)
    item_id: Mapped[str] = mapped_column(String(), nullable=False)
    printer_id: Mapped[str] = mapped_column(ForeignKey("printers.id"), nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
