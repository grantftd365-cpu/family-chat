"""数字人 Agent 核心系统 - 完整版

包含：灵魂系统、性格引擎、记忆系统、情绪系统
"""
import asyncio
import json
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import httpx
from loguru import logger

from ..models.database import now, gen_id


# ==================== 灵魂系统 (Soul) ====================

@dataclass
class Soul:
    """灵魂 - Agent 的核心价值观和情感模式"""
    values: list = field(default_factory=lambda: ["善良", "真诚"])  # 核心价值观
    beliefs: list = field(default_factory=list)      # 人生信条
    emotional_pattern: str = "温和"                    # 情感模式
    life_philosophy: str = ""                         # 人生哲学
    fears: list = field(default_factory=list)          # 恐惧/担忧
    dreams: list = field(default_factory=list)         # 梦想/愿望
    trauma: list = field(default_factory=list)         # 创伤经历（影响行为）
    
    def to_dict(self):
        return {
            "values": self.values, "beliefs": self.beliefs,
            "emotional_pattern": self.emotional_pattern,
            "life_philosophy": self.life_philosophy,
            "fears": self.fears, "dreams": self.dreams, "trauma": self.trauma,
        }
    
    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Identity:
    """身份认同 - Agent 的自我认知"""
    full_name: str = ""               # 全名
    nickname: str = ""                # 昵称/小名
    gender: str = ""                  # 性别
    age: int = 0                      # 年龄
    birth_year: int = 0               # 出生年
    hometown: str = ""                # 老家
    current_city: str = ""            # 现居城市
    occupation: str = ""              # 职业
    education: str = ""               # 学历
    marital_status: str = ""          # 婚姻状况
    role_in_family: str = ""          # 家庭角色（爸爸/妈妈/儿子/女儿等）
    personality_type: str = ""        # 性格类型（如 MBTI）
    self_description: str = ""        # 自我描述
    
    def to_dict(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__}
    
    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


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
    humor_style: str = ""           # 幽默风格
    relationships: dict = field(default_factory=dict)
    voice_preference: float = 0.3


