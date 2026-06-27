# FamilyChat 前端部署文档

> 本文档供阿里云 OpenClaw 部署使用，包含完整的构建、部署、验证流程。

---

## 一、项目结构

```
family-chat/family-chat-app/
├── src/
│   ├── pages/
│   │   ├── chat/chat.vue              # 聊天页（搜索/表情回应/引用跳转）
│   │   ├── refine/refine.vue          # 炼化页（雷达图/进度条）
│   │   └── refine/questionnaire.vue   # 深层问卷页
│   ├── components/
│   │   ├── essence-radar.vue          # 七层雷达图 Canvas 组件
│   │   ├── emoji-panel.vue            # 表情面板
│   │   └── msg-bubble.vue             # 消息气泡
│   ├── utils/
│   │   ├── api.js                     # API 请求封装
│   │   ├── ws.js                      # WebSocket 封装（含自动重连）
│   │   └── response.js                # API 响应格式标准化（新增）
│   ├── stores/
│   │   ├── chat.js                    # 聊天状态管理
│   │   ├── user.js                    # 用户状态
│   │   └── theme.js                   # 主题（暗色模式）
│   ├── uni.scss                       # 设计 Token 系统
│   └── App.vue                        # 入口（含暗色模式 CSS 变量）
├── src/pages.json                     # 路由配置
└── package.json
```

---

## 二、新增/变更文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `src/utils/response.js` | **新增** | API 响应格式标准化工具 |
| `src/components/essence-radar.vue` | **新增** | 七层雷达图 Canvas 组件 |
| `src/pages/refine/questionnaire.vue` | **新增** | 深层问卷页面 |
| `src/pages/chat/chat.vue` | **修改** | 搜索/表情回应/引用跳转 |
| `src/pages/refine/refine.vue` | **修改** | 雷达图/进度条/问卷入口 |
| `src/pages.json` | **修改** | 注册 questionnaire 路由 |

---

## 三、依赖说明

### 无新增 npm 依赖
所有功能均使用原生 Canvas + Vue3 Composition API 实成，无需额外安装包。

### 后端 API 依赖清单

以下 API 必须在后端实现，前端已做防御性适配（支持多种返回格式）：

| API | 方法 | 说明 | 前端容错 |
|-----|------|------|----------|
| `/api/agents/refine/essence/:agentId` | GET | 获取七层本质数据 | 返回 null 时显示空雷达图 |
| `/api/agents/refine/completeness/:agentId` | GET | 获取炼化完成度 | 返回 null 时隐藏进度条 |
| `/api/agents/refine/questionnaire` | GET | 获取问卷模板 | 返回 null 时使用内置 10 题 |
| `/api/agents/refine/self-description` | POST | 提交问卷炼化 | 错误时 Toast 提示 |
| `/api/messages/:id/reactions/v2` | POST | 添加表情回应 | 错误时 Toast 提示 |
| `/api/messages/:id/reactions/v2/:emoji` | DELETE | 移除表情回应 | 错误时 Toast 提示 |

### 响应格式兼容

`response.js` 工具函数自动适配以下格式：

```javascript
// 列表类：以下格式均可
[]
{data: []}
{list: []}
{items: []}
{records: []}
{data: {list: []}}

// 对象类：以下格式均可
{}
{data: {}}
{result: {}}

// 七层数据：自动处理 0-1 和 0-100 两种范围
{cognition: 0.8}        // 0-1 格式
{cognition: 80}         // 0-100 格式，自动转换
{scores: {cognition: 80}} // 嵌套格式
{layers: {cognition: 0.8}} // 嵌套格式

// 问卷类：以下格式均可
[{id: 'q1', question: '...'}]
[{id: 'q1', label: '...'}]
{questions: [...]}
{q1: '问题1', q2: '问题2'}
```

---

## 四、构建命令

```bash
cd family-chat/family-chat-app

# 安装依赖
npm install

# H5 开发模式
npm run dev:h5

# H5 生产构建
npm run build:h5

# 微信小程序开发模式
npm run dev:mp-weixin

# 微信小程序生产构建
npm run build:mp-weixin
```

---

