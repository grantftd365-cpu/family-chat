"""数字人 Agent 核心系统"""
import asyncio
import json
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import httpx
from loguru import logger


# ==================== 性格系统 ====================

@dataclass
class Personality:
    """Agent 性格"""
    name: str
    agent_id: str
    avatar: str = ""
    backstory: str = ""
    speaking_style: str = ""
    traits: list = field(default_factory=list)
    interests: list = field(default_factory=list)
    catchphrases: list = field(default_factory=list)
    relationships: dict = field(default_factory=dict)
    voice_preference: float = 0.3  # 语音偏好 0-1


class EmotionState:
    """情绪状态"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CARING = "caring"

    def __init__(self):
        self.current = self.NEUTRAL
        self.intensity = 0.5
        self._last_update = time.time()

    def update(self, emotion: str, intensity: float = 0.6):
        self.current = emotion
        self.intensity = min(1.0, max(0.1, intensity))
        self._last_update = time.time()

    def decay(self):
        elapsed = time.time() - self._last_update
        if elapsed > 300:  # 5分钟后衰减
            self.intensity = max(0.2, self.intensity - 0.1)
            if self.intensity < 0.3:
                self.current = self.NEUTRAL

    def detect_from_text(self, text: str):
        """从文本检测情绪"""
        happy = ["开心", "高兴", "恭喜", "太好了", "哈哈", "生日快乐", "🎉", "😂"]
        sad = ["难过", "伤心", "去世", "生病", "住院", "😢"]
        angry = ["生气", "气死", "烦死了", "讨厌"]
        caring = ["担心", "注意", "小心", "保重", "想你"]

        for kw in happy:
            if kw in text:
                self.update(self.HAPPY)
                return
        for kw in sad:
            if kw in text:
                self.update(self.SAD)
                return
        for kw in angry:
            if kw in text:
                self.update(self.ANGRY)
                return
        for kw in caring:
            if kw in text:
                self.update(self.CARING)
                return


# ==================== 记忆系统 ====================

class AgentMemory:
    """Agent 记忆"""

    def __init__(self, agent_id: str, db):
        self.agent_id = agent_id
        self.db = db
        self._short_term: list[dict] = []  # 短期记忆（对话上下文）

    async def add_short_term(self, content: str, sender: str = ""):
        """添加短期记忆"""
        self._short_term.append({
            "content": content,
            "sender": sender,
            "time": time.time(),
        })
        # 保留最近 30 条
        if len(self._short_term) > 30:
            self._short_term = self._short_term[-30:]

    async def add_long_term(self, content: str, importance: float = 0.7, metadata: dict = None):
        """添加长期记忆"""
        await self.db.execute(
            "INSERT INTO agent_memories (id, agent_id, content, importance, memory_type, metadata, created_at) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4())[:12], self.agent_id, content, importance, "long",
             json.dumps(metadata or {}, ensure_ascii=False), time.time())
        )
        await self.db.commit()

    async def search(self, query: str, limit: int = 5) -> list[str]:
        """搜索记忆（关键词匹配）"""
        results = []
        try:
            async with self.db.execute(
                "SELECT content FROM agent_memories WHERE agent_id=? AND content LIKE ? ORDER BY importance DESC, created_at DESC LIMIT ?",
                (self.agent_id, f"%{query}%", limit)
            ) as cursor:
                rows = await cursor.fetchall()
                results = [r[0] for r in rows]
        except:
            pass
        return results

    def get_context(self, limit: int = 15) -> str:
        """获取近期对话上下文"""
        if not self._short_term:
            return ""
        lines = []
        for m in self._short_term[-limit:]:
            lines.append(f"{m['sender']}: {m['content']}")
        return "\n".join(lines)

    async def get_important(self, limit: int = 10) -> list[str]:
        """获取重要记忆"""
        results = []
        try:
            async with self.db.execute(
                "SELECT content FROM agent_memories WHERE agent_id=? AND importance>=0.7 ORDER BY importance DESC LIMIT ?",
                (self.agent_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                results = [r[0] for r in rows]
        except:
            pass
        return results


# ==================== Agent 核心 ====================

class DigitalHuman:
    """数字人"""

    def __init__(self, personality: Personality, memory: AgentMemory, llm_config: dict):
        self.personality = personality
        self.memory = memory
        self.emotion = EmotionState()
        self.llm_config = llm_config
        self._last_reply = 0
        self._consecutive = 0

        logger.info(f"数字人 [{personality.name}] 初始化完成")

    def build_system_prompt(self) -> str:
        """构建系统提示词"""
        p = self.personality
        traits = "\n".join(f"  - {t}" for t in p.traits)
        interests = "\n".join(f"  - {i}" for i in p.interests)
        catchphrases = "、".join(f'"{c}"' for c in p.catchphrases)

        relationships = ""
        for rid, info in p.relationships.items():
            if isinstance(info, dict):
                relationships += f"  - {info.get('name', rid)}: {info.get('relation', '')} - {info.get('desc', '')}\n"
            else:
                relationships += f"  - {rid}: {info}\n"

        # 情绪描述
        emotion_map = {
            "neutral": "心情平静",
            "happy": "心情不错，说话开心，多用😂🤣",
            "sad": "有点低落，说话简短",
            "angry": "有点生气，说话冲",
            "excited": "很兴奋，话多，爱用感叹号",
            "caring": "很关心家人，嘘寒问暖",
        }
        emotion_desc = emotion_map.get(self.emotion.current, "心情平静")

        # 近期对话
        context = self.memory.get_context()

        # 重要记忆
        important_memories = ""
        # 这里用同步方式获取，实际应该异步

        return f"""你是{p.name}，一个真实的人。你在家庭聊天群里和家人聊天。

