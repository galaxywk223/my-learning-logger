#!/bin/bash

# --- 脚本说明 ---
# 功能: 自动从Gitee拉取最新代码并重启应用
# 正确的项目路径: /var/www/my-learning-logger

echo "   1/3: 开始更新... 正在进入项目目录..."
# 进入您的项目实际目录，如果失败则退出脚本
cd /var/www/my-learning-logger || { echo "❌ 错误：无法进入项目目录 /var/www/my-learning-logger"; exit 1; }

echo "   2/3: 正在从 Gitee 拉取最新代码 (main分支)..."
# 从 Gitee 的 main 分支拉取代码
# 如果您的主分支是 master，请把下面的 main 改成 master
git pull origin main

echo "   3/3: 代码拉取完成，正在重启 Gunicorn 服务..."
# 使用 systemd 重启 gunicorn 服务
sudo systemctl restart gunicorn.service

# 等待2秒，然后检查服务状态，确保重启成功
sleep 2
echo "✅ 更新完成！检查服务最新状态："
systemctl status gunicorn.service --no-pager -l                                                                                                             ~                                                                                                                       ~                                                                                                                       ~