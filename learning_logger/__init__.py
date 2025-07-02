# learning_logger/__init__.py (Final Corrected Version)

import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config
import matplotlib

# 初始化扩展
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'info'


def create_app(config_name='default'):
    """应用工厂函数。"""
    matplotlib.use(config[config_name].MATPLOTLIB_BACKEND)

    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # 绑定扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # 用户加载函数
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ============================================================================
    # 核心修正：为蓝图注册 URL 前缀
    # ============================================================================
    from .blueprints.main import main_bp
    from .blueprints.records import records_bp
    from .blueprints.charts import charts_bp
    from .blueprints.countdown import countdown_bp
    from .blueprints.auth import auth_bp

    # main_bp 是主页和设置，没有前缀，注册在根URL '/'
    app.register_blueprint(main_bp)

    # 为其他功能模块指定专属的URL前缀
    app.register_blueprint(records_bp, url_prefix='/records')
    app.register_blueprint(charts_bp, url_prefix='/charts')
    app.register_blueprint(countdown_bp, url_prefix='/countdown')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # 注册自定义命令行
    @app.cli.command('init-db')
    @click.option('--drop', is_flag=True, help='先删除已存在的表再创建。')
    def init_db_command(drop):
        """初始化数据库。"""
        from . import models
        if drop:
            click.confirm('这会删除所有数据，确定吗？', abort=True)
            db.drop_all()
            click.echo('已删除所有数据库表。')
        db.create_all()
        click.echo('数据库初始化成功。')

    # 注册自定义模板过滤器
    from . import helpers
    helpers.setup_template_filters(app)

    return app