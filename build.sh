#!/usr/bin/env bash
# Exit on error
set -o errexit

# 在构建阶段，我们只安装依赖包
pip install -r requirements.txt