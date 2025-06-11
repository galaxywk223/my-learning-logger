# /run.py

import os
from learning_logger import create_app, db

# 根据环境变量 'FLASK_CONFIG' 选择配置，默认为 'default'
config_name = os.environ.get('FLASK_CONFIG', 'default')
app = create_app(config_name)

if __name__ == '__main__':
    # 在应用上下文中创建所有数据库表，如果它们不存在的话
    with app.app_context():
        db.create_all()

    # 运行应用
    # 在生产环境 (如 Render) 中，会使用 Gunicorn 启动，而不是这里
    app.run(host='0.0.0.0', port=5000)