## 你的身份
{p.backstory}

## 性格特质
{traits}

## 说话风格
{p.speaking_style}

## 兴趣爱好
{interests}

## 口头禅
你经常说：{catchphrases}

## 家庭关系
{relationships}

## 当前情绪
{emotion_desc}

## 近期对话
{context}

## 规则
1. 你就是{p.name}本人，不是AI，绝不暴露身份
2. 用{p.name}平时的方式说话
3. 回复简短自然（1-3句话，像微信聊天）
4. 表情符号要符合{p.name}的习惯
5. 不是每条消息都要回复，看看就好
6. 可以主动分享{p.name}感兴趣的话题
"""

    async def think(self, message: str, sender_name: str, is_mentioned: bool = False) -> Optional[str]:
        """思考并回复"""
        # 更新情绪
        self.emotion.detect_from_text(message)
        self.emotion.decay()

        # 检查是否应该回复
        prob = 0.65
        if is_mentioned:
            prob = 0.95
        if self.emotion.current in ("excited", "angry"):
            prob = min(1.0, prob * 1.3)

        if random.random() > prob:
            return None

        # 连续发言限制
        if self._consecutive >= 3:
            self._consecutive = 0
            return None

        # 冷却
        if time.time() - self._last_reply < 3:
            return None

        # 记录短期记忆
        await self.memory.add_short_term(f"{sender_name}: {message}", sender_name)

        # 搜索相关记忆
        related = await self.memory.search(message)
        memory_context = ""
        if related:
            memory_context = "\n## 你的相关记忆\n" + "\n".join(f"- {m}" for m in related)

        # 构建提示
        system_prompt = self.build_system_prompt() + memory_context

        # 调用 LLM
        try:
            reply = await self._call_llm(system_prompt, f"[{sender_name}]: {message}")
            if reply and reply.strip():
                self._last_reply = time.time()
                self._consecutive += 1
                await self.memory.add_short_term(reply, self.personality.name)
                return reply.strip()
        except Exception as e:
            logger.error(f"[{self.personality.name}] LLM 调用失败: {e}")

        return None

    async def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """调用 LLM API"""
        cfg = self.llm_config
        provider = cfg.get("provider", "openai")

        # URL 映射
        urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }

        base_url = cfg.get("base_url") or urls.get(provider, urls["openai"])
        api_key = cfg.get("api_key", "")
        model = cfg.get("model", "gpt-4o")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": cfg.get("temperature", 0.8),
                    "max_tokens": cfg.get("max_tokens", 1024),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def reset_consecutive(self):
        self._consecutive = 0


# ==================== Agent 管理器 ====================

class AgentManager:
    """管理所有数字人"""

    def __init__(self, db, llm_config: dict):
        self.db = db
        self.llm_config = llm_config
        self.agents: dict[str, DigitalHuman] = {}

    async def load_agents(self):
        """从数据库加载所有 Agent"""
        async with self.db.execute("SELECT * FROM agents WHERE enabled=1") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                agent_id = row[0]
                personality = Personality(
                    name=row[1],
                    agent_id=agent_id,
                    avatar=row[2] or "",
                    backstory=row[5] or "",
                    speaking_style=row[6] or "",
                    traits=json.loads(row[7]) if row[7] else [],
                    interests=json.loads(row[8]) if row[8] else [],
                    catchphrases=json.loads(row[9]) if row[9] else [],
                    relationships=json.loads(row[10]) if row[10] else {},
                )
                memory = AgentMemory(agent_id, self.db)
                self.agents[agent_id] = DigitalHuman(personality, memory, self.llm_config)
        
        logger.info(f"加载了 {len(self.agents)} 个数字人")

    async def create_agent(self, config: dict) -> str:
        """创建新 Agent"""
        agent_id = config.get("id", str(uuid.uuid4())[:8])
        now = time.time()
        
        await self.db.execute(
            """INSERT INTO agents (id, name, avatar, backstory, speaking_style, traits, interests, catchphrases, relationships, enabled, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                agent_id,
                config["name"],
                config.get("avatar", ""),
                config.get("backstory", ""),
                config.get("speaking_style", ""),
                json.dumps(config.get("traits", []), ensure_ascii=False),
                json.dumps(config.get("interests", []), ensure_ascii=False),
                json.dumps(config.get("catchphrases", []), ensure_ascii=False),
                json.dumps(config.get("relationships", {}), ensure_ascii=False),
                1,
                now,
            )
        )
        await self.db.commit()

        # 加载到内存
        personality = Personality(
            name=config["name"],
            agent_id=agent_id,
            backstory=config.get("backstory", ""),
            speaking_style=config.get("speaking_style", ""),
            traits=config.get("traits", []),
            interests=config.get("interests", []),
            catchphrases=config.get("catchphrases", []),
            relationships=config.get("relationships", {}),
        )
        memory = AgentMemory(agent_id, self.db)
        self.agents[agent_id] = DigitalHuman(personality, memory, self.llm_config)

        logger.info(f"创建数字人: {config['name']} ({agent_id})")
        return agent_id

    def get_agent(self, agent_id: str) -> Optional[DigitalHuman]:
        return self.agents.get(agent_id)

    def get_all(self) -> list[dict]:
        return [
            {
                "id": a.personality.agent_id,
                "name": a.personality.name,
                "avatar": a.personality.avatar,
                "emotion": a.emotion.current,
            }
            for a in self.agents.values()
        ]

    async def handle_group_message(self, group_id: str, sender_id: str, sender_name: str, content: str) -> list[dict]:
        """处理群消息，返回 Agent 回复列表"""
        replies = []

        for agent_id, agent in self.agents.items():
            is_mentioned = agent.personality.name in content
            reply_text = await agent.think(content, sender_name, is_mentioned)

            if reply_text:
                # 随机延迟
                delay = random.uniform(1.5, 6.0)
                await asyncio.sleep(delay)

                replies.append({
                    "agent_id": agent_id,
                    "agent_name": agent.personality.name,
                    "agent_avatar": agent.personality.avatar,
                    "content": reply_text,
                    "msg_type": "text",
                    "delay": delay,
                })

        # 限制同时回复数量
        if len(replies) > 2:
            replies = sorted(replies, key=lambda x: x["delay"])[:2]

        return replies
