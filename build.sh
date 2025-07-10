#!/usr/bin/env bash
# Exit on error
set -o errexit

# Step 1: Install Python dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Step 2: Run database migrations
# This will apply the new sequence reset migration on the next deploy.
echo "Running database migrations..."
flask db upgrade
