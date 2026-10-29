"""Alembic include_object helper that ignores other services' tables and FKs."""

from __future__ import annotations

from collections.abc import Callable, Collection
from typing import Any


def owned_include_object(owned_tables: Collection[str]) -> Callable[..., bool]:
    owned = set(owned_tables)

    def include_object(object: Any, name: str, type_: str, reflected: bool, compare_to: Any) -> bool:
        if type_ == "table":
            return name in owned
        table = getattr(object, "table", None)
        if table is not None and table.name not in owned:
            return False
        if type_ == "foreign_key_constraint":
            for element in getattr(object, "elements", ()) or ():
                column = getattr(element, "column", None)
                remote = getattr(column, "table", None) if column is not None else None
                if remote is not None and remote.name not in owned:
                    return False
        return table is None or table.name in owned

    return include_object
