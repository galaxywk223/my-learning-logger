import os

# 获取项目根目录的绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    基础配置类，包含所有应用共享的配置。
    """
    # 从环境变量中获取密钥，并提供一个默认值以防万一
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key-for-flash-messages')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Matplotlib 后端设置
    MATPLOTLIB_BACKEND = 'Agg'

    @staticmethod
    def init_app(app):
        # 可以在这里执行不依赖于具体配置的初始化
        pass


class DevelopmentConfig(Config):
    """
    开发环境配置。
    """
    DEBUG = True
    # 在开发环境中使用本地的 SQLite 数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'learning_logs_dev.db')


class ProductionConfig(Config):
    """
    生产环境配置 (例如在 Render 上部署时使用)。
    """
    DEBUG = False

    # --- MODIFIED: 更健壮的生产数据库URI配置 ---
    # Render 会通过 DATABASE_URL 环境变量提供 PostgreSQL 的连接字符串。
    # 我们从环境变量中获取它。如果没有设置，则默认使用一个本地的 prod.db 文件。
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'learning_logs_prod.db')

    # 如果 DATABASE_URL 是 postgres URL，Heroku/Render 需要我们
    # 将 "postgres://" 替换为 "postgresql://"
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)


# 将配置类组织在一个字典中，方便根据环境变量选择
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
