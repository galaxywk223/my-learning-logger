import os
from learning_logger import create_app, db

# 根据环境变量 'FLASK_CONFIG' 选择配置，生产环境默认为 'production'
config_name = os.environ.get('FLASK_CONFIG', 'production')
app = create_app(config_name)


# --- 核心修改 ---
# 将数据库创建逻辑移到这里。
# 这段代码将在每次应用启动时（包括在 Render 上被 Gunicorn 启动时）运行。
# db.create_all() 是一个“幂等”操作，它只会创建尚不存在的表，
# 绝不会删除或覆盖您已有的表和数据，所以可以安全地每次都运行。
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    # 这个代码块只在本地直接运行 `python run.py` 时用于测试
    # 在生产环境 (如 Render) 中，会使用 Gunicorn 启动，不会执行这里。
    app.run(host='0.0.0.0')

