#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# 使用最标准的 Flask 命令来更新数据库。
# 它会自动在项目根目录寻找 alembic.ini 文件。
flask db upgrade