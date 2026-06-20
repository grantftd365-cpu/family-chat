# 🏠 FamilyChat - 家庭数字人聊天App

一个类似微信的聊天应用，内置 AI 数字人系统。每个家庭成员可以拥有一个数字分身，在群聊中与真人自由互动。

## ✨ 功能特性

### 聊天功能
- 📱 **类微信界面** - 移动端优先，完整聊天体验
- 🔐 **登录注册** - 用户账号系统 (JWT)
- 👥 **群聊** - 支持多人+数字人混合群聊
- 🎤 **语音消息** - 录音/播放，支持语音消息
- 😊 **表情系统** - 丰富的表情面板
- ⌨️ **打字提示** - 实时显示对方正在输入

### 数字人系统
- 🤖 **多Agent** - 每个数字人有独立性格、记忆、说话风格
- 🧠 **记忆系统** - 长短期记忆，不会遗忘重要事件
- 💬 **自动回复** - 智能判断是否回复，模拟真人行为
- 🎭 **情绪系统** - 根据对话内容动态调整情绪
- 🔊 **语音回复** - Agent 可以用语音回复（TTS）
- 👨‍👩‍👧‍👦 **默认角色** - 内置爸爸、妈妈、奶奶三个数字人

### 技术特性
- 🌐 **实时通信** - WebSocket 即时消息
- 📦 **容器化** - Docker 一键部署
- 🔌 **可扩展** - 支持多种 LLM 后端

## 🚀 快速开始

### 方式一：直接运行

```bash
# 1. 克隆项目
git clone https://github.com/grantftd365-cpu/family-chat.git
cd family-chat

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key

# 4. 启动
python run.py

# 5. 访问 http://localhost:8000
```

### 方式二：Docker

```bash
docker-compose up -d
```

## ⚙️ 配置说明

编辑 `.env` 文件：

```bash
# LLM 配置（必填）
LLM_PROVIDER=deepseek          # 支持: openai, deepseek, zhipu, qwen
LLM_API_KEY=***              # 你的 API Key
LLM_MODEL=deepseek-chat        # 模型名称

# 安全配置
SECRET_KEY=your-secret-key-here
```

### 支持的 LLM 提供商

| 提供商 | 推荐模型 | 说明 |
|--------|----------|------|
| DeepSeek | deepseek-chat | 性价比最高，推荐 |
| OpenAI | gpt-4o | 效果最好，价格较高 |
| 智谱 AI | glm-4 | 中文效果好 |
| 通义千问 | qwen-max | 阿里云，稳定 |

## 📱 功能截图

### 登录页面
![登录](docs/login.png)

### 聊天界面
![聊天](docs/chat.png)

### 数字人管理
![管理](docs/manage.png)

## 🏗️ 项目结构

```
family-chat/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI 主应用
│       ├── agents/
│       │   └── core.py      # 数字人核心系统
│       ├── core/
│       │   ├── auth.py      # 认证系统
│       │   └── websocket.py # WebSocket 管理
│       └── models/
│           └── database.py  # 数据库模型
├── frontend/
│   └── index.html           # 前端界面
├── run.py                   # 启动入口
├── requirements.txt         # Python 依赖
├── Dockerfile               # Docker 配置
├── docker-compose.yaml      # Docker Compose
└── README.md                # 项目文档
```

## 🔧 API 文档

启动后访问 http://localhost:8000/docs 查看完整的 API 文档。

### 主要 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/register` | POST | 用户注册 |
| `/api/login` | POST | 用户登录 |
| `/api/groups` | GET/POST | 群组列表/创建 |
| `/api/messages/{group_id}` | GET | 获取消息 |
| `/api/messages` | POST | 发送消息 |
| `/api/agents` | GET/POST | Agent 列表/创建 |
| `/api/tts` | POST | 文字转语音 |
| `/api/voice/upload` | POST | 上传语音 |
| `/ws` | WebSocket | 实时消息 |

## 🤖 数字人配置

### 默认数字人

系统会自动创建三个数字人：

1. **爸爸** 👨
   - 退休教师，稳重有耐心
   - 喜欢钓鱼、历史、下棋
   - 说话用成语，偶尔幽默

2. **妈妈** 👩
   - 退休护士，热心肠
   - 喜欢做饭、广场舞、养生
   - 说话亲切，爱唠叨

3. **奶奶** 👵
   - 80岁，慈祥
   - 喜欢听戏曲、养花
   - 说话慢悠悠，爱讲过去的事

### 创建新数字人

通过 API 或界面创建：

```json
POST /api/agents
{
  "name": "爷爷",
  "avatar": "👴",
  "backstory": "退休军人，严肃但内心柔软",
  "speaking_style": "说话简洁有力，偶尔用军事术语",
  "traits": ["严肃", "正直", "关心家人"],
  "interests": ["太极拳", "看新闻", "下棋"],
  "catchphrases": ["立正！", "报告！", "收到！"]
}
```

## 🎤 语音功能

### TTS 配置

系统使用 Edge TTS（免费）进行语音合成。支持多种中文语音：

- 晓晓 (zh-CN-XiaoxiaoNeural) - 温柔女声
- 云希 (zh-CN-YunxiNeural) - 稳重男声
- 晓艺 (zh-CN-XiaoyiNeural) - 年长女声
- 云健 (zh-CN-YunjianNeural) - 活力男声

### 语音消息

- 用户可以录制语音消息发送
- Agent 有 30% 概率用语音回复
- 语音消息显示为气泡样式

## 🧠 记忆系统

### 短期记忆

- 保存最近 30 条对话
- 用于理解上下文
- 自动清理旧数据

### 长期记忆

- 重要事件自动记录
- 支持关键词搜索
- 持久化存储

### 记忆触发

Agent 会自动记忆：
- 生日、纪念日
- 重要事件（生病、考试等）
- 情感表达
- 承诺和约定

## 🚀 部署

### 本地部署

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env

# 启动
python run.py
```

### Docker 部署

```bash
# 构建镜像
docker build -t familychat .

# 运行
docker run -d -p 8000:8000 -v ./data:/app/data familychat
```

### Docker Compose

```bash
docker-compose up -d
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [Edge TTS](https://github.com/rany2/edge-tts) - 语音合成
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
