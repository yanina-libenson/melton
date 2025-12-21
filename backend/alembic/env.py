"""Alembic environment configuration."""

from logging.config import fileConfig

from sqlalchemy import pool

from alembic import context

# Import Base and all models
from app.database import Base
from app.models import (
    Agent,
    Conversation,
    Deployment,
    EncryptedCredential,
    ExecutionTrace,
    Integration,
    Message,
    Tool,
)

# Import settings to get DATABASE_URL_SYNC
from app.config import settings

# this is the Alembic Config object
config = context.config

# Set database URL from environment
config.set_main_option("DATABASE_URL_SYNC", settings.database_url_sync)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using sync engine."""
    from sqlalchemy import engine_from_config

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url_sync

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
