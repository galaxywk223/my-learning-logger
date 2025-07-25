#!/bin/bash

# set -e 命令能确保脚本中任何一个命令执行失败，整个脚本就会立刻退出，这对于自动化非常重要。
set -e

echo "--- 部署脚本开始执行 ---"
echo "  - 目标服务: gunicorn.service"
echo "  - 操作: 重启服务"

# 1. 使用 systemd 重启 gunicorn 服务
sudo systemctl restart gunicorn.service

# 2. 等待几秒钟，给服务一点启动时间
echo "  - 等待 3 秒..."
sleep 3

# 3. 检查服务是否真的处于 "active" (运行中) 状态
#    is-active 命令如果服务正常则返回0，否则返回非0，配合 set -e 就能验证重启是否成功
echo "  - 验证服务状态..."
sudo systemctl is-active --quiet gunicorn.service

echo "✅ 部署成功! gunicorn.service 已成功启动并正在运行。"

# 4. (可选) 在日志的最后打印详细状态，方便回看
echo "--- 服务详细状态如下 ---"
sudo systemctl status gunicorn.service --no-pager -l