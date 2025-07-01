# learning_logger/__init__.py (集成 Flask-Migrate 后版本)

import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate  # <--- 1. 新增导入
from config import config
import matplotlib

# 初始化扩展，但尚未绑定到具体的 app
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()  # <--- 2. 新增实例

login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'info'


def create_app(config_name='default'):
    """
    应用工厂函数。
    """
    matplotlib.use(config[config_name].MATPLOTLIB_BACKEND)

    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # 将扩展实例与 Flask 应用绑定
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  # <--- 3. 新增初始化调用

    # --- 用户加载函数 ---
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- 注册蓝图 ---
    from .blueprints.main import main_bp
    from .blueprints.records import records_bp
    from .blueprints.charts import charts_bp
    from .blueprints.countdown import countdown_bp
    from .blueprints.auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(charts_bp)
    app.register_blueprint(countdown_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # --- [核心修改] 注册自定义的命令行命令 (这个命令未来可以被 aask db 命令替代) ---
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
        click.echo('可以添加一些默认设置或初始数据。')

    # --- 注册自定义模板过滤器 ---
    from . import helpers
    helpers.setup_template_filters(app)

    return app