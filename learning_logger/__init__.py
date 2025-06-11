# learning_logger/__init__.py

import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
import matplotlib

from flask_login import LoginManager

# 初始化 SQLAlchemy 扩展，但尚未绑定到具体的 app
db = SQLAlchemy()
# --- 新增 ---
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # 设置登录页面的端点
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'info'


def create_app(config_name='default'):
    """
    应用工厂函数。
    根据传入的配置名称创建并配置 Flask 应用实例。
    """
    # 设置 Matplotlib 的后端，必须在 pyplot 导入之前完成
    matplotlib.use(config[config_name].MATPLOTLIB_BACKEND)

    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # 从配置对象中加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # 将 SQLAlchemy 实例与 Flask 应用绑定
    db.init_app(app)
    # --- 新增 ---
    login_manager.init_app(app)
    # --- 新增: 用户加载函数 ---
    # 这个函数告诉 Flask-Login 如何根据 session 中存储的用户 ID 找到对应的用户对象
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 注册蓝图
    from .blueprints.main import main_bp
    from .blueprints.records import records_bp
    from .blueprints.charts import charts_bp
    from .blueprints.countdown import countdown_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(charts_bp)
    app.register_blueprint(countdown_bp)

    # --- 新增: 注册认证蓝图 ---
    from .blueprints.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # --- [核心修改] 注册自定义的命令行命令 ---
    @app.cli.command('init-db')
    @click.option('--drop', is_flag=True, help='先删除已存在的表再创建。')
    def init_db_command(drop):
        """初始化数据库。"""
        # 在这里导入模型，确保 SQLAlchemy 能找到它们
        from . import models

        if drop:
            click.confirm('这会删除所有数据，确定吗？', abort=True)
            db.drop_all()
            click.echo('已删除所有数据库表。')

        db.create_all()
        click.echo('数据库初始化成功。')
        # 可以在这里添加一些初始数据
        click.echo('可以添加一些默认设置或初始数据。')

    # 注册自定义模板过滤器
    from . import helpers
    helpers.setup_template_filters(app)

    return app
