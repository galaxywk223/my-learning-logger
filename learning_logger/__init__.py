# learning_logger/__init__.py (MODIFIED TO FORCE LOGGING)

import os
import logging  # <--- NEW: Import the logging module
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import config
import matplotlib

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'info'


def create_app(config_name=os.getenv('FLASK_ENV', 'default')):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # --- NEW: Forcefully configure logging ---
    # This block directly manipulates the logger to ensure output, bypassing file configurations.
    if app.config.get('SQLALCHEMY_ECHO'):
        # Get the logger for SQLAlchemy's engine
        sql_logger = logging.getLogger('sqlalchemy.engine')
        # Set its level to INFO to capture query statements
        sql_logger.setLevel(logging.INFO)

        # Check if it already has handlers to avoid duplicate output
        if not sql_logger.handlers:
            # Create a handler to write to the console (standard error)
            console_handler = logging.StreamHandler()
            # Set a formatter for the logs
            formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
            console_handler.setFormatter(formatter)
            # Add the handler to the logger
            sql_logger.addHandler(console_handler)

        print("=" * 50)
        print("INFO: Logging for 'sqlalchemy.engine' has been programmatically enabled.")
        print("=" * 50)
    # --- END of new logging configuration ---

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    with app.app_context():
        # --- BLUEPRINT REGISTRATION ---
        from .blueprints.main import main_bp
        from .blueprints.records import records_bp
        from .blueprints.charts import charts_bp
        from .blueprints.countdown import countdown_bp
        from .blueprints.auth import auth_bp
        from .blueprints.todo import todo_bp
        from .blueprints.milestone import milestone_bp
        from .blueprints.daily_plan import daily_plan_bp
        from .blueprints.category_charts import category_charts_bp
        from .blueprints.stage import stage_bp
        from .blueprints.category import category_management_bp
        from .blueprints.motto_management import motto_management_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(records_bp, url_prefix='/records')
        app.register_blueprint(charts_bp, url_prefix='/charts')
        app.register_blueprint(countdown_bp, url_prefix='/countdown')
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(todo_bp)
        app.register_blueprint(milestone_bp, url_prefix='/milestones')
        app.register_blueprint(daily_plan_bp, url_prefix='/daily-plan')
        app.register_blueprint(category_charts_bp, url_prefix='/category_charts')
        app.register_blueprint(stage_bp)
        app.register_blueprint(category_management_bp)
        app.register_blueprint(motto_management_bp)

        # --- MODELS & LOGIN MANAGER ---
        from .models import User, Setting
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        # --- CONTEXT PROCESSOR ---
        @app.context_processor
        def inject_user_settings():
            if current_user.is_authenticated:
                settings_query = Setting.query.filter_by(user_id=current_user.id).all()
                user_settings = {setting.key: setting.value for setting in settings_query}
                return dict(user_settings=user_settings)
            return dict(user_settings={})

        # --- TEMPLATE FILTERS ---
        from . import helpers
        helpers.setup_template_filters(app)

    return app