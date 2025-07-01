# run.py (最终健壮版)

import os
from dotenv import load_dotenv
from learning_logger import create_app, db

# 明确地构建 .env 文件的绝对路径
# 这可以确保无论从哪里运行脚本，都能正确找到 .env 文件
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')

# 加载指定路径的 .env 文件
load_dotenv(dotenv_path=dotenv_path)


# 现在 os.environ.get() 可以读取到 .env 文件中设置的变量了
# 我们在 .env 文件中设置了 FLASK_ENV=development
# 如果 .env 不存在或未设置，则默认为 'default'
config_name = os.environ.get('FLASK_ENV', 'default')
app = create_app(config_name)


# 这段代码将在每次应用启动时运行，确保数据库表已创建
# db.create_all() 是一个“幂等”操作，只会创建尚不存在的表
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    # 这个代码块只在本地直接运行 `python run.py` 时用于测试
    app.run(host='0.0.0.0')