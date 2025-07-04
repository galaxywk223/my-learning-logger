# migrations/env.py (最终修复版)

import os
import sys
from logging.config import fileConfig

# ===================================================================
# 核心修复：在导入任何应用模块之前，将项目根目录添加到 Python 路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ===================================================================


from alembic import context
from sqlalchemy import engine_from_config, pool

# 1. 直接导入您的数据库实例 (db) 和所有模型
from learning_logger import db
# noinspection PyUnresolvedReferences
from learning_logger.models import *

# 2. 从环境变量直接读取数据库连接字符串
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise ValueError("DATABASE_URL environment variable is not set. Cannot run migrations.")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)


# 这是 Alembic 的标准配置部分
config = context.config

# 将数据库 URL 设置到 Alembic 的配置中
config.set_main_option('sqlalchemy.url', db_url)

# 将您的模型元数据设置为 Alembic 的目标
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """在“离线”模式下运行迁移。"""
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
    """在“在线”模式下运行迁移。"""
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