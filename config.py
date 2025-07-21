# 文件路径: config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))
INSTANCE_FOLDER_PATH = os.path.join(basedir, 'instance')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-for-development'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    MATPLOTLIB_BACKEND = 'Agg'
    SQLALCHEMY_ECHO = False

    UPLOAD_FOLDER_BASE = os.path.join(basedir, 'static', 'uploads')
    MILESTONE_UPLOADS = os.path.join(UPLOAD_FOLDER_BASE, 'milestones')
    BACKGROUND_UPLOADS = os.path.join(UPLOAD_FOLDER_BASE, 'backgrounds')

    @staticmethod
    def init_app(app):
        os.makedirs(INSTANCE_FOLDER_PATH, exist_ok=True)
        os.makedirs(app.config['MILESTONE_UPLOADS'], exist_ok=True)
        os.makedirs(app.config['BACKGROUND_UPLOADS'], exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(INSTANCE_FOLDER_PATH, 'learning_logs_dev.db')


class ProductionConfig(Config):
    # 从名为 'DATABASE_URL' 的环境变量中获取数据库连接字符串
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(INSTANCE_FOLDER_PATH, 'learning_logs_prod.db')

    # --- 这里是核心修改 ---
    # 从名为 'UPLOAD_FOLDER_BASE' 的环境变量获取上传根目录
    # 如果环境变量不存在，则提供一个备用路径
    UPLOAD_FOLDER_BASE = os.environ.get('UPLOAD_FOLDER_BASE') or '/var/www/learning_logger_uploads'
    MILESTONE_UPLOADS = os.path.join(UPLOAD_FOLDER_BASE, 'milestones')
    BACKGROUND_UPLOADS = os.path.join(UPLOAD_FOLDER_BASE, 'backgrounds')
    # --- 修改结束 ---


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
