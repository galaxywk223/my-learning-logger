# run.py (Final version for robust deployment)

import os
from dotenv import load_dotenv
from learning_logger import create_app

# --- MODIFICATION START ---
# This section is now smarter about detecting the environment.

# Load .env file only if it exists (for local development)
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

# If running on Render, always use the 'production' config.
# Render automatically sets the 'RENDER' environment variable.
if os.environ.get('RENDER'):
    config_name = 'production'
else:
    # For local execution, fall back to FLASK_ENV or 'default'.
    config_name = os.environ.get('FLASK_ENV', 'default')

app = create_app(config_name)

# The `db.create_all()` call has been removed.
# Database schema is now managed exclusively by Flask-Migrate.
# --- MODIFICATION END ---


if __name__ == '__main__':
    # This block is for local testing via `python run.py`
    app.run(host='0.0.0.0')