# 文件路径: run.py
import os
from dotenv import load_dotenv
from learning_logger import create_app

load_dotenv()

config_name = os.getenv('FLASK_ENV', 'default')
print(f"<<<<< USING CONFIG: {config_name} >>>>>")

app = create_app(config_name)

if __name__ == '__main__':
    app.run()
