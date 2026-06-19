# 🏠 FamilyChat - 家庭数字人聊天App

一个类似微信的聊天应用，内置 AI 数字人系统。每个家庭成员可以拥有一个数字分身，在群聊中与真人自由互动。

## ✨ 功能

- 📱 **类微信界面** - 移动端优先，完整聊天体验
- 🔐 **登录注册** - 用户账号系统
- 👥 **群聊** - 支持多人+数字人混合群聊
- 🤖 **数字人** - 独立性格、记忆、说话风格的 AI Agent
- 🎤 **语音消息** - TTS 语音合成，支持语音克隆
- 🧠 **记忆系统** - 长短期记忆，不会遗忘重要事件
- 🌐 **实时通信** - WebSocket 即时消息

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env 填入 LLM API Key

# 启动
python run.py

# 访问 http://localhost:8000
```

## 📱 界面预览

界面设计参考微信，包含：
- 登录/注册页
- 聊天列表
- 聊天界面（文字+语音）
- 通讯录
- 个人中心

## 🏗️ 技术栈

- **后端**: FastAPI + WebSocket + SQLite
- **前端**: 原生 HTML/CSS/JS (移动端优先)
- **LLM**: OpenAI / DeepSeek / 智谱 / 本地模型
- **TTS**: Edge TTS / GPT-SoVITS / CosyVoice
- **记忆**: ChromaDB + SQLite