## 五、环境变量配置

### H5 模式
API 地址使用相对路径（同域部署），无需额外配置。

### 小程序模式
需在 `vite.config.js` 或 `manifest.json` 中配置服务器地址：

```javascript
// vite.config.js
define: {
  __SERVER_URL__: JSON.stringify('https://your-api-domain.com')
}
```

或在运行时存储：
```javascript
uni.setStorageSync('server_url', 'https://your-api-domain.com')
```

---

## 六、Nginx 部署配置（H5）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/family-chat/family-chat-app/dist/build/h5;
    index index.html;

    # SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    # WebSocket 代理
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 七、部署后验证清单（阿里云 OpenClaw 逐条执行）

> ⚠️ 以下每一项都需要实际操作验证，不是看代码确认，而是跑一遍。
> 验证时请打开浏览器控制台（F12），观察是否有红色报错。

### 7.1 基础功能（必须先通过）
- [ ] `npm run build:h5` 构建成功，无报错
- [ ] 构建产物 `dist/build/h5/index.html` 存在
- [ ] Nginx 配置后访问首页无白屏
- [ ] 登录/注册流程正常
- [ ] 控制台无 `WebSocket connection failed` 报错
- [ ] 控制台无 `Uncaught TypeError` 或 `ReferenceError`

### 7.2 聊天页验证（chat.vue）
- [ ] 消息列表正常加载，气泡样式正确
- [ ] 导航栏右侧显示 🔍 搜索图标 + 👤 图标（两个图标并排）
- [ ] 点击 🔍 → 搜索覆盖层弹出，输入框自动聚焦
- [ ] 输入 "你好" → 300ms 后消息列表过滤，只显示含 "你好" 的消息
- [ ] 输入空格/清空 → 恢复显示全部消息
- [ ] 搜索结果超过 200 条时，底部显示 "找到 200+ 条结果"
- [ ] 点击某条搜索结果 → 搜索关闭，页面滚动到该消息，消息绿色闪烁 2 秒后消失
- [ ] 点击 "取消" → 搜索关闭，恢复正常列表
- [ ] 长按某条消息 → 气泡上方弹出一排表情（👍❤️😂😮😢🎉），带缩放动画
- [ ] 点击 👍 → 消息底部出现 "👍1"，控制台无报错
- [ ] 再次点击 👍 → "👍1" 消失（取消反应）
- [ ] 如果有引用回复的消息 → 点击引用区域 → 滚动到原消息 + 绿色闪烁
- [ ] 断开网络 → 重连 → 控制台显示 "WS 已连接" → 消息自动同步

### 7.3 炼化页验证（refine.vue）
- [ ] 进入炼化页 → 数字人列表正常加载
- [ ] 选择第一个数字人 → 页面顶部出现雷达图
- [ ] 雷达图有 7 个顶点（认知/知识/情感/语言/价值/关系/叙事）
- [ ] 雷达图有动画效果（从中心逐步展开，约 0.5 秒完成）
- [ ] 雷达图下方图例显示各维度名称 + 百分比 + 颜色条
- [ ] 如果 API 返回七层数据 → 进度条有填充
- [ ] 如果 API 返回 null/404 → 雷达图和进度条不显示（不报错）
- [ ] 已完成（100%）的维度右侧显示 ✅
- [ ] 右上角显示总体完成度百分比
- [ ] "深层问卷" 入口卡片可点击，跳转到问卷页

### 7.4 问卷页验证（questionnaire.vue）
- [ ] 进入问卷页 → 显示 10 个问题（从 API 或默认列表）
- [ ] 每个问题有编号圆圈 + 问题文本 + 输入框
- [ ] 输入文字 → 左侧进度条实时更新
- [ ] 输入 1 个问题后 → "提交并炼化" 按钮可点击
- [ ] 点击提交 → 按钮显示 "炼化中..." + ⏳ 旋转动画
- [ ] 提交成功 → 显示 "炼化完成" + 七维对比图
- [ ] 对比图每个维度有 "前" 和 "后" 两条进度条
- [ ] 如果后端返回了 traits → 显示性格特征、说话风格等
- [ ] 点击 "重新填写" → 回到问卷输入状态
- [ ] 如果后端 API 不存在 → 使用默认 10 题，不报错
- [ ] 如果提交失败 → Toast 提示 "炼化失败: xxx"，不崩溃

