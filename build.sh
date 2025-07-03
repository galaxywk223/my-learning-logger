#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# NEW STEP: Create all tables directly from the models.
# This ensures the database schema exists before migrations are applied.
# The 'init-db' command is defined in your learning_logger/__init__.py file.
flask init-db

# Run database migrations to bring the schema to the latest version.
# This will now run on top of the existing tables, ensuring everything is up-to-date.
flask db upgrade