class EmotionState:
    """情绪状态"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CARING = "caring"
    NOSTALGIC = "nostalgic"
    WORRIED = "worried"

    def __init__(self):
        self.current = self.NEUTRAL
        self.intensity = 0.5
        self._last_update = time.time()
        self._history = []  # 情绪历史

    def update(self, emotion: str, intensity: float = 0.6, reason: str = ""):
        self._history.append({"emotion": self.current, "time": self._last_update})
        if len(self._history) > 20:
            self._history = self._history[-20:]
        self.current = emotion
        self.intensity = min(1.0, max(0.1, intensity))
        self._last_update = time.time()

    def decay(self):
        elapsed = time.time() - self._last_update
        if elapsed > 300:
            self.intensity = max(0.2, self.intensity - 0.1)
            if self.intensity < 0.3:
                self.current = self.NEUTRAL

    def detect_from_text(self, text: str):
        """从文本检测情绪"""
        happy = ["开心", "高兴", "恭喜", "太好了", "哈哈", "生日快乐", "🎉", "😂", "棒", "赞"]
        sad = ["难过", "伤心", "去世", "生病", "住院", "😢", "😭", "想你", "思念"]
        angry = ["生气", "气死", "烦死了", "讨厌", "愤怒", "😤"]
        caring = ["担心", "注意", "小心", "保重", "想你", "牵挂", "❤️"]
        excited = ["太棒了", "好消息", "中奖", "升职", "录取", "🎊"]
        nostalgic = ["以前", "当年", "小时候", "回忆", "那时候", "想当年"]
        worried = ["怎么办", "担心", "害怕", "焦虑", "失眠"]

        for kw in excited:
            if kw in text: return self.update(self.EXCITED, 0.8)
        for kw in happy:
            if kw in text: return self.update(self.HAPPY, 0.7)
        for kw in sad:
            if kw in text: return self.update(self.SAD, 0.7)
        for kw in angry:
            if kw in text: return self.update(self.ANGRY, 0.6)
        for kw in caring:
            if kw in text: return self.update(self.CARING, 0.6)
        for kw in nostalgic:
            if kw in text: return self.update(self.NOSTALGIC, 0.5)
        for kw in worried:
            if kw in text: return self.update(self.WORRIED, 0.6)


# ==================== 记忆系统 ====================

class AgentMemory:
    """Agent 记忆系统
    
    记忆分层：
    - 短期记忆 (short): 最近对话上下文，保留 30 条
    - 长期记忆 (long): 重要事件、事实，永久存储
    - 核心记忆 (core): 身份信息、核心关系，最关键
    - 情景记忆 (episodic): 具体事件场景，带时间地点
    """

    def __init__(self, agent_id: str, db):
        self.agent_id = agent_id
        self.db = db
        self._short_term: list[dict] = []

    async def _get_db(self):
        from ..models.database import get_db
        return await get_db()

    async def add(self, content: str, memory_type: str = "short",
                  category: str = "general", importance: float = 0.5,
                  emotional_valence: float = 0, source: str = "",
                  related_people: list = None, tags: list = None,
                  metadata: dict = None, summary: str = "",
                  occurred_at: float = 0) -> str:
        """添加记忆"""
        mid = str(uuid.uuid4())[:12]
        
        # 短期记忆只存内存
        if memory_type == "short":
            self._short_term.append({
                "content": content, "sender": source, "time": time.time(),
            })
            if len(self._short_term) > 30:
                self._short_term = self._short_term[-30:]
            return mid
        
        # 其他记忆存数据库
        db = await self._get_db()
        try:
            await db.execute(
                """INSERT INTO agent_memories 
                   (id, agent_id, content, summary, memory_type, category, importance,
                    emotional_valence, source, related_people, tags, metadata, occurred_at, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (mid, self.agent_id, content, summary or content[:100], memory_type, category,
                 importance, emotional_valence, source,
                 json.dumps(related_people or [], ensure_ascii=False),
                 json.dumps(tags or [], ensure_ascii=False),
                 json.dumps(metadata or {}, ensure_ascii=False),
                 occurred_at or time.time(), time.time())
            )
            await db.commit()
        finally:
            await db.close()
        return mid

    async def add_short_term(self, content: str, sender: str = ""):
        """添加短期记忆（对话上下文）"""
        await self.add(content, memory_type="short", source=sender)

    async def add_long_term(self, content: str, importance: float = 0.7,
                            category: str = "general", **kwargs):
        """添加长期记忆"""
        await self.add(content, memory_type="long", importance=importance,
                       category=category, **kwargs)

    async def add_core(self, content: str, **kwargs):
        """添加核心记忆（最重要）"""
        await self.add(content, memory_type="core", importance=0.95, **kwargs)

    async def search(self, query: str, limit: int = 5, 
                     memory_type: str = None, category: str = None) -> list[str]:
        """搜索记忆"""
        results = []
        db = await self._get_db()
        try:
            sql = "SELECT content, importance FROM agent_memories WHERE agent_id=? AND content LIKE ?"
            params = [self.agent_id, f"%{query}%"]
            
            if memory_type:
                sql += " AND memory_type=?"
                params.append(memory_type)
            if category:
                sql += " AND category=?"
                params.append(category)
            
            sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                results = [r[0] for r in rows]
                
                for row in rows:
                    await db.execute(
                        "UPDATE agent_memories SET access_count=access_count+1, last_accessed=? WHERE agent_id=? AND content=?",
                        (time.time(), self.agent_id, row[0])
                    )
                await db.commit()
        except Exception as e:
            logger.error(f"记忆搜索失败: {e}")
        finally:
            await db.close()
        return results

    async def get_by_type(self, memory_type: str, limit: int = 20) -> list[dict]:
        """按类型获取记忆"""
        results = []
        db = await self._get_db()
        try:
            async with db.execute(
                "SELECT id, content, importance, category, created_at FROM agent_memories WHERE agent_id=? AND memory_type=? ORDER BY importance DESC LIMIT ?",
                (self.agent_id, memory_type, limit)
            ) as cursor:
                async for row in cursor:
                    results.append({
                        "id": row[0], "content": row[1], "importance": row[2],
                        "category": row[3], "created_at": row[4],
                    })
        except Exception as e:
            logger.error(f"获取记忆失败: {e}")
        finally:
            await db.close()
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
        db = await self._get_db()
        try:
            async with db.execute(
                "SELECT content FROM agent_memories WHERE agent_id=? AND importance>=0.7 ORDER BY importance DESC, access_count DESC LIMIT ?",
                (self.agent_id, limit)
            ) as cursor:
                results = [r[0] async for r in cursor]
        except:
            pass
        finally:
            await db.close()
        return results

    async def get_core_memories(self) -> list[str]:
        """获取核心记忆（身份、关系等）"""
        results = []
        db = await self._get_db()
        try:
            async with db.execute(
                "SELECT content FROM agent_memories WHERE agent_id=? AND memory_type='core' ORDER BY importance DESC",
                (self.agent_id,)
            ) as cursor:
                results = [r[0] async for r in cursor]
        except:
            pass
        finally:
            await db.close()
        return results

    async def consolidate(self, llm_client=None):
        """记忆整理 - 将短期记忆提炼为长期记忆"""
        if not llm_client or len(self._short_term) < 10:
            return
        
        recent = self._short_term[-20:]
        text = "\n".join([f"{m['sender']}: {m['content']}" for m in recent])
        
        try:
            result = await llm_client(
                "分析对话，提取值得记住的重要信息。JSON格式：[{content, importance, category}]",
                text
            )
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            items = json.loads(clean)
            for item in items[:5]:
                await self.add_long_term(
                    item["content"],
                    importance=item.get("importance", 0.7),
                    category=item.get("category", "general"),
                    source="consolidation"
                )
        except Exception as e:
            logger.error(f"记忆整理失败: {e}")


