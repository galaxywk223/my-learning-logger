# config.py (FINAL SERVER VERSION)
import os

# 获取项目根目录下的 'instance' 文件夹的绝对路径
# 这是存放数据库文件的地方
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
        # 确保 instance 和 uploads 文件夹存在
        os.makedirs(INSTANCE_FOLDER_PATH, exist_ok=True)
        os.makedirs(app.config['MILESTONE_UPLOADS'], exist_ok=True)
        os.makedirs(app.config['BACKGROUND_UPLOADS'], exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    # 开发数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(INSTANCE_FOLDER_PATH, 'learning_logs_dev.db')


class ProductionConfig(Config):
    # --- 核心修正：让生产环境也明确使用 SQLite ---
    # 这样它就不会去读 .env 文件里那个错误的 postgresql 地址了
    # 我们为生产环境指定一个独立的数据库文件，以保证数据安全
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(INSTANCE_FOLDER_PATH, 'learning_logs_prod.db')


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