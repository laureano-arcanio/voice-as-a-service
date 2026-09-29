from alembic import context

from app import models  # noqa: F401  (registra las tablas en Base.metadata)
from app.config import settings
from app.db import Base, make_engine

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=settings.db_dsn, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = context.config.attributes.get("connection") or make_engine(settings.db_dsn)
    if hasattr(connectable, "connect"):
        with connectable.connect() as connection:
            _run(connection)
    else:
        _run(connectable)


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
