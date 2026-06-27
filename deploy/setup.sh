#!/bin/bash
# ============================================================
# FamilyChat 阿里云一键部署脚本
# 用法: sudo bash deploy/setup.sh
# 前置条件: 阿里云 ECS / CentOS 7+ / Ubuntu 20+ / Alinux 3
# ============================================================

set -euo pipefail

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[✅]${NC} $1"; }
warn()  { echo -e "${YELLOW}[⚠️]${NC} $1"; }
err()   { echo -e "${RED}[❌]${NC} $1"; }
step()  { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# ============================================================
# 0. 交互式配置（如果 .env 不存在）
# ============================================================
step "Step 0: 配置检查"

generate_secret_key() {
    python3 -c "import secrets; print(secrets.token_hex(32))"
}

if [ ! -f .env ]; then
    info "首次部署，开始配置向导..."
    echo ""

    # 生成 SECRET_KEY
    SECRET_KEY=$(generate_secret_key)

    # 读取域名
    read -p "🌐 请输入域名 (例: chat.yourdomain.com，留用 IP): " DOMAIN
    DOMAIN=${DOMAIN:-$(curl -s ifconfig.me 2>/dev/null || echo "localhost")}

    # 读取 LLM 配置
    echo ""
    echo "  支持的 LLM 提供商:"
    echo "    1) DeepSeek (推荐，便宜好用)"
    echo "    2) OpenAI (GPT-4o)"
    echo "    3) 智谱 AI (GLM-4)"
    echo "    4) 通义千问 (Qwen)"
    echo "    5) 本地模型 (Ollama)"
    echo "    6) 稍后配置"
    read -p "  选择 [1]: " LLM_CHOICE
    LLM_CHOICE=${LLM_CHOICE:-1}

    case $LLM_CHOICE in
        1) LLM_PROVIDER="deepseek"; LLM_BASE_URL="https://api.deepseek.com/v1"; LLM_MODEL="deepseek-chat" ;;
        2) LLM_PROVIDER="openai"; LLM_BASE_URL="https://api.openai.com/v1"; LLM_MODEL="gpt-4o" ;;
        3) LLM_PROVIDER="zhipu"; LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4"; LLM_MODEL="glm-4" ;;
        4) LLM_PROVIDER="qwen"; LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"; LLM_MODEL="qwen-max" ;;
        5) LLM_PROVIDER="local"; LLM_BASE_URL="http://localhost:11434/v1"; LLM_MODEL="ollama/any" ;;
        *) LLM_PROVIDER="deepseek"; LLM_BASE_URL="https://api.deepseek.com/v1"; LLM_MODEL="deepseek-chat" ;;
    esac

    if [ "$LLM_CHOICE" != "6" ]; then
        read -p "  请输入 LLM API Key: " LLM_API_KEY
    else
        LLM_API_KEY=""
    fi

    # 微信配置（可选）
    echo ""
    read -p "📱 是否配置微信登录？(y/N): " WX_CHOICE
    if [ "$WX_CHOICE" = "y" ] || [ "$WX_CHOICE" = "Y" ]; then
        read -p "  WX_APPID: " WX_APPID
        read -p "  WX_SECRET: " WX_SECRET
    else
        WX_APPID=""
        WX_SECRET=""
    fi

    # CORS 配置
    if [ "$DOMAIN" != "localhost" ] && [ "$DOMAIN" != "$(curl -s ifconfig.me 2>/dev/null)" ]; then
        CORS_ORIGINS="https://${DOMAIN},http://${DOMAIN}"
    else
        CORS_ORIGINS="http://${DOMAIN}:8000,http://localhost:8000"
    fi

    # 写入 .env
    cat > .env << EOF
# ============================================================
# FamilyChat 生产环境配置
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================

# === 安全配置（必填）===
SECRET_KEY=${SECRET_KEY}

# === CORS 允许的域名 ===
CORS_ORIGINS=${CORS_ORIGINS}

# === LLM 配置 ===
LLM_PROVIDER=${LLM_PROVIDER}
LLM_API_KEY=${LLM_API_KEY}
LLM_BASE_URL=${LLM_BASE_URL}
LLM_MODEL=${LLM_MODEL}
LLM_TEMPERATURE=0.8

# === 服务器配置 ===
HOST=0.0.0.0
PORT=8000

# === 微信登录（可选）===
WX_APPID=${WX_APPID}
WX_SECRET=${WX_SECRET}
WX_OAUTH_SCOPE=snsapi_userinfo

# === 时区 ===
TZ=Asia/Shanghai
EOF

    ok ".env 配置文件已生成"
    echo ""
    warn "请检查 .env 文件确认配置正确:"
    echo "  cat .env"
    echo ""
