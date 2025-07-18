# config.py (REVISED FOR PRODUCTION)
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    MATPLOTLIB_BACKEND = 'Agg'
    SQLALCHEMY_ECHO = False # In production, this should generally be False

    UPLOAD_FOLDER_BASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MILESTONE_UPLOADS = os.path.join(UPLOAD_FOLDER_BASE, 'milestones')
    BACKGROUND_UPLOADS = os.path.join(UPLOAD_FOLDER_BASE, 'backgrounds')

    @staticmethod
    def init_app(app):
        # Create upload directories if they don't exist
        os.makedirs(app.config['MILESTONE_UPLOADS'], exist_ok=True)
        os.makedirs(app.config['BACKGROUND_UPLOADS'], exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True # Enable query logging for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance',
                                                          'learning_logs_dev.db')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    # --- 核心修正：让生产环境也使用 SQLite 数据库 ---
    # 我们直接复用和开发环境一样的逻辑来定位数据库文件。
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance',
                                                          'learning_logs_prod.db') # 使用一个不同的文件名以区分


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}