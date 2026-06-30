# 🚀 FamilyChat 部署指南

## 目录

- [阿里云 + APP 模拟器测试](ALIYUN_APP_TEST.md)
- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [Docker 部署](#docker-部署)
- [手动部署](#手动部署)
- [OpenClaw 配置](#openclaw-配置)
- [微信小程序配置](#微信小程序配置)
- [APP 打包](#app-打包)
- [常见问题](#常见问题)

---

## 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| OS | Ubuntu 22.04+ / Debian 12+ | 推荐 Ubuntu 24.04 |
| Python | 3.10+ | 后端运行环境 |
| Node.js | 18+ | OpenClaw + 前端构建 |
| OpenClaw | 2026.5.27+ | AI 助手网关 |
| Docker | 24+ | 可选，容器化部署 |

---

## 快速部署

### 1. 克隆项目

```bash
git clone https://github.com/grantftd365-cpu/family-chat.git
cd family-chat
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的配置
vim .env
```

### 3. 启动后端

```bash
# 方式一：直接运行
pip install -r requirements.txt
python run.py

# 方式二：Docker
docker-compose up -d
```

### 4. 访问

- Web 版：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

---

## Docker 部署

### docker-compose.yaml

```yaml
version: "3.8"

services:
  familychat:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env:ro
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/avatars data/voices data/images

EXPOSE 8000

CMD ["python", "run.py"]
```

### 构建和启动

```bash
docker-compose build
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

---

## 手动部署

### 1. 安装 Python 依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 .env

```bash
# 必填
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxxxxxxxxxxx
LLM_MODEL=deepseek-v4-flash
SECRET_KEY=your-random-secret-key-here

# 可选：微信小程序登录
WX_APPID=wx1234567890abcdef
WX_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：服务配置
HOST=0.0.0.0
PORT=8000
```

LLM Key 注意事项：`LLM_API_KEY` 必须是完整真实 Key，不能使用 APP 设置页或日志里显示的 `sk-xxxx***` 脱敏值。修改 `/opt/family-chat/.env` 后执行 `sudo systemctl restart familychat` 生效；如果“炼化数字人”提示 401，优先检查 DeepSeek/LLM Key 是否无效、过期或余额不足。

### 3. 启动

```bash
# 前台运行
python run.py

# 后台运行（推荐用 systemd）
nohup python run.py > familychat.log 2>&1 &
```

### 4. systemd 服务（推荐）

创建 `/etc/systemd/system/familychat.service`：

```ini
[Unit]
Description=FamilyChat Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/family-chat
EnvironmentFile=/opt/family-chat/.env
ExecStart=/opt/family-chat/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable familychat
sudo systemctl start familychat
sudo systemctl status familychat
```

---

## OpenClaw 配置

详见 [OPENCLAW_SETUP.md](./OPENCLAW_SETUP.md)

### 快速配置

```bash
# 安装 OpenClaw（如果未安装）
npm install -g openclaw

# 交互式配置
openclaw onboard

# 或直接编辑配置
vim ~/.openclaw/openclaw.json
```

### 最小配置示例

```json5
// ~/.openclaw/openclaw.json
{
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace",
      model: { primary: "xiaomi/mimo-v2.5-pro" },
    },
    list: [
      {
        id: "main",
        identity: {
          name: "FamilyChat 助手",
          theme: "家庭数字人聊天助手",
          emoji: "🏠",
        },
      },
    ],
  },
  channels: {
    // 按需配置消息渠道
  },
}
```

---

## 微信小程序配置

### 1. 注册小程序

访问 [微信公众平台](https://mp.weixin.qq.com/) 注册小程序账号。

### 2. 获取 AppID 和 Secret

在公众平台 → 开发 → 开发管理 → 开发设置 中获取。

### 3. 配置服务器域名

在公众平台 → 开发 → 开发管理 → 服务器域名 中配置：

| 类型 | 域名 |
|------|------|
| request 合法域名 | `https://your-domain.com` |
| wss 合法域名 | `wss://your-domain.com` |
| uploadFile 合法域名 | `https://your-domain.com` |
| downloadFile 合法域名 | `https://your-domain.com` |

### 4. 配置后端

在 `.env` 中添加：

```bash
WX_APPID=wx1234567890abcdef
WX_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 5. 编译小程序

```bash
cd family-chat-app
npm install
# 使用 HBuilderX 或 CLI 编译到微信小程序
npx uni build -p mp-weixin
```

编译产物在 `dist/build/mp-weixin/` 目录，用微信开发者工具导入即可。

---

## APP 打包

### 方式一：HBuilderX 云打包（推荐）

1. 用 HBuilderX 打开 `family-chat-app` 项目
2. 菜单 → 发行 → 原生APP-云打包
3. 选择平台（Android/iOS）
4. 配置证书和包名
5. 等待云端打包完成

### 方式二：本地打包

```bash
cd family-chat-app
npm install
npx uni build -p app
```

生成的工程文件在 `dist/build/app/` 中，用 Android Studio 或 Xcode 打开编译。

### Android 签名

```bash
# 生成签名文件
keytool -genkey -v -keystore familychat.keystore \
  -alias familychat -keyalg RSA -keysize 2048 -validity 10000

# 在 manifest.json 中配置签名信息
```

---

## 常见问题

### Q: 端口被占用怎么办？

```bash
# 查看占用端口的进程
lsof -i :8000
# 或
ss -tlnp | grep 8000

# 修改 .env 中的 PORT
PORT=8001
```

### Q: 如何配置 HTTPS？

推荐使用 Nginx 反向代理 + Let's Encrypt：

```nginx
server {
    listen 443 ssl;
    server_name chat.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/chat.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}

server {
    listen 80;
    server_name chat.yourdomain.com;
    return 301 https://$host$request_uri;
}
```

### Q: 如何备份数据？

```bash
# 数据库文件
cp data/familychat.db data/familychat.db.backup.$(date +%Y%m%d)

# 完整备份
tar czf familychat-backup-$(date +%Y%m%d).tar.gz data/ .env
```

### Q: 如何更新版本？

```bash
git pull
pip install -r requirements.txt
# 重启服务
sudo systemctl restart familychat
# 或 Docker
docker-compose down && docker-compose up -d --build
```
