# config.py (Final fix for production environment variable loading)

import os

# 获取项目根目录的绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    基础配置类。
    """
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    MATPLOTLIB_BACKEND = 'Agg'

    @staticmethod
    def init_app(app):
        # This method can be used for app-specific initialization
        pass


class DevelopmentConfig(Config):
    """
    开发环境配置。
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app-dev.db')


class TestingConfig(Config):
    """
    测试环境配置。
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MATPLOTLIB_BACKEND = 'Agg'


class ProductionConfig(Config):
    """
    生产环境配置。
    """
    # --- 最终修复：在这里直接、立即地读取环境变量 ---
    # 这能确保像 `flask db upgrade` 这样的构建命令
    # 在第一时间就能获取到正确的数据库地址。
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url


# 将配置类组织在一个字典中，方便根据环境变量选择
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
