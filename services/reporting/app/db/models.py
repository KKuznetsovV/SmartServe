"""SQLAlchemy ORM models for the reporting service.

Reporting owns `event_log`, `reporting_orders` and `reporting_order_items`. User and Location
are trimmed, read-only mirrors of auth tables (see docs/microservices-plan.md §4). Location
exists so report endpoints can verify a `location_id` belongs to the caller's business.
"""

import uuid
from datetime import UTC, datetime

from smartserve_shared.mirrors import ReadOnlyMirror
from smartserve_shared.outbox import declare_processed_events
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


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


class Location(ReadOnlyMirror, Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class ReportingOrder(Base):
    __tablename__ = "reporting_orders"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), default="dine_in")
    status: Mapped[str] = mapped_column(String(50), default="open")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[str | None] = mapped_column(String(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReportingOrderItem(Base):
    __tablename__ = "reporting_order_items"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("reporting_orders.id"), nullable=False, index=True)
    menu_item_id: Mapped[str | None] = mapped_column(String(), nullable=True)
    menu_item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(), nullable=True)
    category_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)


class EventLog(Base):
    """Generic audit trail of every RabbitMQ event received on the `smartserve.events`
    topic exchange (wildcard `#` subscription) — see docs/microservices-plan.md §4."""

    __tablename__ = "event_log"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str] = mapped_column(String(), nullable=False)
    business_id: Mapped[str | None] = mapped_column(String(), nullable=True, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


ProcessedEvent = declare_processed_events(Base, "reporting_processed_events")
