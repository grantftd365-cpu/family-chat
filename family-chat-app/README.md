# 📱 FamilyChat App - uni-app 跨平台前端

基于 uni-app + Vue 3 构建的跨平台前端，支持编译到 **微信小程序**、**Android/iOS APP** 和 **H5 Web**。

## 🚀 快速开始

### 环境要求

- Node.js 18+
- npm 或 pnpm

### 安装依赖

```bash
cd family-chat-app
npm install
```

### 开发调试

```bash
# H5 Web 版
npm run dev:h5

# 微信小程序
npm run dev:mp-weixin

# Android APP
npm run dev:app-android

# iOS APP
npm run dev:app-ios
```

### 构建发布

```bash
# 构建 H5
npm run build:h5

# 构建微信小程序（产物在 dist/build/mp-weixin/）
npm run build:mp-weixin

# 构建 APP
npm run build:app
```

## 📦 项目结构

```
family-chat-app/
├── src/
│   ├── pages/              # 页面
│   │   ├── login/          # 登录/注册
│   │   ├── index/          # 消息列表（TabBar）
│   │   ├── chat/           # 聊天页面
│   │   ├── contacts/       # 通讯录（TabBar）
│   │   ├── profile/        # 个人中心（TabBar）
│   │   ├── moments/        # 朋友圈
│   │   ├── search/         # 搜索
│   │   ├── favorites/      # 收藏
│   │   └── settings/       # 设置
│   ├── components/         # 组件
│   │   ├── msg-bubble.vue  # 消息气泡
│   │   ├── chat-item.vue   # 聊天列表项
│   │   ├── contact-item.vue # 联系人项
│   │   ├── moment-item.vue # 朋友圈动态项
│   │   ├── emoji-panel.vue # 表情面板
│   │   └── red-envelope.vue # 红包组件
│   ├── stores/             # Pinia 状态管理
│   │   ├── user.js         # 用户状态
│   │   ├── chat.js         # 聊天状态
│   │   └── theme.js        # 主题状态
│   ├── utils/              # 工具函数
│   │   ├── api.js          # API 请求封装
│   │   ├── ws.js           # WebSocket 封装
│   │   └── storage.js      # 本地存储封装
│   ├── static/             # 静态资源
│   ├── App.vue             # 根组件
│   ├── main.js             # 入口文件
│   ├── pages.json          # 页面路由配置
│   ├── manifest.json       # 应用配置
│   └── uni.scss            # 全局样式变量
├── package.json
├── vite.config.js
└── README.md
```

## 🎨 功能特性

- ✅ 登录/注册（邮箱 + 微信小程序登录）
- ✅ 消息列表 + 未读数
- ✅ 聊天（文字/图片/语音/文件/红包）
- ✅ 消息回复/撤回/转发/置顶/表情反应
- ✅ 通讯录（数字人 + 好友）
- ✅ 朋友圈（发布/点赞/评论）
- ✅ 全局搜索
- ✅ 收藏
- ✅ 设置（暗黑模式/AI模型配置/炼化数字人）
- ✅ WebSocket 实时通信
- ✅ 暗黑模式
- ✅ 多端适配（rpx）

## ⚙️ 后端配置

后端为 Python FastAPI，无需修改。API 地址配置：

- **H5 模式**：自动使用同域相对路径
- **小程序/APP 模式**：在 `src/utils/api.js` 中修改 `CONFIG.baseUrl`

## 📝 注意事项

1. 微信小程序需要在 `manifest.json` 中配置 AppID
2. APP 打包需要使用 HBuilderX 或 CLI
3. 图片上传和语音功能在小程序中需要用户授权
4. WebSocket 地址在非 H5 模式下需要手动配置

## 📄 License

MIT License
