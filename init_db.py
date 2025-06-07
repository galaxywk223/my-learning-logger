# 文件: init_db.py (手动重置数据库的最终版本)

from app import app, db

# 使用 app.app_context() 来确保在正确的环境中执行数据库操作
with app.app_context():
    print("--- 手动数据库重置脚本 ---")
    print("警告：此脚本将彻底删除所有数据表，并根据最新的模型重建它们。")

    try:
        print("第 1 步: 正在删除所有旧的数据表...")
        db.drop_all()
        print(">>> 所有表已成功删除。")

        print("第 2 步: 正在根据最新模型代码创建新表...")
        db.create_all()
        print(">>> 新表已成功创建！数据库结构与代码已同步。")

        print("--- 数据库重置成功 ---")

    except Exception as e:
        print(f"在重置过程中发生错误: {e}")