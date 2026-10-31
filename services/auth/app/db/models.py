"""SQLAlchemy ORM models owned by the `auth` service: businesses, locations, users, devices.

Same physical Postgres instance/database as the other services (pragmatic schema-per-service
approach, see docs/microservices-plan.md §1/§4) — but this service only maps the tables it
owns. Other services hold plain UUID columns (no ORM relationship) for cross-service
references such as `orders.location_id`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from smartserve_shared.money import RATE_NUMERIC
from smartserve_shared.outbox import declare_outbox
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str] = mapped_column(String(2), default="IL")
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    vat_rate: Mapped[Decimal] = mapped_column(RATE_NUMERIC, default=Decimal("0.18"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    locations: Mapped[list[Location]] = relationship(back_populates="business")
    users: Mapped[list[User]] = relationship(back_populates="business")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Jerusalem")
    language: Mapped[str] = mapped_column(String(5), default="he")
    vat_rate: Mapped[Decimal | None] = mapped_column(RATE_NUMERIC, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    business: Mapped[Business] = relationship(back_populates="locations")
    devices: Mapped[list[Device]] = relationship(back_populates="location")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email_lower", text("lower(email)"), unique=True),)

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


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (Index("ix_devices_token_hash", "token_hash", unique=True),)

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    location: Mapped[Location] = relationship(back_populates="devices")


Outbox = declare_outbox(Base, "auth_outbox")
