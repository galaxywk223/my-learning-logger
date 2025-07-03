#!/usr/bin/env bash
# Exit on error
set -o errexit

# 1. 安装所有依赖包
pip install -r requirements.txt

# 2. 使用 Flask-Migrate 的标准命令来运行数据库迁移
# 这能确保迁移在与您的线上应用完全相同的配置和环境下运行
flask db upgrade