### 7.5 暗色模式验证
- [ ] 切换到暗色模式（如果有切换入口）
- [ ] 聊天页：消息气泡、输入框、搜索覆盖层文字可读
- [ ] 炼化页：雷达图标签、进度条文字可读
- [ ] 问卷页：问题文字、输入框背景对比度足够
- [ ] 无 "黑底黑字" 或 "白底白字" 的不可读情况

### 7.6 API 异常场景验证（关键！）
> 以下测试前端对后端异常的容错能力

- [ ] 后端未实现 `/api/agents/refine/essence/:id` → 返回 404 → 雷达图不显示，无报错
- [ ] 后端未实现 `/api/agents/refine/completeness/:id` → 返回 404 → 进度条不显示，无报错
- [ ] 后端未实现 `/api/agents/refine/questionnaire` → 返回 404 → 使用默认 10 题
- [ ] 后端返回格式不标准（如 `{code:0, data:{list:[...]}}`）→ 前端自动适配
- [ ] 后端七层数据返回 0-100 范围 → 前端自动转为 0-1（如 80 → 80%）
- [ ] 网络断开时点击提交 → Toast 提示 "炼化失败"，不崩溃
- [ ] 连续快速点击 "提交" 按钮 → 只发送一次请求
- [ ] 连续快速点击表情回应 → 只发送一次请求（reactingMsgId 锁）

---

## 八、已知限制（需后续优化）

| 优先级 | 限制 | 影响 | 建议方案 |
|--------|------|------|----------|
| P1 | 搜索为前端内存过滤 | 消息 > 5000 条时卡顿 | 后端提供 `/api/messages/search` 接口 |
| P1 | Canvas 旧版小程序无高清 | 基础库 < 2.9.0 模糊 | 升级基础库或用 SVG 替代 |
| P2 | 表情回应前端防抖 | 极端高频点击可能重复 | 后端做幂等处理 |
| P2 | 问卷答案不持久化 | 页面关闭丢失 | 加 localStorage 缓存 |
| P3 | 搜索结果无关键词高亮 | 体验略差 | 用 rich-text 组件实现高亮 |

---

## 九、回滚方案

如新功能出现严重问题，3 条命令回退：

```bash
cd family-chat/family-chat-app

# 回退修改的文件
git checkout HEAD~1 -- \
  src/pages/chat/chat.vue \
  src/pages/refine/refine.vue

# 删除新增文件
git rm -f src/components/essence-radar.vue
  src/pages/refine/questionnaire.vue \
  src/utils/response.js

# 重新构建
npm run build:h5
```

原有聊天/炼化功能完全不受影响，新增文件独立性强，无交叉依赖。

---

## 十、给阿里云 OpenClaw 的执行摘要

**本次变更：6 个功能 + 1 个工具库**

1. 聊天内搜索（🔍 图标 → 实时过滤 → 跳转高亮）
2. 七层雷达图（Canvas 组件，H5/小程序双端兼容）
3. 深层问卷页（10 题 → 提交 → 前后对比）
4. 炼化进度可视化（七维进度条 + ✅ + 总体百分比）
5. 消息引用跳转（点击引用 → 滚动 + 闪烁）
6. 表情回应 UI（长按 → 快速表情 → 底部显示 → 可取消）
7. API 响应标准化工具 `response.js`（防格式不一致）

**风险已排除：**
- API 返回格式不一致 → `response.js` 自动适配 10+ 种格式
- Canvas 小程序兼容 → 三路降级（type=2d → canvas-id → legacy）
- 空数据/网络异常 → 全面 `.catch(() => null)` 兜底
- 并发点击 → `reactingMsgId` 锁 + `submitting` 守卫
- WebSocket 断线 → 重连后自动同步消息
- 暗色模式 → 使用 CSS 变量，自动适配

**需要实测验证的：** 见第七节验证清单（逐条勾选）
