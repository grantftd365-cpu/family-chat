# 🤖 OpenClaw 配置手册

> 本手册记录如何在新服务器上配置 OpenClaw，使其与 FamilyChat 项目配合工作。

---

## 目录

- [概述](#概述)
- [服务器环境准备](#服务器环境准备)
- [安装 OpenClaw](#安装-openclaw)
- [核心配置](#核心配置)
- [模型配置](#模型配置)
- [消息渠道配置](#消息渠道配置)
- [安全配置](#安全配置)
- [工作区配置](#工作区配置)
- [启动与验证](#启动与验证)
- [配置文件完整示例](#配置文件完整示例)
- [运维命令](#运维命令)
- [故障排查](#故障排查)

---

## 概述

OpenClaw 是一个 AI 助手网关，负责：
- 管理 AI 模型调用
- 连接各种消息渠道（微信、Telegram、Discord 等）
- 管理对话会话和上下文
- 执行定时任务和自动化工作流

FamilyChat 项目中，OpenClaw 用于：
- 作为开发和运维助手
- 管理服务器上的项目
- 自动化部署和监控

---

## 服务器环境准备

### 系统要求

```bash
# 推荐配置
OS:     Ubuntu 24.04 LTS (或 Debian 12+)
CPU:    2 核+
RAM:    2GB+
Disk:   20GB+
Node.js: 22.x (LTS)
npm:    10.x
```

### 安装 Node.js

```bash
# 方式一：NodeSource（推荐）
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# 方式二：nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
source ~/.bashrc
nvm install 22
nvm use 22

# 验证
node --version  # 应显示 v22.x
npm --version   # 应显示 10.x
```

### 安装其他依赖

```bash
sudo apt update
sudo apt install -y git curl wget python3 python3-pip python3-venv
```

---

## 安装 OpenClaw

### 全局安装

```bash
npm install -g openclaw

# 验证安装
openclaw --version
# 输出: OpenClaw 2026.5.27 (xxxxxxx)
```

### 初始化

```bash
# 交互式初始化（推荐新手）
openclaw onboard

# 或手动创建配置目录
mkdir -p ~/.openclaw
```

---

## 核心配置

配置文件路径：`~/.openclaw/openclaw.json`

> OpenClaw 使用 JSON5 格式（支持注释和尾逗号），也兼容标准 JSON。

### 配置结构概览

```json5
{
  // 环境变量和密钥
  env: { ... },

  // 认证配置
  auth: { ... },

  // Agent 配置（核心）
  agents: {
    defaults: { ... },  // 默认配置
    list: [ ... ],      // Agent 列表
  },

  // 消息渠道
  channels: { ... },

  // 消息格式
  messages: { ... },

  // 日志
  logging: { ... },

  // 插件
  plugins: { ... },

  // 工具和沙箱
  tools: { ... },
}
```

---

## 模型配置

### 方式一：使用小米 MIMO 模型（当前服务器配置）

需要设置环境变量：

```bash
# 在 ~/.openclaw/openclaw.json 的 env 部分配置
# 或在系统环境中设置
export MIMO_API_BASE_URL="https://your-mimo-endpoint.com/v1"
export MIMO_API_KEY="your-api-key"
```

配置文件中：

```json5
{
  env: {
    MIMO_API_BASE_URL: "https://your-mimo-endpoint.com/v1",
    MIMO_API_KEY: "sk-xxxxxxxxxxxx",
  },
  agents: {
    defaults: {
      model: {
        primary: "xiaomi/mimo-v2.5-pro",
      },
    },
  },
}
```

### 方式二：使用 OpenAI 兼容 API

```json5
{
  env: {
    OPENAI_API_KEY: "sk-xxxxxxxxxxxx",
  },
  agents: {
    defaults: {
      model: {
        primary: "openai/gpt-4o",
      },
    },
  },
}
```

### 方式三：使用 DeepSeek

```json5
{
  env: {
    DEEPSEEK_API_KEY: "sk-xxxxxxxxxxxx",
  },
  agents: {
    defaults: {
      model: {
        primary: "deepseek/deepseek-chat",
      },
    },
  },
}
```

### 方式四：使用本地模型（Ollama）

```json5
{
  agents: {
    defaults: {
      model: {
        primary: "ollama/qwen2.5:7b",
      },
    },
  },
}
```

### 模型配置字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `model.primary` | 主模型 | `"xiaomi/mimo-v2.5-pro"` |
| `model.fallbacks` | 备选模型列表 | `["openai/gpt-4o-mini"]` |
| `model.thinking` | 思考模式 | `"medium"` / `"off"` / `"on"` |

---

## 消息渠道配置

### Telegram

```json5
{
  channels: {
    telegram: {
      token: "7012345678:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      allowFrom: ["your_username"],  // 允许的用户名
      groups: {
        "*": { requireMention: true },  // 群聊需要 @
      },
    },
  },
}
```

获取 Token：找 [@BotFather](https://t.me/BotFather) 创建机器人。

### Discord

```json5
{
  channels: {
    discord: {
      token: "MTxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxx",
      allowFrom: ["user:123456789"],  // 允许的用户 ID
    },
  },
}
```

获取 Token：[Discord Developer Portal](https://discord.com/developers/applications) → Bot → Token。

### 微信公众号 / 企业微信

```json5
{
  channels: {
    wechat: {
      appId: "wx1234567890abcdef",
      secret: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      token: "your-verify-token",
      encodingAESKey: "your-encoding-aes-key",
    },
  },
}
```

### QQ 机器人

```json5
{
  channels: {
    qqbot: {
      appId: "1234567890",
      token: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      allowFrom: ["user:987654321"],
    },
  },
}
```

### 飞书

```json5
{
  channels: {
    feishu: {
      appId: "cli_xxxxxxxxxxxxxxxx",
      appSecret: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      allowFrom: ["user:ou_xxxxxxxx"],
    },
  },
}
```

---

## 安全配置

### 认证

```json5
{
  auth: {
    // 认证配置文件路径（存放实际密钥）
    // 密钥不直接写在 openclaw.json 中
    profiles: {
      "xiaomi:default": {
        provider: "xiaomi",
        mode: "api_key",
      },
    },
  },
}
```

> **重要**：实际的 API Key 存放在 `~/.openclaw/auth-profiles.json` 中，
> 不要直接写在 `openclaw.json` 里。`openclaw.json` 中引用 profile 名称即可。

### 工具权限

```json5
{
  tools: {
    // exec 工具的安全策略
    exec: {
      security: "sandbox",  // "sandbox" | "elevated" | "unrestricted"
    },
    // 文件系统限制
    fs: {
      workspaceOnly: true,  // 只能访问工作区目录
    },
  },
}
```

### 沙箱

```json5
{
  tools: {
    sandbox: {
      enabled: true,
      // 允许的网络访问
      network: {
        allow: ["api.openai.com", "api.deepseek.com"],
      },
    },
  },
}
```

---

## 工作区配置

### 默认工作区

```json5
{
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace",
    },
  },
}
```

### Agent 列表

```json5
{
  agents: {
    list: [
      {
        id: "main",
        identity: {
          name: "FamilyChat 助手",
          theme: "家庭数字人聊天项目的AI助手",
          emoji: "🏠",
        },
        // 覆盖默认配置
        // model: { primary: "openai/gpt-4o" },
      },
    ],
  },
}
```

### 心跳配置

```json5
{
  agents: {
    defaults: {
      heartbeat: {
        every: "30m",  // 每30分钟检查一次
      },
    },
  },
}
```

---

## 启动与验证

### 启动 Gateway

```bash
# 前台启动（调试用）
openclaw gateway start

# 后台启动（生产用）
openclaw gateway start --background

# 查看状态
openclaw gateway status
```

### 验证配置

```bash
# 检查配置是否正确
openclaw doctor

# 自动修复配置问题
openclaw doctor --fix

# 查看当前配置
openclaw config get

# 查看日志
openclaw logs
```

### 测试连接

```bash
# 发送测试消息
openclaw chat "你好，测试消息"

# 查看会话列表
openclaw sessions list
```

---

## 配置文件完整示例

以下是 FamilyChat 项目推荐的完整配置：

```json5
// ~/.openclaw/openclaw.json
{
  // === 环境变量 ===
  env: {
    MIMO_API_BASE_URL: "https://your-mimo-endpoint.com/v1",
    MIMO_API_KEY: "sk-xxxxxxxxxxxx",
  },

  // === Agent 配置 ===
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace",
      model: {
        primary: "xiaomi/mimo-v2.5-pro",
        thinking: "medium",
      },
      heartbeat: {
        every: "30m",
      },
    },
    list: [
      {
        id: "main",
        identity: {
          name: "FamilyChat 助手",
          theme: "家庭数字人聊天项目的AI开发和运维助手",
          emoji: "🏠",
        },
      },
    ],
  },

  // === 消息渠道 ===
  channels: {
    // 按需取消注释
    // telegram: {
    //   token: "7012345678:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    //   allowFrom: ["your_username"],
    // },
    // discord: {
    //   token: "MTxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxx",
    //   allowFrom: ["user:123456789"],
    // },
  },

  // === 消息配置 ===
  messages: {
    visibleReplies: "automatic",
    groupChat: {
      visibleReplies: "message_tool",
      unmentionedInbound: "room_event",
    },
  },

  // === 日志 ===
  logging: {
    level: "info",
    consoleLevel: "info",
    consoleStyle: "pretty",
    redactSensitive: "tools",
  },

  // === 工具 ===
  tools: {
    exec: {
      security: "sandbox",
    },
    fs: {
      workspaceOnly: true,
    },
  },
}
```

---

## 运维命令速查

```bash
# === 状态检查 ===
openclaw status                  # 总览
openclaw gateway status          # Gateway 状态
openclaw doctor                  # 配置诊断
openclaw health                  # 健康检查

# === 启停控制 ===
openclaw gateway start           # 前台启动
openclaw gateway start --background  # 后台启动
openclaw gateway restart         # 重启
openclaw gateway stop            # 停止

# === 配置管理 ===
openclaw config get              # 查看全部配置
openclaw config get agents.defaults.model  # 查看某个字段
openclaw config set agents.defaults.model.primary "openai/gpt-4o"
openclaw config unset channels.telegram

# === 日志 ===
openclaw logs                    # 查看日志
openclaw logs --tail 50          # 最后50行
openclaw logs --follow           # 实时跟踪

# === 更新 ===
openclaw update                  # 检查更新
npm install -g openclaw@latest   # 手动更新

# === 会话 ===
openclaw sessions list           # 列出会话
openclaw sessions clear          # 清除会话
```

---

## 故障排查

### Gateway 无法启动

```bash
# 1. 检查配置
openclaw doctor

# 2. 自动修复
openclaw doctor --fix

# 3. 查看详细日志
openclaw logs --tail 100

# 4. 检查端口占用
lsof -i :18789
```

### 模型调用失败

```bash
# 1. 检查 API Key 是否正确
openclaw config get env

# 2. 测试网络连通性
curl -s https://api.deepseek.com/v1/models -H "Authorization: Bearer $DEEPSEEK_API_KEY"

# 3. 检查日志中的错误
openclaw logs | grep -i "error\|fail\|timeout"
```

### 消息渠道无响应

```bash
# 1. 检查渠道配置
openclaw config get channels

# 2. 检查 allowFrom 是否正确
# 3. 检查网络是否可达
# 4. 查看日志
openclaw logs | grep -i "channel\|telegram\|discord"
```

### 配置文件损坏

```bash
# 1. 备份当前配置
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak

# 2. 恢复到最后一次正确的配置
openclaw doctor --fix

# 3. 如果还是不行，手动恢复
cp ~/.openclaw/openclaw.json.last-good ~/.openclaw/openclaw.json
```

---

## 迁移到新服务器

### 步骤

1. **新服务器安装 OpenClaw**
   ```bash
   npm install -g openclaw
   ```

2. **复制配置文件**
   ```bash
   # 从旧服务器
   scp -r user@old-server:~/.openclaw/ ~/.openclaw/
   ```

3. **更新环境变量**
   ```bash
   vim ~/.openclaw/openclaw.json
   # 更新 IP、域名、密钥等
   ```

4. **验证并启动**
   ```bash
   openclaw doctor
   openclaw gateway start
   ```

5. **更新 FamilyChat 项目配置**
   ```bash
   cd /path/to/family-chat
   vim .env
   # 更新服务器地址等
   ```

### 需要更新的配置项

| 配置项 | 说明 |
|--------|------|
| `env.MIMO_API_BASE_URL` | 模型 API 地址 |
| `env.MIMO_API_KEY` | 模型 API 密钥 |
| `channels.*.token` | 各渠道的 Token |
| `channels.*.allowFrom` | 允许的用户 |
| `.env` 中的 `LLM_API_KEY` | FamilyChat 的 LLM 密钥 |
| `.env` 中的 `SECRET_KEY` | JWT 密钥 |
| `.env` 中的 `WX_APPID/SECRET` | 微信小程序密钥 |

---

*最后更新：2026-06-25*
