"""Decimal money helpers: quantize at the cent, serialize JSON as numbers."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any

from pydantic import BeforeValidator, PlainSerializer
from sqlalchemy import Numeric

CENTS = Decimal("0.01")
RATE_QUANT = Decimal("0.0001")
MONEY_NUMERIC = Numeric(10, 2)
RATE_NUMERIC = Numeric(5, 4)


def money(x: object) -> Decimal:
    """Round half-up to cents. Always go through `str` so binary floats cannot leak in."""
    value = x if isinstance(x, Decimal) else Decimal(str(x))
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def rate(x: object) -> Decimal:
    value = x if isinstance(x, Decimal) else Decimal(str(x))
    return value.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def _parse_money(value: object) -> Decimal:
    if value is None:
        raise TypeError("money value is required")
    return money(value)


def _parse_optional_money(value: object) -> Decimal | None:
    if value is None:
        return None
    return money(value)


def _parse_rate(value: object) -> Decimal:
    if value is None:
        raise TypeError("rate value is required")
    return rate(value)


def _parse_optional_rate(value: object) -> Decimal | None:
    if value is None:
        return None
    return rate(value)


def _dump_optional(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


Money = Annotated[Decimal, BeforeValidator(_parse_money), PlainSerializer(float, when_used="json")]
OptionalMoney = Annotated[
    Decimal | None,
    BeforeValidator(_parse_optional_money),
    PlainSerializer(_dump_optional, when_used="json"),
]
Rate = Annotated[Decimal, BeforeValidator(_parse_rate), PlainSerializer(float, when_used="json")]
OptionalRate = Annotated[
    Decimal | None,
    BeforeValidator(_parse_optional_rate),
    PlainSerializer(_dump_optional, when_used="json"),
]


def json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def alter_to_numeric(table: str, column: str, precision: int, scale: int) -> None:
    from alembic import op

    op.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} "
        f"TYPE numeric({precision},{scale}) USING {column}::numeric({precision},{scale})"
    )


def alter_to_float(table: str, column: str) -> None:
    from alembic import op

    op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE double precision USING {column}::double precision")
