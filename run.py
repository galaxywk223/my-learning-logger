# run.py (Simplified for the final deployment fix)
import os
from dotenv import load_dotenv
from learning_logger import create_app

# This will load the .env file for local development
load_dotenv()

# The config name is now reliably determined by the FLASK_ENV environment variable.
# On Render, you should have FLASK_ENV set to 'production'.
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    app.run()