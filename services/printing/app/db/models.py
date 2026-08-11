"""SQLAlchemy ORM models — printing service owns Printer + PrinterRoute. User is a
trimmed, read-only-elsewhere mirror (see docs/microservices-plan.md §4). Printer.location_id
and PrinterRoute.item_id are plain strings (not ForeignKeys) since Location (auth) and
MenuItem (catalog) aren't mirrored here — the service never joins to their tables, only
compares/stores the id values, following the minimal-mirror precedent set in payments/staff.
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
