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
    # --- 核心修正：让生产环境优先使用服务器提供的 DATABASE_URL ---
    # 如果服务器环境变量中没有设置 DATABASE_URL，它才会回退到使用本地的 SQLite 文件。
    # 这修复了与 Render/Heroku 等平台部署时的数据库连接问题。
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