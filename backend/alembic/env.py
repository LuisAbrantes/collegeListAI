"""
Alembic Environment Configuration for College List AI

Customized for:
- Async SQLAlchemy/SQLModel
- Environment variable for DATABASE_URL
- Exclude Supabase system tables from autogenerate
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Add the backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import settings and models
from app.config.settings import settings
from sqlmodel import SQLModel

# Import all models to register them with SQLModel.metadata
from app.infrastructure.db.models import (
    UserProfile,
    College,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLModel metadata for autogenerate
target_metadata = SQLModel.metadata

# Tables to exclude from autogenerate (Supabase system tables)
EXCLUDE_TABLES = {
    "schema_migrations",
    "buckets",
    "objects",
    "s3_multipart_uploads",
    "s3_multipart_uploads_parts",
    "secrets",
    "decrypted_secrets",
    "refresh_tokens",
    "audit_log_entries",
    "instances",
    "sessions",
    "mfa_factors",
    "mfa_challenges",
    "mfa_amr_claims",
    "sso_providers",
    "sso_domains",
    "saml_providers",
    "saml_relay_states",
    "flow_state",
    "identities",
    "users",
    "one_time_tokens",
}


def include_object(object, name, type_, reflected, compare_to):
    """Filter objects for autogenerate."""
    if type_ == "table":
        # Exclude Supabase system tables
        if name in EXCLUDE_TABLES:
            return False
        # Exclude tables in auth, storage, realtime schemas
        schema = getattr(object, "schema", None)
        if schema in ("auth", "storage", "realtime", "extensions", "graphql", "graphql_public"):
            return False
    return True


def get_url():
    """Get database URL from settings or environment."""
    url = settings.database_url
    if not url:
        url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Convert to async driver if needed
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    Generates SQL script without database connection.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode with async engine.
    """
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
