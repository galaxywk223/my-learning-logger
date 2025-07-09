# run.py
import os
from dotenv import load_dotenv
from learning_logger import create_app

# 加载 .env 文件
load_dotenv()

# 从环境中获取配置名称, Render 默认会将其设置为 'production'
config_name = os.environ.get('FLASK_ENV', 'production')

# 在文件的顶层创建 app 实例，这样 Gunicorn 才能找到它
app = create_app(config_name)

# 这个 if 语句现在只用于本地开发时直接运行文件
if __name__ == '__main__':
    app.run()