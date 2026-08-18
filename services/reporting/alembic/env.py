"""Alembic migration environment for the reporting service.

Reporting's SQLAlchemy `Base.metadata` also contains trimmed, read-only mirror models
(`User`, `Location`, `Order`, `OrderItem`) for tables owned/migrated by `auth`/`ordering` —
all services share the same physical Postgres database with no schema separation (see
docs/microservices-plan.md §4). This service's migration chain must only ever create/alter
`event_log`, the one table reporting truly owns; the `include_object` filter below enforces
that so `alembic revision --autogenerate` never tries to manage a table another service
owns/migrates.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.db import models  # noqa: F401 — ensure all models are registered on Base.metadata
from app.db.session import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables this service's Alembic chain is allowed to create/alter. Everything else on
# Base.metadata (users, locations, orders, order_items) is a read-only mirror owned and
# migrated by another service (auth/ordering) and must be left alone here.
REPORTING_OWNED_TABLES = {"event_log"}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in REPORTING_OWNED_TABLES
    if hasattr(object, "table") and object.table is not None:
        return object.table.name in REPORTING_OWNED_TABLES
    return True


def get_url() -> str:
    return settings.DATABASE_URL


VERSION_TABLE = "alembic_version_reporting"


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object, version_table=VERSION_TABLE)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
