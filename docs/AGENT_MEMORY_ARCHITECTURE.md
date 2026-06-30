# FamilyChat Agent 与记忆架构

## 结论

FamilyChat 可以做到“每个数字人都是活的 Agent”：每个数字人都有独立人格、情绪、短期上下文、长期/核心/情景记忆，并且能在家庭群中被 `@`、主动回复、与其他数字人继续对话。

当前版本已完成第一阶段的关键改造：群聊消息会进入 `group:{group_id}` 会话，短期记忆按 session 隔离，重要互动会写入持久化记忆，检索时优先使用当前群、当前说话人、当前 Agent 的关系记忆，避免不同群/私聊上下文串在一起。

## Agent 模型

每个数字人是一套独立运行单元：

- `DigitalHuman`：负责人格、情绪、LLM 回复、观察消息。
- `AgentMemory`：负责短期记忆、核心记忆、长期记忆、情景/关系记忆。
- `AgentManager`：负责群聊调度、`@` 识别、Agent-to-Agent 跟进。
- `messages` 表：保存真实聊天记录，包含 `group_id`、`sender_id`、`sender_name`、`is_agent`。
- `agent_memories` 表：保存每个 Agent 自己的长期/核心/情景记忆。

关键原则：Agent 不共享脑子。`我` 和 `老婆` 会分别保存自己的观察、自己的回复、自己与对方/真人用户的关系记忆。

## Session 设计

当前实现统一使用下面的 session 规则：

- 家庭群：`group:{group_id}`
- 未来私聊：建议使用 `dm:{user_id}:{agent_id}`
- 系统主动触发：没有群时使用 `global`，有群时仍使用 `group:{group_id}`

一次群聊中，Agent 提示词会明确包含：

- 当前 `session_id`
- 当前 `group_id`
- 当前发言人 `sender_name/sender_id`
- 当前会话近期对话
- 当前会话/当前说话人的相关关系记忆

因此同一个数字人在不同家庭群、不同测试群、未来私聊里，会拥有不同的短期上下文，长期记忆检索也会屏蔽其他 session 的情景记忆。

## 群聊记忆流程

1. 用户或 Agent 在群里发消息。
2. `AgentManager.handle_group_message()` 计算 `session_id = group:{group_id}`。
3. 群里每个非发送者 Agent 先 `observe()`：
   - 保存当前 session 的短期上下文。
   - 被 `@`、Agent-to-Agent、较重要长消息会固化成 `episodic` 关系记忆。
4. 被 `@` 或概率命中的 Agent 再 `think()`：
   - 读取当前 session 短期上下文。
   - 读取核心记忆。
   - 按当前 `session_id/group_id/sender_id` 检索相关记忆。
   - 调 LLM 生成微信式短回复。
   - 把自己的回复写入同一个 session 的短期记忆和持久关系记忆。
5. 如果 Agent 回复里自然 `@` 了另一个数字人，现有一跳 follow-up 会继续触发 Agent-to-Agent 对话。

## Agent-to-Agent 关系

Agent 之间不是简单“机器人接龙”，而是带关系上下文的互动：

- Agent A 的发言会作为 Agent B 的 `incoming` 记忆。
- Agent B 的回复会作为 Agent B 的 `outgoing` 记忆。
- 这些记忆带 `agent_to_agent`、`session_scoped`、`group_chat` 标签。
- 后续同一群里再聊类似内容时，会优先调出同一 session、同一对话对象的记忆。

这能支撑“我沉稳有思想”“老婆东北人泼辣”“偶尔吵架但有分寸”的家庭群人格关系演化。

## OpenClaw 使用边界

OpenClaw 在阿里云服务器上建议先定位为部署/运维/AI 网关辅助，而不是直接替代 FamilyChat 后端的 Agent 调度器。

原因：FamilyChat 需要强绑定业务数据，包括 `group_id`、`sender_id`、消息表、Agent 记忆表、`@` 规则和 WebSocket 推送。这个调度必须在 FamilyChat 后端里保持确定性，否则容易出现串群、重复回复、权限不清的问题。

推荐用法：

```bash
openclaw doctor
openclaw gateway start --background
openclaw gateway status
openclaw sessions list
```

如果 OpenClaw 后续提供稳定的 OpenAI-compatible gateway endpoint，可以把 FamilyChat 的 LLM 层切到 OpenClaw 网关，而不是改 Agent 业务逻辑：

```bash
sudo nano /opt/family-chat/.env

LLM_PROVIDER=openai
LLM_BASE_URL=http://127.0.0.1:<openclaw-gateway-port>/v1
LLM_MODEL=<openclaw-profile-model>
LLM_API_KEY=<openclaw-or-upstream-key>

sudo systemctl restart familychat
curl https://grantclaw.com/family-chat/api/status
```

如果继续直连 DeepSeek，则保持：

```bash
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=<真实 DeepSeek Key>
```

不要把真实 Key 提交到 GitHub；只放在服务器 `/opt/family-chat/.env`。

## 后续迭代建议

- 增加私聊 `dm:{user_id}:{agent_id}` session。
- 给 `agent_memories` 增加显式 `session_id/group_id/related_person_id` 列和索引，提高长期数据量后的检索效率。
- 增加“每日记忆整理”任务，把同一 session 高频互动压缩为长期关系摘要。
- 增加主动发言策略：按群活跃度、时间、关系紧张度决定是否发起话题。
- 增加家庭关系图谱：丈夫、妻子、父母、孩子、数字人之间的稳定关系单独建模。
