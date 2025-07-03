# migrations/env.py (最终修复版)

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ===================================================================
# 核心修复：让 Alembic 直接知道您的模型和数据库
# ===================================================================

# 1. 直接导入您的数据库实例 (db) 和所有模型
#    这样 Alembic 就能知道数据库应该是什么样的结构
from learning_logger import db
# noinspection PyUnresolvedReferences
from learning_logger.models import *

# 2. 从环境变量直接读取数据库连接字符串
#    这确保了无论在何种环境下，Alembic 都能连上正确的数据库
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise ValueError("DATABASE_URL environment variable is not set. Cannot run migrations.")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
# ===================================================================


# 这是 Alembic 的标准配置部分
config = context.config

# 将数据库 URL 设置到 Alembic 的配置中
config.set_main_option('sqlalchemy.url', db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

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