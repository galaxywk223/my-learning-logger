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
    # We will set the URI in init_app to ensure os.environ is populated.
    SQLALCHEMY_DATABASE_URI = None

    @staticmethod
    def init_app(app):
        # --- FIX START: Move the logic here ---
        # This code now runs when the app is being created,
        # ensuring Render's environment variables are available.
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        # Set the configuration on the app object
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        # --- FIX END ---


# 将配置类组织在一个字典中，方便根据环境变量选择
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}