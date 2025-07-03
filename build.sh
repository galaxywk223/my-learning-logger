#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# 直接使用 alembic 命令更新数据库到最新版本
# 这比 'flask db upgrade' 更直接、更稳定
alembic upgrade head