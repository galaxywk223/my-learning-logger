# migrations/env.py (The Definitive Final Version)
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- THE FINAL FIX ---
# This section directly sets the SQLAlchemy URL from the environment variable.
# It completely bypasses the Flask app's configuration loading during migrations.
# This is the most robust way to ensure migrations run on the correct database in any environment.
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise ValueError("DATABASE_URL environment variable is not set. Cannot run migrations.")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

config.set_main_option('sqlalchemy.url', db_url)
# --- END OF FIX ---


# This part is needed to discover the models, we get it from the Flask-Migrate extension
# We assume the Flask app is created and available in the context attributes
try:
    from flask import current_app
    # This assumes your __init__.py sets up the db object
    # This is the only part that still "touches" the app context, but only for model metadata
    target_metadata = current_app.extensions['migrate'].db.metadata
except (ImportError, AttributeError):
    # Fallback for environments where the app context might not be available
    # You might need to import your models manually here if the above fails
    target_metadata = None


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
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()