else
    ok ".env 配置文件已存在"

    # 检查 SECRET_KEY
    if grep -q "^SECRET_KEY=$" .env || grep -q "SECRET_KEY=change" .env; then
        err "SECRET_KEY 未设置或使用了默认值！"
        NEW_KEY=$(generate_secret_key)
        sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${NEW_KEY}/" .env
        ok "已自动生成新的 SECRET_KEY"
    fi

    # 检查 LLM_API_KEY
    if ! grep -q "^LLM_API_KEY=.\+" .env; then
        warn "LLM_API_KEY 未设置，AI 数字人功能将不可用"
    fi

    # 提取域名
    DOMAIN=$(grep CORS_ORIGINS .env | head -1 | sed 's/.*https*:\/\///' | sed 's/[,/:].*//' || echo "localhost")
fi

# ============================================================
# 1. 系统依赖
# ============================================================
step "Step 1: 安装系统依赖"

# 检测包管理器
if command -v apt-get &> /dev/null; then
    PKG_MGR="apt"
    apt-get update -qq
    INSTALL_CMD="apt-get install -y -qq"
elif command -v yum &> /dev/null; then
    PKG_MGR="yum"
    INSTALL_CMD="yum install -y -q"
elif command -v dnf &> /dev/null; then
    PKG_MGR="dnf"
    INSTALL_CMD="dnf install -y -q"
else
    err "不支持的包管理器，请手动安装 Python3、Nginx、ffmpeg"
    exit 1
fi
info "包管理器: $PKG_MGR"

# Python 3.11+
PYTHON_OK=$(python3 -c "import sys; print(1 if sys.version_info >= (3, 11) else 0)" 2>/dev/null || echo 0)
if [ "$PYTHON_OK" = "0" ]; then
    info "安装 Python 3.11..."
    if [ "$PKG_MGR" = "apt" ]; then
        $INSTALL_CMD python3.11 python3.11-venv python3.11-dev python3-pip 2>/dev/null || true
    else
        $INSTALL_CMD python3 python3-pip python3-devel 2>/dev/null || true
    fi
fi
PYTHON_VER=$(python3 --version 2>&1)
ok "Python: $PYTHON_VER"

# pip
python3 -m pip --version &>/dev/null || $INSTALL_CMD python3-pip 2>/dev/null || true

# ffmpeg（视频炼化 + 语音处理）
if ! command -v ffmpeg &> /dev/null; then
    info "安装 ffmpeg..."
    $INSTALL_CMD ffmpeg 2>/dev/null || warn "ffmpeg 安装失败，视频炼化功能将不可用"
else
    ok "ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
fi

# Nginx
if ! command -v nginx &> /dev/null; then
    info "安装 Nginx..."
    $INSTALL_CMD nginx 2>/dev/null || warn "Nginx 安装失败，请手动配置反向代理"
else
    ok "Nginx: $(nginx -v 2>&1)"
fi

# certbot (SSL)
if ! command -v certbot &> /dev/null; then
    info "安装 certbot (SSL 证书)..."
    if [ "$PKG_MGR" = "apt" ]; then
        $INSTALL_CMD certbot python3-certbot-nginx 2>/dev/null || true
    else
        $INSTALL_CMD certbot python3-certbot-nginx 2>/dev/null || pip3 install certbot certbot-nginx 2>/dev/null || true
    fi
fi

# ============================================================
# 2. Python 虚拟环境 + 依赖
# ============================================================
step "Step 2: Python 环境"

if [ ! -d "venv" ]; then
    info "创建虚拟环境..."
    python3 -m venv venv
    ok "虚拟环境已创建"
else
    ok "虚拟环境已存在"
fi

source venv/bin/activate

info "安装 Python 依赖..."
pip install --upgrade pip -q 2>/dev/null
pip install -r requirements.txt -q 2>/dev/null
ok "Python 依赖安装完成"

# ============================================================
# 3. 数据目录
# ============================================================
step "Step 3: 数据目录"

mkdir -p data/uploads data/voices data/avatars data/backups data/refinement_uploads
chmod 750 data
ok "数据目录已创建"

# ============================================================
# 4. 前端构建（如果有 Node.js）
# ============================================================
step "Step 4: 前端"

if [ -d "family-chat-app" ] && command -v npm &> /dev/null; then
    info "构建前端..."
    cd family-chat-app
    npm install -q 2>/dev/null
    npm run build:h5 -q 2>/dev/null && ok "前端构建完成" || warn "前端构建失败，将使用 frontend/index.html"
    cd "$PROJECT_DIR"
else
    info "跳过前端构建（使用现有 frontend/index.html）"
fi

# ============================================================
# 5. systemd 服务
# ============================================================
step "Step 5: systemd 服务"

if [ -d /etc/systemd/system ]; then
    # 更新 service 文件中的路径
    sed "s|/opt/family-chat|${PROJECT_DIR}|g" deploy/familychat.service > /tmp/familychat.service
    # 更新用户
    CURRENT_USER=$(logname 2>/dev/null || echo "root")
    sed -i "s|User=www-data|User=${CURRENT_USER}|g" /tmp/familychat.service
    sed -i "s|Group=www-data|Group=${CURRENT_USER}|g" /tmp/familychat.service

    cp /tmp/familychat.service /etc/systemd/system/familychat.service
    systemctl daemon-reload
    ok "systemd 服务已注册"
