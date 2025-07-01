# config.py (清理后最终版)

import os

# 获取项目根目录的绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    基础配置类，只定义配置的名称，不包含任何硬编码的值。
    """
    # 如果在 .env 中未设置 SECRET_KEY，这里会是 None，Flask会报错，这是期望的行为。
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    MATPLOTLIB_BACKEND = 'Agg'

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """
    开发环境配置。
    """
    DEBUG = True
    # 完全依赖 .env 文件来提供数据库URI
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL')


class TestingConfig(Config):
    """
    测试环境配置。
    测试配置保持独立，不依赖 .env 文件。
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MATPLOTLIB_BACKEND = 'Agg'


class ProductionConfig(Config):
    """
    生产环境配置。
    """
    DEBUG = False
    MATPLOTLIB_BACKEND = 'Agg'
    # 完全依赖环境变量 (例如由 Render, Heroku 提供)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)


# 将配置类组织在一个字典中，方便根据环境变量选择
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}