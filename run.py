# run.py (CORRECTED FOR PRODUCTION)

import os
from dotenv import load_dotenv
from learning_logger import create_app

# 加载 .env 文件
load_dotenv()

# --- 核心修正 ---
# 从环境变量 'FLASK_ENV' 中获取配置名称。
# 如果未设置，则默认为 'default' (也就是 development)。
# 服务器平台（如 Render）会自动将此变量设置为 'production'。
config_name = os.getenv('FLASK_ENV', 'default')
print(f"<<<<< USING CONFIG: {config_name} >>>>>")

# 创建 app 实例
app = create_app(config_name)

# 这个 if 语句是本地开发的入口
# 在 Gunicorn 部署时，这个块不会被执行
if __name__ == '__main__':
    app.run()