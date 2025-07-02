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
    from .blueprints.motto import motto_bp
    from .blueprints.todo import todo_bp
    from .blueprints.category import category_bp
    from .blueprints.category_charts import category_charts_bp

    # main_bp 是主页和设置，没有前缀，注册在根URL '/'
    app.register_blueprint(main_bp)

    # 为其他功能模块指定专属的URL前缀
    app.register_blueprint(records_bp, url_prefix='/records')
    app.register_blueprint(charts_bp, url_prefix='/charts')
    app.register_blueprint(category_charts_bp, url_prefix='/category_charts')
    app.register_blueprint(countdown_bp, url_prefix='/countdown')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(motto_bp)
    app.register_blueprint(todo_bp)
    app.register_blueprint(category_bp, url_prefix='/categories')

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

    # --- 新增：迁移旧分类数据的命令行工具 ---
    @app.cli.command('migrate-legacy-categories')
    def migrate_legacy_categories_command():
        """将 log_entries.legacy_category 中的数据迁移到新的分类体系中。"""
        # BUG FIX: Added 'Stage' to the import list
        from .models import LogEntry, Category, SubCategory, User, Stage

        click.echo('开始迁移历史分类数据...')

        # 找到所有需要迁移的用户
        users_with_legacy_data = db.session.query(User.id).join(Stage).join(LogEntry).filter(
            LogEntry.legacy_category != None, LogEntry.subcategory_id == None).distinct().all()
        user_ids = [u[0] for u in users_with_legacy_data]

        if not user_ids:
            click.echo('没有找到需要迁移的历史分类数据。')
            return

        for user_id in user_ids:
            user = User.query.get(user_id)
            click.echo(f'正在处理用户：{user.username} (ID: {user.id})')

            # 1. 为用户创建或找到“历史导入数据”大分类
            legacy_cat_name = "历史导入数据"
            legacy_category = Category.query.filter_by(user_id=user.id, name=legacy_cat_name).first()
            if not legacy_category:
                legacy_category = Category(name=legacy_cat_name, user_id=user.id)
                db.session.add(legacy_category)
                db.session.commit()
                click.echo(f'  -> 已创建 “{legacy_cat_name}” 大分类。')

            # 2. 查找该用户所有不重复的旧分类名称
            legacy_names = db.session.query(LogEntry.legacy_category) \
                .join(Stage).filter(Stage.user_id == user.id, LogEntry.legacy_category != None,
                                    LogEntry.subcategory_id == None) \
                .distinct().all()

            legacy_name_strings = [name[0] for name in legacy_names if name[0] and name[0].strip()]

            if not legacy_name_strings:
                click.echo('  -> 用户没有需要迁移的分类名称。')
                continue

            # 3. 为每个旧分类名称创建新的小分类（如果不存在）
            name_to_subcategory_map = {}
            for name in legacy_name_strings:
                sub = SubCategory.query.filter_by(name=name, category_id=legacy_category.id).first()
                if not sub:
                    sub = SubCategory(name=name, category_id=legacy_category.id)
                    db.session.add(sub)
                name_to_subcategory_map[name] = sub
            db.session.commit()
            click.echo(f'  -> 已为 {len(legacy_name_strings)} 个历史分类创建新的小分类条目。')

            # 4. 遍历所有相关日志，更新 subcategory_id
            logs_to_update = LogEntry.query.join(Stage).filter(Stage.user_id == user.id,
                                                               LogEntry.legacy_category != None,
                                                               LogEntry.subcategory_id == None).all()

            count = 0
            for log in logs_to_update:
                if log.legacy_category in name_to_subcategory_map:
                    log.subcategory_id = name_to_subcategory_map[log.legacy_category].id
                    count += 1

            db.session.commit()
            click.echo(f'  -> 成功更新了 {count} 条学习记录的分类。')

        click.echo('数据迁移完成！')

    # 注册自定义模板过滤器
    from . import helpers
    helpers.setup_template_filters(app)

    return app