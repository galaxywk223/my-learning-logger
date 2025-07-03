#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# 使用-c标志明确指定alembic.ini的路径，并执行迁移
alembic -c migrations/alembic.ini upgrade head