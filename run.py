# run.py (DEFINITIVE DEBUG FIX)
print("<<<<< HELLO, I AM THE NEW RUN.PY FILE! >>>>>")

import os
from dotenv import load_dotenv
from learning_logger import create_app

# 加载 .env 文件
load_dotenv()

# 为了本地开发的稳定性，我们强制使用 'development' 配置
config_name = 'development'
print(f"<<<<< USING CONFIG: {config_name} >>>>>")

# 创建 app 实例
app = create_app(config_name)

# 这个 if 语句是本地开发的入口
if __name__ == '__main__':
    # --- 核心修正 ---
    # 强制 debug=True 来覆盖所有其他设置。
    # 这将确保应用始终以调试模式运行，从而激活日志记录和自动重载。
    print("<<<<< FORCING app.run(debug=True) >>>>>")
    app.run(debug=True)