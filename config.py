# config.py (已修复CSRF漏洞)
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # --- 核心改动 1: 默认启用 CSRF 保护 ---
    # 将此项从 False 改为 True，确保所有配置默认都是安全的。
    WTF_CSRF_ENABLED = True
    MATPLOTLIB_BACKEND = 'Agg'
    MILESTONE_UPLOADS = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads/milestones')

    @staticmethod
    def init_app(app):
        # This method is called by create_app, so it must exist.
        # We can leave it empty if no special initialization is needed.
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app-dev.db')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # --- 核心改动 2: 仅在测试配置中禁用 CSRF ---
    # 这对于运行自动化测试是必要的，并且是安全的。
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    # 生产环境将继承 Config 中的 WTF_CSRF_ENABLED = True，这是正确的。
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace("postgres://", "postgresql://", 1)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
