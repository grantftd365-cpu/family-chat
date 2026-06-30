# FamilyChat 阿里云部署完全指南

## 一、服务器要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 磁盘 | 40 GB SSD | 100 GB SSD |
| 系统 | Alinux 3 / Ubuntu 22.04 / CentOS 7+ | Alinux 3 |
| 带宽 | 3 Mbps | 5 Mbps+ |

**推荐机型：** 阿里云 ECS ecs.c7.xlarge（4C8G）或 ecs.g7.large（2C8G）

## 二、前置条件

### 2.1 阿里云控制台操作

1. **购买 ECS 实例**（按量付费或包年包月）
2. **配置安全组**，放行端口：

| 协议 | 端口 | 来源 | 说明 |
|------|------|------|------|
| TCP | 22 | 你的 IP | SSH |
| TCP | 80 | 0.0.0.0/0 | HTTP |
| TCP | 443 | 0.0.0.0/0 | HTTPS |
| TCP | 8000 | 0.0.0.0/0 | 直接访问（调试，生产可关） |

3. **域名解析**（可选）：将域名 A 记录指向 ECS 公网 IP

### 2.2 SSH 连接

```bash
ssh root@你的ECS公网IP
```

## 三、一键部署

### 方式一：自动脚本（推荐）

```bash
# 1. 安装 git
yum install -y git  # CentOS/Alinux
# apt install -y git  # Ubuntu

# 2. 克隆项目
cd /opt
git clone https://github.com/grantftd365-cpu/family-chat.git
cd family-chat

# 3. 一键部署（交互式配置向导）
sudo bash deploy/setup.sh
```

脚本会自动完成：
- ✅ 安装系统依赖（Python、Nginx、ffmpeg、certbot）
- ✅ 创建 Python 虚拟环境 + 安装依赖
- ✅ 交互式配置 .env（域名、LLM、微信）
- ✅ 创建数据目录
- ✅ 注册 systemd 服务
- ✅ 配置 Nginx 反向代理
- ✅ 启动服务 + 健康检查

### 方式二：手动部署

```bash
# 1. 系统依赖
yum install -y python3 python3-pip python3-devel nginx ffmpeg

# 2. 项目
cd /opt
git clone https://github.com/grantftd365-cpu/family-chat.git
cd family-chat

# 3. 配置
cp .env.example .env
# 编辑 .env 填入实际值
vim .env

# 4. Python 环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. 启动
python run.py
```

## 四、.env 配置说明

```bash
# === 必填 ===
SECRET_KEY=你的密钥              # python3 -c "import secrets; print(secrets.token_hex(32))"
CORS_ORIGINS=https://chat.xxx.com # 允许的前端域名，逗号分隔
LLM_API_KEY=sk-xxx               # AI 数字人的大脑，没有这个 Agent 不会说话

# === LLM 选择 ===
LLM_PROVIDER=deepseek            # openai / deepseek / zhipu / qwen / local
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash

# === 微信（可选）===
WX_APPID=                        # 微信开放平台 AppID
WX_SECRET=                       # 微信开放平台 AppSecret

# === 服务器 ===
HOST=0.0.0.0
PORT=8000
TZ=Asia/Shanghai
```

## 五、SSL 证书（HTTPS）

```bash
# 域名解析生效后执行
sudo certbot --nginx -d chat.yourdomain.com

# 自动续期测试
sudo certbot renew --dry-run
```

## 六、管理命令

```bash
# 服务管理
systemctl start familychat      # 启动
systemctl stop familychat       # 停止
systemctl restart familychat    # 重启
systemctl status familychat     # 状态

# 查看日志
journalctl -u familychat -f              # 实时日志
journalctl -u familychat --since today   # 今日日志
journalctl -u familychat -n 100          # 最近100行

# 更新代码
cd /opt/family-chat
git pull
systemctl restart familychat

# 备份
cp data/familychat.db data/backups/manual_$(date +%Y%m%d).db
```

## 七、监控

```bash
# 健康检查
curl http://localhost:8000/api/status

# 系统资源
htop
df -h
free -m

# Nginx 日志
tail -f /var/log/nginx/familychat-access.log
tail -f /var/log/nginx/familychat-error.log
```

## 八、故障排查

| 问题 | 排查命令 | 解决方案 |
|------|----------|----------|
| 服务启动失败 | `journalctl -u familychat -n 50` | 检查 .env 配置 |
| 502 Bad Gateway | `systemctl status familychat` | 确认服务在运行 |
| WebSocket 断连 | 检查 Nginx ws 配置 | 确认 proxy_read_timeout |
| AI 不回复 | 检查 LLM_API_KEY | 确认 API Key 有效 |
| 磁盘满了 | `df -h` | 清理 data/backups/ |
| 数据库锁 | `journalctl` 搜索 "database is locked" | 重启服务 |

## 九、安全加固清单

- [x] SECRET_KEY 使用随机强密钥
- [x] CORS 限制为实际域名
- [x] HTTPS 启用
- [x] 安全组仅放行必要端口
- [x] systemd 安全加固（NoNewPrivileges、ProtectSystem）
- [x] 文件上传大小限制
- [x] 路径遍历防护
- [x] 权限校验（群主/管理员）
- [ ] 定期备份 cron（建议配置）
- [ ] fail2ban 防暴力破解（建议配置）
- [ ] 日志轮转（建议配置 logrotate）

## 十、一键部署清单（OpenClaw 执行）

当你对 OpenClaw 说"部署 FamilyChat"时，它会执行：

1. SSH 连接阿里云 ECS
2. `git clone` 项目
3. `bash deploy/setup.sh`（交互式配置）
4. 配置 SSL 证书
5. 健康检查
6. 返回访问地址

**你需要提前准备：**
- [ ] 阿里云 ECS 实例 + 公网 IP
- [ ] 安全组已放行 80/443 端口
- [ ] 域名已解析到 ECS IP（可选）
- [ ] LLM API Key（DeepSeek/OpenAI/智谱/千问）
- [ ] 微信 AppID + Secret（可选）
