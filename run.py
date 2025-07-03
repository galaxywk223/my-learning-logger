# run.py (更新后的版本)
import os
from dotenv import load_dotenv
from learning_logger import create_app

# 加载 .env 文件，这主要用于本地开发
load_dotenv()

# 通过检查 Render 平台自带的 RENDER 环境变量来判断是否在生产环境
# 这是一个比依赖 FLASK_ENV 更可靠的方法
if os.environ.get('RENDER') == 'true':
    config_name = 'production'
else:
    # 在本地或其他环境，我们仍然可以依赖 FLASK_ENV，默认为 development
    config_name = os.environ.get('FLASK_ENV', 'development')

# 使用识别出的配置名称创建应用实例
app = create_app(config_name)

if __name__ == '__main__':
    # 这部分主要用于本地启动，Gunicorn 在生产环境会直接与 app 对象交互
    app.run()