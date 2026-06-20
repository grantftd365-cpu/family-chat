# 🚀 FamilyChat 部署与迁移指南

## 一、快速部署（任何服务器）

### 1.1 环境要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| CPU | 1核 | 2核+ |
| 内存 | 1GB | 2GB+ |
| 磁盘 | 10GB | 50GB+ (SSD) |
| OS | Ubuntu 20.04+ / CentOS 7+ | Ubuntu 22.04 LTS |
| Python | 3.10+ | 3.12 |
| 网络 | 公网IP + 开放8000端口 | 域名 + HTTPS |

### 1.2 一键部署脚本

```bash
# 1. 安装基础环境
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git nginx

# 2. 克隆项目
git clone https://github.com/grantftd365-cpu/family-chat.git
cd family-chat

# 3. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 文件（见下方配置说明）

# 6. 启动服务
python run.py
```

---

## 二、环境变量配置 (.env)

```bash
# ==================== LLM 大模型配置 ====================
# 支持的提供商: openai, deepseek, zhipu, qwen, minimax, baichuan, moonshot, stepfun, yi, spark, doubao
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL=deepseek-chat
LLM_BASE_URL=                           # 留空则使用默认URL，自定义部署时填写
LLM_TEMPERATURE=0.8

# ==================== 安全配置 ====================
SECRET_KEY=your-random-secret-key-here   # 生产环境务必修改！用 openssl rand -hex 32 生成

# ==================== 服务配置 ====================
HOST=0.0.0.0
PORT=8000
DEBUG=false

# ==================== 数据库 ====================
DB_PATH=data/familychat.db               # SQLite数据库路径

# ==================== 文件存储 ====================
UPLOAD_DIR=data/uploads                  # 上传文件目录
VOICE_DIR=data/voices                    # 语音文件目录
MAX_UPLOAD_SIZE=10485760                 # 最大上传大小(字节) 10MB

# ==================== TTS 语音合成 ====================
TTS_PROVIDER=edge                        # edge (免费) / azure / aliyun
TTS_DEFAULT_VOICE=zh-CN-XiaoxiaoNeural
```

---

## 三、阿里云 ECS 部署方案

### 3.1 购买 ECS 实例

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 创建实例：
   - **地域**: 华东1(杭州) 或 华东2(上海)
   - **规格**: ecs.t6-c1m2.large (2核4GB) 或更高
   - **镜像**: Ubuntu 22.04 LTS 64位
   - **存储**: 40GB ESSD云盘
   - **网络**: 专有网络VPC，分配公网IP
   - **安全组**: 开放 80(HTTP)、443(HTTPS)、8000(API) 端口

### 3.2 安全组规则

| 协议 | 端口 | 源 | 说明 |
|------|------|-----|------|
| TCP | 22 | 你的IP/32 | SSH |
| TCP | 80 | 0.0.0.0/0 | HTTP |
| TCP | 443 | 0.0.0.0/0 | HTTPS |
| TCP | 8000 | 0.0.0.0/0 | FamilyChat API |

### 3.3 服务器初始化

```bash
# SSH 连接服务器
ssh root@你的公网IP

# 更新系统
apt update && apt upgrade -y

# 安装必要工具
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx ufw

# 配置防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw enable
```

### 3.4 部署 FamilyChat

```bash
# 创建应用用户（安全起见不用root）
adduser familychat
usermod -aG sudo familychat
su - familychat

# 克隆项目
git clone https://github.com/grantftd365-cpu/family-chat.git
cd family-chat

# Python 环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置
cp .env.example .env
nano .env
# 填入你的配置（LLM API Key等）

# 测试启动
python run.py
# 访问 http://你的公网IP:8000 验证
```

### 3.5 配置 Systemd 服务（开机自启）

```bash
sudo nano /etc/systemd/system/familychat.service
```

```ini
[Unit]
Description=FamilyChat Server
After=network.target

[Service]
Type=simple
User=familychat
WorkingDirectory=/home/familychat/family-chat
Environment=PATH=/home/familychat/family-chat/venv/bin
ExecStart=/home/familychat/family-chat/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable familychat
sudo systemctl start familychat
sudo systemctl status familychat
```

