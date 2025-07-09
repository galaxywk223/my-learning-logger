# learning_logger/__init__.py (已修复 CSRF 初始化问题)

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect # 1. 新增: 导入 CSRFProtect
from config import config
import matplotlib

# 2. 初始化扩展 (新增 csrf)
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect() # 新增

login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'info'


def create_app(config_name=os.getenv('FLASK_ENV', 'default')):
    """标准的应用工厂函数。"""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # 3. 将扩展绑定到 app (新增 csrf.init_app)
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app) # 新增

    # 4. 在应用上下文中注册蓝图和用户加载器
    with app.app_context():
        # 导入蓝图
        from .blueprints.main import main_bp
        from .blueprints.records import records_bp
        from .blueprints.charts import charts_bp
        from .blueprints.countdown import countdown_bp
        from .blueprints.auth import auth_bp
        from .blueprints.motto import motto_bp
        from .blueprints.todo import todo_bp
        from .blueprints.category import category_bp
        from .blueprints.category_charts import category_charts_bp
        from .blueprints.milestone import milestone_bp
        from .blueprints.daily_plan import daily_plan_bp

        # 注册蓝图
        app.register_blueprint(main_bp)
        app.register_blueprint(records_bp, url_prefix='/records')
        app.register_blueprint(charts_bp, url_prefix='/charts')
        app.register_blueprint(category_charts_bp, url_prefix='/category_charts')
        app.register_blueprint(countdown_bp, url_prefix='/countdown')
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(motto_bp)
        app.register_blueprint(todo_bp)
        app.register_blueprint(category_bp, url_prefix='/categories')
        app.register_blueprint(milestone_bp, url_prefix='/milestones')
        app.register_blueprint(daily_plan_bp, url_prefix='/daily-plan')

        # 注册用户加载器
        from .models import User
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        # 注册自定义模板过滤器
        from . import helpers
        helpers.setup_template_filters(app)

    return app
