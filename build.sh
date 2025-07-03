#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations. This is the single source of truth for the database schema.
# On a new, empty database, it will create all tables from scratch and apply
# all subsequent migrations to bring it to the latest version.
flask db upgrade