else
    warn "systemd 不可用，请手动管理进程"
fi

# ============================================================
# 6. Nginx 配置
# ============================================================
step "Step 6: Nginx 反向代理"

if command -v nginx &> /dev/null; then
    # 生成 Nginx 配置
    if [ "$DOMAIN" != "localhost" ] && ! curl -s ifconfig.me | grep -q "$DOMAIN" 2>/dev/null; then
        # 有域名，生成 HTTPS 配置
        NGINX_CONF="/etc/nginx/sites-available/familychat"
        mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

        sed "s/chat\.yourdomain\.com/${DOMAIN}/g" deploy/nginx-familychat.conf > "$NGINX_CONF"

        ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/familychat

        # 移除默认站点
        rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

        nginx -t 2>/dev/null && systemctl reload nginx && ok "Nginx 配置已加载" || warn "Nginx 配置检查失败，请手动修复"

        echo ""
        info "SSL 证书配置（域名解析生效后执行）:"
        echo "  sudo certbot --nginx -d ${DOMAIN}"
        echo ""
    else
        # 无域名，HTTP 代理
        cat > /etc/nginx/conf.d/familychat.conf << NGINX_EOF
upstream familychat {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 50m;

    location /api/ {
        proxy_pass http://familychat;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }

    location /ws {
        proxy_pass http://familychat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400s;
    }

    location / {
        proxy_pass http://familychat;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        proxy_pass http://familychat;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
NGINX_EOF
        nginx -t 2>/dev/null && systemctl reload nginx && ok "Nginx HTTP 代理已配置" || warn "Nginx 配置检查失败"
    fi
else
    warn "Nginx 未安装，服务将直接监听 8000 端口"
fi

# ============================================================
# 7. 阿里云安全组提示
# ============================================================
step "Step 7: 阿里云安全组"

echo ""
echo "  ⚠️  请确保阿里云安全组已放行以下端口:"
echo ""
echo "    协议    端口    说明"
echo "    ─────────────────────────────"
echo "    TCP     80      HTTP (Nginx)"
echo "    TCP     443     HTTPS (Nginx + SSL)"
echo "    TCP     8000    直接访问 (调试用，生产可关闭)"
echo ""
echo "  配置路径: 阿里云控制台 → ECS → 安全组 → 配置规则 → 入方向"
echo ""

# ============================================================
# 8. 启动服务
# ============================================================
step "Step 8: 启动 FamilyChat"

# 先停掉旧服务
systemctl stop familychat 2>/dev/null || true

# 启动
systemctl start familychat
sleep 3

if systemctl is-active --quiet familychat; then
    ok "FamilyChat 已启动！"
else
    err "启动失败，查看日志:"
    journalctl -u familychat --no-pager -n 20
    exit 1
fi

# 开机自启
systemctl enable familychat 2>/dev/null && ok "已设置开机自启"

# ============================================================
# 9. 健康检查
# ============================================================
step "Step 9: 健康检查"

sleep 2
HEALTH=$(curl -s http://localhost:8000/api/status 2>/dev/null || echo "{}")
if echo "$HEALTH" | grep -q '"status"'; then
    ok "API 正常: $HEALTH"
else
    err "API 不可达，检查日志: journalctl -u familychat -f"
fi

# ============================================================
# 完成
# ============================================================
echo ""
echo "============================================================"
echo -e "${GREEN}🎉 FamilyChat 部署完成！${NC}"
echo "============================================================"
echo ""
echo "  📍 访问地址:"
if [ "$DOMAIN" != "localhost" ]; then
    echo "     https://${DOMAIN}"
else
    echo "     http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_IP'):8000"
fi
echo ""
echo "  🔧 管理命令:"
echo "     systemctl status familychat    # 查看状态"
echo "     systemctl restart familychat   # 重启"
echo "     journalctl -u familychat -f    # 实时日志"
echo ""
echo "  📝 配置文件:"
echo "     ${PROJECT_DIR}/.env"
echo ""
echo "  🤖 AI 数字人:"
if grep -q "^LLM_API_KEY=.\+" .env 2>/dev/null; then
    echo "     ✅ LLM 已配置"
else
    echo "     ⚠️  LLM 未配置，请编辑 .env 填入 LLM_API_KEY"
fi
echo ""
echo "  📱 微信登录:"
if grep -q "^WX_APPID=.\+" .env 2>/dev/null; then
    echo "     ✅ 微信已配置"
else
    echo "     ⚠️  微信未配置（可选功能）"
fi
echo ""
echo "  🔒 SSL 证书:"
if [ "$DOMAIN" != "localhost" ]; then
    echo "     sudo certbot --nginx -d ${DOMAIN}"
else
    echo "     跳过（无域名）"
fi
echo ""
echo "============================================================"
