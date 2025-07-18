# config.py (REVISED FOR DEBUGGING)
import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    MATPLOTLIB_BACKEND = 'Agg'

    # --- NEW: Add this line to enable SQL query logging ---
    SQLALCHEMY_ECHO = True

    # Define the base path for uploads inside the 'static' folder
    UPLOAD_FOLDER_BASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')

    # Path for milestone attachments
    MILESTONE_UPLOADS = os.path.join(UPLOAD_FOLDER_BASE, 'milestones')

    # NEW: Path for custom background images
    BACKGROUND_UPLOADS = os.path.join(UPLOAD_FOLDER_BASE, 'backgrounds')

    @staticmethod
    def init_app(app):
        # This method is called by create_app, so it must exist.
        # We can leave it empty if no special initialization is needed.
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance',
                                                          'learning_logs_dev.db')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace("postgres://", "postgresql://", 1)
    # --- IMPORTANT: Ensure logging is off in production ---
    SQLALCHEMY_ECHO = False


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}