### 3.6 Nginx 反向代理 + HTTPS

```bash
sudo nano /etc/nginx/sites-available/familychat
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/familychat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 申请免费SSL证书（需要域名已解析到此IP）
sudo certbot --nginx -d your-domain.com
```

---

## 四、LLM 大模型配置方案

### 4.1 支持的提供商一览

| 提供商 | 环境变量配置 | 推荐模型 | 价格 | 说明 |
|--------|-------------|----------|------|------|
| **DeepSeek** | `LLM_PROVIDER=deepseek` | deepseek-chat | ¥1/100万tokens | 性价比最高，推荐 |
| **通义千问** | `LLM_PROVIDER=qwen` | qwen-max | ¥2/100万tokens | 阿里云原生，稳定 |
| **智谱AI** | `LLM_PROVIDER=zhipu` | glm-4 | ¥5/100万tokens | 中文效果好 |
| **OpenAI** | `LLM_PROVIDER=openai` | gpt-4o | $5/100万tokens | 效果最好 |
| **Moonshot** | `LLM_PROVIDER=moonshot` | moonshot-v1-8k | ¥8/100万tokens | 长文本 |
| **百川** | `LLM_PROVIDER=baichuan` | Baichuan4 | ¥5/100万tokens | 中文强 |
| **MiniMax** | `LLM_PROVIDER=minimax` | abab6.5-chat | ¥5/100万tokens | 多模态 |
| **阶跃星辰** | `LLM_PROVIDER=stepfun` | step-2-16k | ¥5/100万tokens | 推理强 |
| **零一万物** | `LLM_PROVIDER=yi` | yi-large | ¥5/100万tokens | 中英双语 |
| **讯飞星火** | `LLM_PROVIDER=spark` | spark-max | ¥5/100万tokens | 语音强 |
| **豆包** | `LLM_PROVIDER=doubao` | doubao-pro-32k | ¥2/100万tokens | 字节跳动 |
| **本地Ollama** | `LLM_PROVIDER=openai` | 任意模型 | 免费 | 需GPU |

### 4.2 本地模型部署 (Ollama)

```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama pull qwen2:7b
ollama pull llama3:8b

# .env 配置
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2:7b
LLM_API_KEY=ollama
```

### 4.3 运行时切换模型

通过 API 动态切换，无需重启：

```bash
# 切换到通义千问
curl -X POST http://localhost:8000/api/config/llm \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"provider":"qwen","api_key":"sk-xxx","model":"qwen-max"}'
```

---

## 五、从一台服务器迁移到另一台

### 5.1 迁移步骤（3分钟完成）

```bash
# ===== 在旧服务器上 =====

# 1. 备份数据
cd /home/familychat/family-chat
tar -czf familychat-backup-$(date +%Y%m%d).tar.gz \
  data/ .env backend/app/agents/ frontend/

# 2. 下载备份
# 用 scp 或其他方式下载到本地
scp root@旧服务器IP:~/familychat-backup-*.tar.gz ./

# ===== 在新服务器上 =====

# 3. 部署新服务器（按上面第三节操作）

# 4. 上传并恢复备份
scp familychat-backup-*.tar.gz root@新服务器IP:~/
ssh root@新服务器IP

# 5. 恢复数据
cd /home/familychat/family-chat
tar -xzf ~/familychat-backup-*.tar.gz

# 6. 重启服务
sudo systemctl restart familychat
```

### 5.2 迁移检查清单

- [ ] `.env` 文件中的 API Key 已更新
- [ ] `data/` 目录完整（包含数据库和上传文件）
- [ ] 新服务器安全组已开放端口
- [ ] DNS 已更新指向新IP（如有域名）
- [ ] SSL 证书已重新申请
- [ ] 服务正常启动并可访问

### 5.3 Docker 一键迁移

