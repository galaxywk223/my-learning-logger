# init_db.py
from app import app, db

# 这会确保在应用上下文中执行
with app.app_context():
    print("正在创建数据库表...")
    db.create_all()
    print("数据库表创建成功！")