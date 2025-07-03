#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# 使用 -c 标志明确指定 alembic.ini 的路径
# 这是解决 "No 'script_location' key found" 问题的最终方法
alembic -c migrations/alembic.ini upgrade head