```bash
# 旧服务器: 导出镜像+数据
docker save familychat > familychat.tar
docker run --rm -v familychat-data:/data -v $(pwd):/backup alpine tar czf /backup/familychat-data.tar.gz /data

# 新服务器: 导入
docker load < familychat.tar
docker run --rm -v familychat-data:/data -v $(pwd):/backup alpine tar xzf /backup/familychat-data.tar.gz -C /
docker-compose up -d
```

---

## 六、OpenClaw 集成部署

### 6.1 在阿里云上安装 OpenClaw

```bash
# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 OpenClaw
npm install -g openclaw

# 初始化
openclaw init
openclaw gateway start
```

### 6.2 OpenClaw 配置 FamilyChat

在 OpenClaw 配置中添加 FamilyChat 作为自定义工具：

```yaml
# ~/.openclaw/config.yaml
tools:
  custom:
    familychat:
      type: http
      base_url: http://localhost:8000
      description: "家庭数字人聊天系统"
      endpoints:
        - path: /api/conversations
          method: GET
          description: 获取会话列表
        - path: /api/messages/{group_id}
          method: GET
          description: 获取群消息
        - path: /api/messages
          method: POST
          description: 发送消息
        - path: /api/agents
          method: GET
          description: 获取数字人列表
```

### 6.3 完整的 .env 模板（阿里云 + OpenClaw）

```bash
# ===== LLM 配置（推荐使用通义千问，阿里云原生） =====
LLM_PROVIDER=qwen
LLM_API_KEY=sk-你的通义千问API_KEY
LLM_MODEL=qwen-max
LLM_TEMPERATURE=0.8

# ===== 安全 =====
SECRET_KEY=$(openssl rand -hex 32)

# ===== 服务 =====
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

---

## 七、监控与维护

### 7.1 日志查看

```bash
# 查看服务状态
sudo systemctl status familychat

# 查看实时日志
sudo journalctl -u familychat -f

# 查看最近100行日志
sudo journalctl -u familychat -n 100
```

### 7.2 数据备份（自动定时）

```bash
# 添加定时备份脚本
nano /home/familychat/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/familychat/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cd /home/familychat/family-chat
tar -czf $BACKUP_DIR/familychat_$DATE.tar.gz data/ .env
# 只保留最近7天的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

```bash
chmod +x /home/familychat/backup.sh
# 每天凌晨3点自动备份
crontab -e
0 3 * * * /home/familychat/backup.sh
```

### 7.3 性能监控

```bash
# 查看API状态
curl http://localhost:8000/api/status

# 返回示例:
# {"status":"running","agents":3,"online":2,"version":"2.0.0"}
```

---

## 八、故障排查

| 问题 | 解决方案 |
|------|----------|
| 服务无法启动 | 检查 `.env` 配置，查看 `journalctl -u familychat` 日志 |
| LLM 不回复 | 检查 API Key 是否正确，网络是否通畅 |
| WebSocket 断连 | 检查 Nginx 配置中的 `proxy_read_timeout` |
| 上传文件失败 | 检查 `data/` 目录权限，`chmod -R 755 data/` |
| 数据库锁定 | SQLite 并发限制，检查是否有僵尸进程 |

---

## 九、项目结构

```
family-chat/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI 主应用 (49个API端点)
│       ├── agents/
│       │   └── core.py          # 数字人核心 (社交智能引擎)
│       ├── core/
│       │   ├── auth.py          # JWT认证
│       │   └── websocket.py     # WebSocket管理
│       └── models/
│           └── database.py      # 数据库模型
├── frontend/
│   └── index.html               # 前端界面 (微信级UI)
├── data/                        # 运行时数据(不提交到git)
│   ├── familychat.db            # SQLite数据库
│   ├── uploads/                 # 上传的图片
│   └── voices/                  # 语音文件
├── .env.example                 # 环境变量模板
├── requirements.txt             # Python依赖
├── run.py                       # 启动入口
├── Dockerfile                   # Docker配置
├── docker-compose.yaml          # Docker Compose
├── DEPLOY.md                    # 本文档
└── README.md                    # 项目说明
```

---

## 十、许可证

MIT License - 自由使用、修改、部署。
