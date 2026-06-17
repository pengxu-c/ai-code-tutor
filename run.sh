#!/bin/bash
# AI 编程题讲解机器人 - 启动脚本
# 用法：bash run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  AI 编程题讲解机器人"
echo "  错解代码诊断与变式训练系统"
echo "=========================================="
echo ""

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到 python3，请安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本：$PYTHON_VERSION"

# 检查是否已安装依赖
if ! python3 -c "import gradio" 2>/dev/null; then
    echo ""
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
    echo "依赖安装完成！"
fi

# 创建日志目录
mkdir -p logs

echo ""
echo "正在启动服务..."
echo "访问地址：http://localhost:7860"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="

python3 app.py
