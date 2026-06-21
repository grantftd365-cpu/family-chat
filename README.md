# 🏠 FamilyChat v2.0 - 家庭数字人聊天App

一个类似微信的聊天应用，内置 AI 数字人系统。每个家庭成员可以拥有一个数字分身，在群聊中与真人自由互动。

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

### 方式一：直接运行

```bash
git clone https://github.com/grantftd365-cpu/family-chat.git
cd family-chat
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 LLM API Key
python run.py
# 访问 http://localhost:8000
```

### 方式二：Docker

```bash
docker-compose up -d
```

## ⚙️ 配置

编辑 `.env`：

```bash
LLM_PROVIDER=deepseek      # openai / deepseek / zhipu / qwen / local
LLM_API_KEY=your-key
LLM_MODEL=deepseek-chat
SECRET_KEY=your-secret-key
```

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
├── backend/
│   └── app/
│       ├── main.py              # FastAPI 主应用
│       ├── agents/
│       │   └── core.py          # 数字人核心系统
│       ├── core/
│       │   ├── auth.py          # JWT 认证
│       │   └── websocket.py     # WebSocket 管理
│       ├── models/
│       │   └── database.py      # 数据库模型（17张表）
│       └── routes/
│           ├── auth.py          # 认证路由
│           ├── chat.py          # 聊天路由
│           ├── friends.py       # 好友路由
│           ├── moments.py       # 朋友圈路由
│           ├── agents.py        # Agent 路由
│           ├── search.py        # 搜索路由
│           └── notifications.py # 通知路由
├── frontend/
│   └── index.html               # 前端界面（单文件）
├── run.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yaml
└── .env.example
```

## 🤖 默认数字人

| 角色 | 性格 | 兴趣 |
|------|------|------|
| 👨 爸爸 | 退休教师，稳重幽默 | 钓鱼、历史、象棋 |
| 👩 妈妈 | 退休护士，热心爱唠叨 | 做饭、广场舞、养生 |
| 👵 奶奶 | 80岁慈祥，爱讲过去 | 戏曲、养花、回忆 |

## 🔧 API 文档

启动后访问 http://localhost:8000/docs

## 📄 License

MIT License
