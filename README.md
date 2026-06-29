# 🏠 FamilyChat v2.0 - 家庭数字人聊天App

一个类似微信的聊天应用，内置 AI 数字人系统。每个家庭成员可以拥有一个数字分身，在群聊中与真人自由互动。

## 📱 支持平台

| 平台 | 状态 | 说明 |
|------|------|------|
| 🌐 Web | ✅ 可用 | 浏览器访问 |
| 📱 Android APP | ✅ 可用 | uni-app 编译 |
| 🍎 iOS APP | ✅ 可用 | uni-app 编译 |
| 💬 微信小程序 | ✅ 可用 | uni-app 编译 |

## ✨ v2.0 新特性

### 🎨 界面升级
- 🌙 **暗黑模式** - 全局深色主题，保护眼睛
- 📱 **流畅动画** - 消息气泡动画、页面切换过渡
- 🎯 **完整微信风格** - 对标微信的 UI 细节

### 💬 聊天增强
- ↩️ **消息回复** - 长按引用回复
- 🗑️ **消息撤回** - 2 分钟内可撤回
- ↪️ **消息转发** - 转发到其他群聊
- 📌 **消息置顶** - 重要消息置顶
- 😊 **表情回复** - 对消息添加 emoji 反应
- 📎 **文件发送** - 支持文档、视频、压缩包
- 🧧 **红包系统** - 发红包、拆红包
- 👋 **拍一拍** - 拍一拍群友

### 👥 社交功能
- 📷 **朋友圈** - 发布动态、点赞、评论
- 🤝 **好友系统** - 好友申请、搜索、备注
- 🔍 **全局搜索** - 搜索消息、联系人、群组
- ⭐ **消息收藏** - 收藏重要消息
- 🔔 **通知中心** - 未读消息提醒

### 🤖 Agent 升级
- 🧠 **增强记忆** - 核心/长期/情景记忆分层
- 🎭 **情绪联动** - 根据对话动态调整情绪
- 🧪 **炼化系统** - 通过聊天记录提取性格
- 🎤 **语音回复** - 30% 概率用语音回复

### ⚙️ 系统功能
- 👤 **个人资料** - 头像上传、签名、性别
- 🤖 **LLM 配置** - 运行时切换 AI 模型
- 📦 **Docker 部署** - 一键容器化部署
- 🔒 **JWT 认证** - 安全的用户认证

## 🚀 快速开始

### 方式一：直接运行（Web 版）

```bash
git clone https://github.com/grantftd365-cpu/family-chat.git
cd family-chat
bash deploy/setup.sh      # 一键部署
python run.py              # 启动服务
# 访问 http://localhost:8000
```

### 方式二：Docker

```bash
docker-compose up -d
```

### 方式三：编译 APP / 小程序

```bash
cd family-chat-app
npm install
npm run dev:h5             # H5 开发预览
npm run dev:mp-weixin      # 微信小程序开发
npm run build:h5           # 构建 H5
npm run build:mp-weixin    # 构建微信小程序
npm run build:app          # 构建 APP
```

## ⚙️ 配置

编辑 `.env`（从 `.env.example` 复制）：

```bash
LLM_PROVIDER=deepseek      # openai / deepseek / zhipu / qwen / local
LLM_API_KEY=***
LLM_MODEL=deepseek-chat
SECRET_KEY=***
WX_APPID=***               # 微信小程序（可选）
WX_SECRET=***              # 微信小程序（可选）
```

详见 [deploy/README.md](deploy/README.md)

## 📱 功能模块

| 模块 | 说明 |
|------|------|
| 💬 聊天 | 群聊/私聊、图片、语音、文件、红包 |
| 👥 通讯录 | 好友管理、群成员、搜索用户 |
| 📷 朋友圈 | 发布动态、点赞、评论 |
| ⭐ 收藏 | 收藏消息、文件 |
| 🔍 搜索 | 全局搜索消息/联系人/群组 |
| ⚙️ 设置 | 暗黑模式、LLM 配置、个人资料 |
| 🧪 炼化 | 通过文本/聊天记录训练数字人 |

## 🏗️ 项目结构

```
family-chat/
├── backend/                    # Python FastAPI 后端
│   └── app/
│       ├── main.py             # 主应用
│       ├── agents/             # 数字人系统
│       ├── core/               # 认证、WebSocket
│       ├── models/             # 数据库模型
│       └── routes/             # API 路由
├── frontend/
│   └── index.html              # Web 前端（单文件）
├── family-chat-app/            # uni-app 跨平台前端 ⭐
│   ├── src/
│   │   ├── pages/              # 页面
│   │   ├── components/         # 组件
│   │   ├── utils/              # 工具函数
│   │   ├── App.vue             # 根组件
│   │   ├── main.js             # 入口
│   │   ├── pages.json          # 路由配置
│   │   └── manifest.json       # 应用配置
│   └── package.json
├── miniprogram/                # 微信小程序原生版（旧）
├── deploy/                     # 部署配置 ⭐
│   ├── README.md               # 部署指南
│   ├── OPENCLAW_SETUP.md       # OpenClaw 配置手册
│   ├── setup.sh                # 一键部署脚本
│   ├── familychat.service      # systemd 服务
│   └── nginx-familychat.conf   # Nginx 配置
├── .env.example                # 环境变量模板
├── docker-compose.yaml         # Docker 配置
├── Dockerfile                  # Docker 镜像
├── requirements.txt            # Python 依赖
└── run.py                      # 启动入口
```

## 🤖 默认数字人

| 角色 | 性格 | 兴趣 |
|------|------|------|
| 👨 爸爸 | 退休教师，稳重幽默 | 钓鱼、历史、象棋 |
| 👩 妈妈 | 退休护士，热心爱唠叨 | 做饭、广场舞、养生 |
| 👵 奶奶 | 80岁慈祥，爱讲过去 | 戏曲、养花、回忆 |

## 🔧 API 文档

启动后访问 http://localhost:8000/docs

## 📦 部署

- [部署指南](deploy/README.md) - 完整部署文档
- [阿里云 + APP 测试](deploy/ALIYUN_APP_TEST.md) - ECS 部署、HTTPS、模拟器联调
- [OpenClaw 配置](deploy/OPENCLAW_SETUP.md) - AI 助手配置手册
- [一键部署](deploy/setup.sh) - `bash deploy/setup.sh`

## 📄 License

MIT License
