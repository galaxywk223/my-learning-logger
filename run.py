# run.py (FINAL CORRECTED VERSION)
import os
from dotenv import load_dotenv
from learning_logger import create_app

# 加载 .env 文件
load_dotenv()

# 这部分只在直接运行 `python run.py` 时执行
if __name__ == '__main__':
    # 在本地或其他环境，我们仍然可以依赖 FLASK_ENV，默认为 development
    config_name = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_name)
    app.run()