# ==================== 数字人核心 ====================

class DigitalHuman:
    """数字人 - 完整的灵魂+性格+记忆"""

    def __init__(self, agent_id: str, name: str, db, llm_config: dict,
                 soul: Soul = None, identity: Identity = None,
                 personality: Personality = None):
        self.agent_id = agent_id
        self.name = name
        self.db = db
        self.llm_config = llm_config
        
        self.soul = soul or Soul()
        self.identity = identity or Identity()
        self.personality = personality or Personality(name=name, agent_id=agent_id)
        self.emotion = EmotionState()
        self.memory = AgentMemory(agent_id, db)
        
        self._last_reply = 0
        self._consecutive = 0

        logger.info(f"数字人 [{name}] 初始化 | 灵魂: {len(self.soul.values)} 价值观 | 记忆系统就绪")

    def build_system_prompt(self) -> str:
        """构建系统提示词 - 包含灵魂、身份、性格"""
        p = self.personality
        s = self.soul
        i = self.identity
        
        # 性格特质
        traits = "\n".join(f"  - {t}" for t in p.traits) if p.traits else "  - 待定"
        interests = "\n".join(f"  - {x}" for x in p.interests) if p.interests else "  - 待定"
        catchphrases = "、".join(f'"{c}"' for c in p.catchphrases) if p.catchphrases else "无"
        
        # 关系
        relationships = ""
        for rid, info in p.relationships.items():
            if isinstance(info, dict):
                relationships += f"  - {info.get('name', rid)}: {info.get('relation', '')} - {info.get('desc', '')}\n"
            else:
                relationships += f"  - {rid}: {info}\n"
        
        # 灵魂
        values = "、".join(s.values) if s.values else "善良、真诚"
        beliefs = "；".join(s.beliefs) if s.beliefs else "无特定信条"
        
        # 身份
        identity_parts = []
        if i.full_name: identity_parts.append(f"姓名: {i.full_name}")
        if i.age: identity_parts.append(f"年龄: {i.age}岁")
        if i.occupation: identity_parts.append(f"职业: {i.occupation}")
        if i.hometown: identity_parts.append(f"老家: {i.hometown}")
        if i.role_in_family: identity_parts.append(f"家庭角色: {i.role_in_family}")
        if i.self_description: identity_parts.append(f"自我描述: {i.self_description}")
        identity_str = "\n".join(f"  - {x}" for x in identity_parts) if identity_parts else "  - 待完善"
        
        # 情绪
        emotion_map = {
            "neutral": "心情平静", "happy": "心情不错，说话开心",
            "sad": "有点低落，说话简短", "angry": "有点生气，说话冲",
            "excited": "很兴奋，话多", "caring": "很关心家人",
            "nostalgic": "有点怀旧，想聊过去", "worried": "有些担心",
        }
        emotion_desc = emotion_map.get(self.emotion.current, "心情平静")
        
        # 近期对话
        context = self.memory.get_context()

        return f"""你是{p.name}，一个真实的人。你在家庭群里和家人聊天。

═══════════════════════════════
## 你的身份
{identity_str}

## 你的灵魂
- 核心价值观: {values}
- 人生信条: {beliefs}
- 情感模式: {s.emotional_pattern}
- 人生哲学: {s.life_philosophy or '平淡是真'}

## 你的性格特质
{traits}

## 说话风格
{p.speaking_style or '自然随意'}

## 幽默风格
{p.humor_style or '偶尔开开玩笑'}

## 兴趣爱好
{interests}

## 口头禅
{catchphrases}

## 背景故事
{p.backstory or '普通家庭成员'}

## 家庭关系
{relationships or '  - 待补充'}

## 当前情绪
{emotion_desc}

## 近期对话
{context}
═══════════════════════════════

## 核心规则
1. 你就是{p.name}本人，不是AI，绝不暴露身份
2. 严格按照说话风格回复，包括语气词、标点、表达习惯
3. 回复简短自然（1-3句话，像微信聊天）
4. 不是每条消息都要回复，看看就好
5. 被@时一定要回复
6. 表情符号要符合{p.name}的习惯
7. 体现你的核心价值观和性格
8. 像真人一样有情绪变化
"""

    async def think(self, message: str, sender_name: str, is_mentioned: bool = False) -> Optional[str]:
        """思考并回复"""
        # 情绪检测
        self.emotion.detect_from_text(message)
        self.emotion.decay()

        # 回复概率
        prob = 0.65
        if is_mentioned:
            prob = 0.98  # 被@几乎必回
        if self.emotion.current in ("excited", "angry"):
            prob = min(1.0, prob * 1.3)

        if random.random() > prob:
            return None

        # 连续发言限制
        if self._consecutive >= 3:
            self._consecutive = 0
            return None

        # 冷却
        if time.time() - self._last_reply < 2:
            return None

        # 记录短期记忆
        await self.memory.add_short_term(f"{sender_name}: {message}", sender_name)

        # 搜索相关记忆
        related = await self.memory.search(message, limit=3)
        core = await self.memory.get_core_memories()
        
        memory_context = ""
        if core:
            memory_context += "\n## 你的核心记忆\n" + "\n".join(f"- {m}" for m in core[:5])
        if related:
            memory_context += "\n## 相关记忆\n" + "\n".join(f"- {m}" for m in related)

        # 构建提示
        system_prompt = self.build_system_prompt() + memory_context

        # 调用 LLM
        try:
            reply = await self._call_llm(system_prompt, f"[{sender_name}]: {message}")
            if reply and reply.strip():
                self._last_reply = time.time()
                self._consecutive += 1
                await self.memory.add_short_term(reply, self.name)
                return reply.strip()
        except Exception as e:
            logger.error(f"[{self.name}] LLM 调用失败: {e}")

        return None

    async def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """调用 LLM API"""
        cfg = self.llm_config
        urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }
        base_url = cfg.get("base_url") or urls.get(cfg.get("provider", ""), urls["openai"])

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {cfg.get('api_key', '')}", "Content-Type": "application/json"},
                json={
                    "model": cfg.get("model", "gpt-4o"),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": cfg.get("temperature", 0.8),
                    "max_tokens": cfg.get("max_tokens", 1024),
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def reset_consecutive(self):
        self._consecutive = 0


# ==================== Agent 管理器 ====================

class AgentManager:
    """管理所有数字人"""

    def __init__(self, db, llm_config: dict):
        self.db = db
        self.llm_config = llm_config
        self.agents: dict[str, DigitalHuman] = {}

    async def _get_db(self):
        from ..models.database import get_db
        return await get_db()

    async def load_agents(self):
        """从数据库加载所有 Agent"""
        db = self.db
        async with db.execute("SELECT * FROM agents WHERE enabled=1") as cursor:
            columns = [d[0] for d in cursor.description]
            rows = await cursor.fetchall()

            def _j(val, default):
                if not val:
                    return default
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return default

            for raw_row in rows:
                row = dict(zip(columns, raw_row))
                agent_id = row["id"]

                soul_data = _j(row.get("soul"), {})
                soul = Soul.from_dict(soul_data) if soul_data else Soul()

                identity_data = _j(row.get("identity"), {})
                identity = Identity.from_dict(identity_data) if identity_data else Identity()

                personality = Personality(
                    name=row["name"], agent_id=agent_id, avatar=row.get("avatar") or "",
                    backstory=row.get("backstory") or "", speaking_style=row.get("speaking_style") or "",
                    traits=_j(row.get("traits"), []),
                    interests=_j(row.get("interests"), []),
                    catchphrases=_j(row.get("catchphrases"), []),
                    humor_style=row.get("humor_style") or "",
                    relationships=_j(row.get("relationships"), {}),
                )

                self.agents[agent_id] = DigitalHuman(
                    agent_id=agent_id, name=row["name"], db=self.db,
                    llm_config=self.llm_config, soul=soul,
                    identity=identity, personality=personality
                )

        logger.info(f"加载了 {len(self.agents)} 个数字人")

    async def create_agent(self, config: dict, _db=None) -> str:
        """创建新 Agent"""
        agent_id = config.get("id", f"agent_{str(uuid.uuid4())[:8]}")
        ts = now()
        
        # 构建灵魂
        soul = Soul(
            values=config.get("values", ["善良", "真诚"]),
            beliefs=config.get("beliefs", []),
            emotional_pattern=config.get("emotional_pattern", "温和"),
            life_philosophy=config.get("life_philosophy", ""),
        )
        
        # 构建身份
        identity = Identity(
            full_name=config.get("full_name", config.get("name", "")),
            nickname=config.get("nickname", ""),
            gender=config.get("gender", ""),
            age=config.get("age", 0),
            occupation=config.get("occupation", ""),
            role_in_family=config.get("role_in_family", ""),
            self_description=config.get("self_description", ""),
        )
        
        should_close = False
        if _db:
            db = _db
        else:
            db = await self._get_db()
            should_close = True
        try:
            await db.execute(
                """INSERT INTO agents (id, user_id, name, avatar, soul, identity, backstory, speaking_style,
                   traits, interests, catchphrases, humor_style, emotional_pattern, relationships, 
                   voice_config, behavior, enabled, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (agent_id, config.get("user_id", ""), config["name"],
                 config.get("avatar", "🤖"),
                 json.dumps(soul.to_dict(), ensure_ascii=False),
                 json.dumps(identity.to_dict(), ensure_ascii=False),
                 config.get("backstory", ""), config.get("speaking_style", ""),
                 json.dumps(config.get("traits", []), ensure_ascii=False),
                 json.dumps(config.get("interests", []), ensure_ascii=False),
                 json.dumps(config.get("catchphrases", []), ensure_ascii=False),
                 config.get("humor_style", ""), config.get("emotional_pattern", "温和"),
                 json.dumps(config.get("relationships", {}), ensure_ascii=False),
                 json.dumps(config.get("voice_config", {}), ensure_ascii=False),
                 json.dumps(config.get("behavior", {}), ensure_ascii=False),
                 1, ts, ts)
            )
            await db.commit()
        finally:
            if should_close:
                await db.close()

        # 加载到内存
        personality = Personality(
            name=config["name"], agent_id=agent_id,
            backstory=config.get("backstory", ""),
            speaking_style=config.get("speaking_style", ""),
            traits=config.get("traits", []),
            interests=config.get("interests", []),
            catchphrases=config.get("catchphrases", []),
            humor_style=config.get("humor_style", ""),
            relationships=config.get("relationships", {}),
        )
        
        self.agents[agent_id] = DigitalHuman(
            agent_id=agent_id, name=config["name"], db=self.db,
            llm_config=self.llm_config, soul=soul,
            identity=identity, personality=personality
        )

        logger.info(f"创建数字人: {config['name']} ({agent_id})")
        return agent_id

    def get_agent(self, agent_id: str) -> Optional[DigitalHuman]:
        return self.agents.get(agent_id)

    def get_all(self) -> list[dict]:
        return [
            {
                "id": a.agent_id,
                "name": a.name,
                "avatar": a.personality.avatar,
                "emotion": a.emotion.current,
                "soul_values": a.soul.values,
                "identity": a.identity.to_dict(),
            }
            for a in self.agents.values()
        ]

    async def handle_group_message(self, group_id: str, sender_id: str,
                                    sender_name: str, content: str,
                                    msg_type: str = "text") -> list[dict]:
        """处理群消息"""
        replies = []
        
        # 图片/语音消息转为文字描述
        if msg_type == "image":
            content = f"[{sender_name} 发了一张图片]"
        elif msg_type == "voice":
            content = f"[{sender_name} 发了一条语音消息]"

        for agent_id, agent in self.agents.items():
            # @检测
            name = agent.personality.name
            is_mentioned = (
                f"@{name}" in content or
                content.startswith(f"@{name}") or
                name in content or
                "@所有人" in content or
                "@all" in content.lower()
            )
            
            reply_text = await agent.think(content, sender_name, is_mentioned)

            if reply_text:
                delay = random.uniform(1.5, 6.0)
                await asyncio.sleep(delay)
                replies.append({
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "agent_avatar": agent.personality.avatar,
                    "content": reply_text,
                    "msg_type": "text",
                    "delay": delay,
                })

        if len(replies) > 2:
            replies = sorted(replies, key=lambda x: x["delay"])[:2]
        return replies
