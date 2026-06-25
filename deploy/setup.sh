#!/bin/bash
# ============================================================
# FamilyChat 一键部署脚本
# 用法: bash deploy/setup.sh
# ============================================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================
# 检查环境
# ============================================================
info "检查系统环境..."

# Python
if ! command -v python3 &> /dev/null; then
    err "Python3 未安装，请先安装: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
ok "Python: $PYTHON_VERSION"

# 检查 .env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        warn ".env 不存在，正在从 .env.example 复制..."
        cp .env.example .env
        warn "请编辑 .env 文件填入实际配置！"
        echo ""
        echo "  vim .env"
        echo ""
        exit 1
    else
        err ".env 和 .env.example 都不存在"
        exit 1
    fi
fi
ok ".env 配置文件存在"

# ============================================================
# 创建虚拟环境
# ============================================================
if [ ! -d "venv" ]; then
    info "创建 Python 虚拟环境..."
    python3 -m venv venv
    ok "虚拟环境已创建"
else
    ok "虚拟环境已存在"
fi

# 激活虚拟环境
source venv/bin/activate

# ============================================================
# 安装依赖
# ============================================================
info "安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "依赖安装完成"

# ============================================================
# 创建数据目录
# ============================================================
info "创建数据目录..."
mkdir -p data/avatars data/voices data/images
ok "数据目录已创建"

# ============================================================
# 初始化数据库
# ============================================================
info "初始化数据库..."
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from backend.app.models.database import init_db
asyncio.run(init_db())
print('数据库初始化完成')
" 2>/dev/null || warn "数据库将在首次启动时自动初始化"

# ============================================================
# 安装 OpenClaw（如果未安装）
# ============================================================
if ! command -v openclaw &> /dev/null; then
    warn "OpenClaw 未安装"
    info "如需安装 OpenClaw，请运行: npm install -g openclaw"
else
    OC_VERSION=$(openclaw --version 2>/dev/null | head -1)
    ok "OpenClaw: $OC_VERSION"
fi

# ============================================================
# 完成
# ============================================================
echo ""
echo "============================================================"
ok "🎉 FamilyChat 部署完成！"
echo "============================================================"
echo ""
echo "  启动服务:"
echo "    python run.py"
echo ""
echo "  或后台运行:"
echo "    nohup python run.py > familychat.log 2>&1 &"
echo ""
echo "  或使用 systemd（需要 root）:"
echo "    sudo cp deploy/familychat.service /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable familychat"
echo "    sudo systemctl start familychat"
echo ""
echo "  访问地址:"
echo "    http://localhost:8000"
echo "    API 文档: http://localhost:8000/docs"
echo ""
echo "  如需配置 OpenClaw，请参考:"
echo "    deploy/OPENCLAW_SETUP.md"
echo ""
