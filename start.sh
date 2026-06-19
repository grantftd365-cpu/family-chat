#!/bin/bash
# FamilyChat 启动脚本

echo "🏠 FamilyChat 启动中..."

# 检查依赖
echo "📦 检查依赖..."
pip3 install -q fastapi uvicorn python-jose passlib python-multipart aiosqlite httpx pyyaml loguru python-dotenv edge-tts 2>/dev/null

# 创建数据目录
mkdir -p data/uploads data/voices data/logs

# 启动服务
echo "🚀 启动服务..."
python3 run.py &
SERVER_PID=$!

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 3

# 检查服务是否运行
if curl -s http://localhost:8000/api/status > /dev/null 2>&1; then
    echo "✅ 服务已启动！"
    echo ""
    echo "🌐 访问: http://localhost:8000"
    echo "📧 测试账号: grantftd365@gmail.com"
    echo ""
    echo "运行测试: python3 test_e2e.py"
    echo ""
    
    # 如果传了 --test 参数，自动运行测试
    if [ "$1" = "--test" ]; then
        echo "🧪 运行端到端测试..."
        python3 test_e2e.py
    fi
    
    # 保持服务运行
    wait $SERVER_PID
else
    echo "❌ 服务启动失败！"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi
