"""数字人 Agent 核心系统 - 社交智能版 (20轮深度优化)

核心架构:
  1. 信息隔离: 每个Agent有独立的世界观，只知道自己的记忆和在场听到的内容
  2. 关系动态: Agent之间的关系会随互动演化
  3. 沟通规则: 社交礼仪、长幼有序、情绪传染、话题延续
  4. 主动/被动: 既能主动发起对话，也能智能响应
  5. 记忆隐私: 每个Agent的记忆边界清晰，不会泄露私聊内容
"""
import asyncio
import json
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

import httpx
from loguru import logger


# ============================================================
#  第1轮: 信息隔离架构 - 每个Agent独立世界观
# ============================================================

class KnowledgeScope:
    """知识范围 - 定义Agent知道什么、不知道什么

    核心原则:
    - 群聊中说的内容 → 群内所有Agent都知道
    - 私聊内容 → 只有参与的Agent知道
    - Agent之间的私下交流 → 只有参与的Agent知道
    - 真人告诉Agent的事 → 只有该Agent知道(除非被允许传播)
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._public_knowledge: list[dict] = []    # 群聊中公开知道的事
        self._private_knowledge: list[dict] = []    # 私聊/私下知道的事
        self._shared_secrets: dict[str, list] = {}  # 谁告诉我的秘密
        self._rumors: list[dict] = []                # 从其他Agent那听来的(可能不准确)

    def observe_public(self, content: str, speaker: str, context: str = "group"):
        """观察到公开信息(群聊)"""
        self._public_knowledge.append({
            "content": content, "speaker": speaker,
            "context": context, "time": time.time(),
        })
        if len(self._public_knowledge) > 100:
            self._public_knowledge = self._public_knowledge[-100:]

    def receive_private(self, content: str, speaker: str):
        """接收到私密信息(私聊/秘密)"""
        self._private_knowledge.append({
            "content": content, "speaker": speaker,
            "time": time.time(), "trusted": True,
        })

    def hear_rumor(self, content: str, from_agent: str, reliability: float = 0.7):
        """从其他Agent那听来的事(二手信息)"""
        self._rumors.append({
            "content": content, "from": from_agent,
            "reliability": reliability, "time": time.time(),
        })

    def what_do_i_know_about(self, topic: str) -> list[str]:
        """关于某个话题我知道什么"""
        results = []
        for k in self._public_knowledge:
            if topic in k["content"]:
                results.append(f"[公开] {k['speaker']}: {k['content']}")
        for k in self._private_knowledge:
            if topic in k["content"]:
                results.append(f"[私下] {k['speaker']}告诉我: {k['content']}")
        for r in self._rumors:
            if topic in r["content"]:
                results.append(f"[听说] 从{r['from']}那听说: {r['content']}(可信度{r['reliability']:.0%})")
        return results

    def can_share(self, content: str, to_agent: str) -> bool:
        """判断是否可以把某个信息分享给另一个Agent"""
        # 秘密不能传播
        for k in self._private_knowledge:
            if k["content"] == content and not k.get("trusted"):
                return False
        return True


# ============================================================
#  第2轮: Agent间关系动态系统
# ============================================================

class RelationType(Enum):
    """关系类型"""
    SPOUSE = "spouse"           # 夫妻
    PARENT_CHILD = "parent"     # 父母-子女
    GRANDPARENT = "grandparent" # 祖孙
    SIBLING = "sibling"         # 兄弟姐妹
    IN_LAW = "in_law"           # 姻亲
    FRIEND = "friend"           # 朋友
    NEIGHBOR = "neighbor"       # 邻居


@dataclass
class RelationState:
    """关系状态 - 动态变化"""
    relation_type: str = ""
    intimacy: float = 0.5        # 亲密度 0-1
    trust: float = 0.5           # 信任度 0-1
    tension: float = 0.0         # 紧张度 0-1 (越高越容易冲突)
    shared_experiences: list = field(default_factory=list)  # 共同经历
    last_interaction: float = 0   # 最后互动时间
    interaction_count: int = 0    # 互动次数
    mood_toward: str = "neutral"  # 对此人的情绪态度

    def update_after_talk(self, positive: bool = True):
        """互动后更新关系"""
        self.interaction_count += 1
        self.last_interaction = time.time()
        if positive:
            self.intimacy = min(1.0, self.intimacy + 0.02)
            self.trust = min(1.0, self.trust + 0.01)
            self.tension = max(0.0, self.tension - 0.05)
        else:
            self.tension = min(1.0, self.tension + 0.1)
            self.intimacy = max(0.0, self.intimacy - 0.03)

    def natural_decay(self):
        """自然衰减 - 长时间不互动关系会淡化"""
        elapsed = time.time() - self.last_interaction
        if elapsed > 86400 * 7:  # 超过7天
            self.intimacy = max(0.2, self.intimacy - 0.01)
            self.tension = max(0.0, self.tension - 0.02)


class RelationGraph:
    """关系图谱 - 管理Agent与所有人的关系"""

    def __init__(self, agent_id: str, db):
        self.agent_id = agent_id
        self.db = db
        self._relations: dict[str, RelationState] = {}

    def get_relation(self, other_id: str) -> RelationState:
        if other_id not in self._relations:
            self._relations[other_id] = RelationState()
        return self._relations[other_id]

    def set_relation(self, other_id: str, relation_type: str, **kwargs):
        state = self.get_relation(other_id)
        state.relation_type = relation_type
        for k, v in kwargs.items():
            if hasattr(state, k):
                setattr(state, k, v)

    def get_closeness_ranking(self) -> list[tuple[str, float]]:
        """按亲密度排序"""
        return sorted(
            [(oid, r.intimacy) for oid, r in self._relations.items()],
            key=lambda x: x[1], reverse=True
        )

    def should_care_about(self, other_id: str) -> float:
        """应该多关心此人(0-1)"""
        r = self.get_relation(other_id)
        base = r.intimacy
        if r.relation_type in ("spouse", "parent", "grandparent"):
            base = max(base, 0.8)
        if r.tension > 0.5:
            base *= 0.6  # 关系紧张时不太想回应
        return min(1.0, base)


# ============================================================
#  第3轮: Agent-Agent自主对话引擎
# ============================================================

class InterAgentChannel:
    """Agent之间的私密沟通通道

    当多个Agent在同一群时，它们可以:
    1. 公开回应(群聊消息)
    2. 私下交流(通过此通道，其他Agent/真人看不到)
    """

    def __init__(self):
        self._channels: dict[str, list[dict]] = {}  # "agentA_agentB" -> messages
        self._lock = asyncio.Lock()

    def _channel_key(self, a1: str, a2: str) -> str:
        return "_".join(sorted([a1, a2]))

    async def send(self, from_id: str, to_id: str, content: str, msg_type: str = "discuss"):
        """Agent之间的私密消息"""
        key = self._channel_key(from_id, to_id)
        async with self._lock:
            if key not in self._channels:
                self._channels[key] = []
            self._channels[key].append({
                "from": from_id, "to": to_id,
                "content": content, "type": msg_type,
                "time": time.time(),
            })
            # 只保留最近20条
            if len(self._channels[key]) > 20:
                self._channels[key] = self._channels[key][-20:]

    async def get_history(self, agent1: str, agent2: str, limit: int = 10) -> list[dict]:
        key = self._channel_key(agent1, agent2)
        return self._channels.get(key, [])[-limit:]

    async def discuss_before_reply(self, agents: list, topic: str, context: str) -> dict:
        """多个Agent先私下讨论再公开回复

        流程:
        1. 相关Agent交换意见
        2. 达成共识或保留分歧
        3. 各自决定是否公开回复
        """
        opinions = {}
        for agent in agents:
            try:
                opinion = await agent._call_llm(
                    f"你是{agent.name}。在家庭群里有人说: {topic}\n"
                    f"你的性格: {', '.join(agent.personality.traits[:3])}\n"
                    f"你的想法是(用一句话概括你的态度):",
                    f"群聊上下文:\n{context}"
                )
                if opinion:
                    opinions[agent.agent_id] = opinion.strip()[:100]
            except Exception:
                pass

        # Agent之间交换意见
        for i, a1 in enumerate(agents):
            for a2 in agents[i+1:]:
                if a1.agent_id in opinions:
                    await self.send(a1.agent_id, a2.agent_id,
                                   f"我觉得: {opinions[a1.agent_id]}", "opinion")

        return opinions


# ============================================================
#  第4轮: 沟通规则引擎
# ============================================================

class CommunicationRules:
    """沟通规则引擎 - 决定谁该说、谁该听、谁该沉默

    规则层次:
    1. 硬规则: 被@必须回复、被提问必须回复
    2. 礼仪规则: 长辈说完晚辈要回应、夫妻要互动
    3. 性格规则: 内向的人少说话、爱唠叨的人多说
    4. 情绪规则: 生气时少说、开心时多说
    5. 场景规则: 严肃话题少插嘴、日常话题多参与
    """

    def __init__(self):
        self._rules = []

    @staticmethod
    def should_reply(agent: 'DigitalHuman', message: str, sender: str,
                     sender_relation: str, is_mentioned: bool,
                     other_replies_count: int, topic_mood: str) -> tuple[bool, float]:
        """判断Agent是否应该回复

        Returns:
            (should_reply: bool, reply_probability: float)
        """
        # ===== 硬规则 =====
        if is_mentioned:
            return True, 0.98
        if "所有人" in message or "大家" in message:
            return True, 0.9

        # ===== 基础概率 =====
        prob = 0.35

        # ===== 关系规则 =====
        intimacy_bonus = {
            "spouse": 0.30, "parent": 0.25, "grandparent": 0.20,
            "sibling": 0.15, "in_law": 0.10, "friend": 0.08,
        }
        prob += intimacy_bonus.get(sender_relation, 0.05)

        # ===== 礼仪规则 =====
        # 晚辈提到长辈相关话题时，长辈应该回应
        if sender_relation in ("parent", "grandparent"):
            prob += 0.10  # 长辈对晚辈说话，晚辈更应回应
        # 夫妻之间
        if sender_relation == "spouse":
            prob += 0.20

        # ===== 性格规则 =====
        traits = agent.personality.traits
        if any(t in str(traits) for t in ["爱唠叨", "话多", "热心"]):
            prob += 0.15
        if any(t in str(traits) for t in ["沉默", "内向", "话少"]):
            prob -= 0.15
        if any(t in str(traits) for t in ["稳重", "严肃"]):
            prob -= 0.05

        # ===== 情绪规则 =====
        emo = agent.emotion.current
        if emo in ("excited", "happy"):
            prob += 0.10
        elif emo in ("angry"):
            prob += 0.15  # 生气时更想说话
        elif emo in ("sad"):
            prob -= 0.10
        elif emo == "nostalgic":
            # 怀旧时，如果话题相关则更想说
            if any(w in message for w in ["以前", "当年", "小时候", "记得"]):
                prob += 0.25

        # ===== 拥挤规则 =====
        if other_replies_count >= 2:
            prob *= 0.3  # 已经有人回复了，减少回复概率
        elif other_replies_count == 1:
            prob *= 0.7

        # ===== 冷却规则 =====
        elapsed = time.time() - agent._last_reply
        if elapsed < 5:
            prob *= 0.2
        elif elapsed < 15:
            prob *= 0.5

        # ===== 连续发言限制 =====
        if agent._consecutive >= 2:
            prob *= 0.1

        prob = max(0.02, min(0.98, prob))
        return random.random() < prob, prob

    @staticmethod
    def get_reply_delay(agent: 'DigitalHuman', message: str, reply_text: str) -> float:
        """计算回复延迟(模拟真人打字)"""
        # 基础: 按字数算打字时间
        typing_speed = random.uniform(20, 45)  # 字/秒
        base_time = len(reply_text) / typing_speed

        # 性格影响: 急性子打字快
        if any(t in str(agent.personality.traits) for t in ["急性子", "直爽"]):
            base_time *= 0.7
        if any(t in str(agent.personality.traits) for t in ["慢性子", "稳重", "认真"]):
            base_time *= 1.3

        # 年龄影响: 年长者打字慢
        if agent.identity.age >= 60:
            base_time *= 1.5
        elif agent.identity.age >= 40:
            base_time *= 1.2

        # 情绪影响: 生气时打字快
        if agent.emotion.current == "angry":
            base_time *= 0.6
        elif agent.emotion.current == "excited":
            base_time *= 0.8

        # 添加随机波动
        delay = base_time + random.uniform(0.3, 2.0)
        return max(1.0, min(delay, 15.0))


# ============================================================
#  第5轮: 灵魂系统 (Soul)
# ============================================================

@dataclass
class Soul:
    """灵魂 - Agent的核心价值观和情感模式"""
    values: list = field(default_factory=lambda: ["善良", "真诚"])
    beliefs: list = field(default_factory=list)
    emotional_pattern: str = "温和"
    life_philosophy: str = ""
    fears: list = field(default_factory=list)
    dreams: list = field(default_factory=list)
    trauma: list = field(default_factory=list)
    moral_lines: list = field(default_factory=list)    # 底线/原则
    humor_style: str = ""                               # 幽默风格
    anger_triggers: list = field(default_factory=list)  # 生气触发点
    comfort_triggers: list = field(default_factory=list) # 安慰触发点

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ============================================================
#  第5轮: 身份系统 (Identity)
# ============================================================

@dataclass
class Identity:
    """身份认同"""
    full_name: str = ""
    nickname: str = ""
    gender: str = ""
    age: int = 0
    birth_year: int = 0
    birthday: str = ""          # MM-DD格式
    hometown: str = ""
    current_city: str = ""
    occupation: str = ""
    education: str = ""
    marital_status: str = ""
    role_in_family: str = ""
    personality_type: str = ""
    self_description: str = ""
    health_conditions: list = field(default_factory=list)  # 健康状况
    daily_schedule: dict = field(default_factory=dict)     # 作息时间

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ============================================================
#  第6轮: 性格系统
# ============================================================

@dataclass
class Personality:
    """Agent性格"""
    name: str
    agent_id: str
    avatar: str = ""
    backstory: str = ""
    speaking_style: str = ""
    traits: list = field(default_factory=list)
    interests: list = field(default_factory=list)
    catchphrases: list = field(default_factory=list)
    humor_style: str = ""
    relationships: dict = field(default_factory=dict)
    voice_preference: float = 0.3
    talkativeness: float = 0.5      # 健谈程度 0-1
    empathy_level: float = 0.5      # 共情能力 0-1
    conflict_style: str = "avoid"   # 冲突风格: avoid / confront / mediate
    learning_rate: float = 0.3      # 从对话中学习的速度


# ============================================================
#  第7轮: 情绪系统(增强 - 传染+共鸣)
# ============================================================

class EmotionState:
    """情绪状态 - 支持传染和共鸣"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CARING = "caring"
    NOSTALGIC = "nostalgic"
    WORRIED = "worried"
    PROUD = "proud"         # 自豪(孩子取得成就)
    EMBARRASSED = "embarrassed"  # 尴尬
    GRATEFUL = "grateful"   # 感恩

    def __init__(self):
        self.current = self.NEUTRAL
        self.intensity = 0.5
        self._last_update = time.time()
        self._history: list[dict] = []
        self._contagion_buffer: list[tuple[str, float]] = []  # 从他人那传染来的情绪

    def update(self, emotion: str, intensity: float = 0.6, reason: str = ""):
        self._history.append({"emotion": self.current, "intensity": self.intensity, "time": self._last_update})
        if len(self._history) > 30:
            self._history = self._history[-30:]
        self.current = emotion
        self.intensity = min(1.0, max(0.1, intensity))
        self._last_update = time.time()

    def decay(self):
        elapsed = time.time() - self._last_update
        if elapsed > 300:
            self.intensity = max(0.15, self.intensity - 0.08)
            if self.intensity < 0.25:
                self.current = self.NEUTRAL

    def absorb_contagion(self, other_emotion: str, other_intensity: float, closeness: float):
        """情绪传染 - 越亲近的人情绪越容易传染"""
        if closeness < 0.3:
            return
        # 传染强度 = 对方情绪强度 * 亲密度 * 衰减系数
        contagion_strength = other_intensity * closeness * 0.4
        if contagion_strength > 0.15:
            self._contagion_buffer.append((other_emotion, contagion_strength))

    def process_contagion(self):
        """处理情绪传染缓冲区"""
        if not self._contagion_buffer:
            return
        # 取最强的传染情绪
        strongest = max(self._contagion_buffer, key=lambda x: x[1])
        if strongest[1] > self.intensity * 0.5:
            # 传染成功
            self.update(strongest[0], min(strongest[1], 0.7))
        self._contagion_buffer.clear()

    def detect_from_text(self, text: str):
        """从文本检测情绪"""
        happy_words = ["开心", "高兴", "恭喜", "太好了", "哈哈", "生日快乐", "🎉", "😂", "棒", "赞", "厉害", "牛"]
        sad_words = ["难过", "伤心", "去世", "生病", "住院", "😢", "😭", "想你", "思念", "走了", "不在了"]
        angry_words = ["生气", "气死", "烦死了", "讨厌", "愤怒", "😤", "过分", "受不了"]
        caring_words = ["担心", "注意", "小心", "保重", "想你", "牵挂", "❤️", "照顾好自己"]
        excited_words = ["太棒了", "好消息", "中奖", "升职", "录取", "🎊", "通过了", "成功了"]
        nostalgic_words = ["以前", "当年", "小时候", "回忆", "那时候", "想当年", "还记得"]
        worried_words = ["怎么办", "担心", "害怕", "焦虑", "失眠", "不确定"]
        proud_words = ["真棒", "为你骄傲", "好样的", "争气", "优秀"]
        grateful_words = ["谢谢", "感谢", "感恩", "辛苦了", "多亏了"]

        word_emotion_map = [
            (excited_words, self.EXCITED, 0.8),
            (proud_words, self.PROUD, 0.7),
            (happy_words, self.HAPPY, 0.7),
            (grateful_words, self.GRATEFUL, 0.6),
            (sad_words, self.SAD, 0.7),
            (angry_words, self.ANGRY, 0.6),
            (caring_words, self.CARING, 0.6),
            (nostalgic_words, self.NOSTALGIC, 0.5),
            (worried_words, self.WORRIED, 0.6),
        ]

        for words, emotion, intensity in word_emotion_map:
            for kw in words:
                if kw in text:
                    return self.update(emotion, intensity)

    @property
    def valence(self) -> float:
        """当前情绪效价(-1负面 ~ +1正面)"""
        positive = {"happy", "excited", "caring", "proud", "grateful"}
        negative = {"sad", "angry", "worried", "embarrassed"}
        if self.current in positive:
            return self.intensity
        elif self.current in negative:
            return -self.intensity
        return 0.0


# ============================================================
#  第8轮: 记忆系统(增强 - 衰减+强化+隐私)
# ============================================================

class AgentMemory:
    """Agent记忆系统

    记忆分层:
    - 短期(short): 最近对话，30条
    - 长期(long): 重要事件，永久
    - 核心(core): 身份/关系，最关键
    - 情景(episodic): 具体场景，带情绪
    - 关于人(person): 对某个人的了解

    记忆衰减:
    - 不被访问的记忆重要性会下降
    - 被频繁访问的记忆会强化
    - 情绪强烈的记忆衰减更慢
    """

    def __init__(self, agent_id: str, db):
        self.agent_id = agent_id
        self.db = db
        self._short_term: list[dict] = []
        self._person_impressions: dict[str, list[str]] = {}  # 对某人的印象

    async def add(self, content: str, memory_type: str = "short",
                  category: str = "general", importance: float = 0.5,
                  emotional_valence: float = 0, source: str = "",
                  related_people: list = None, tags: list = None,
                  metadata: dict = None, summary: str = "",
                  occurred_at: float = 0) -> str:
        mid = str(uuid.uuid4())[:12]

        if memory_type == "short":
            self._short_term.append({"content": content, "sender": source, "time": time.time()})
            if len(self._short_term) > 30:
                self._short_term = self._short_term[-30:]
            return mid

        await self.db.execute(
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
        await self.db.commit()
        return mid

    async def add_short_term(self, content: str, sender: str = ""):
        await self.add(content, memory_type="short", source=sender)

    async def add_long_term(self, content: str, importance: float = 0.7,
                            category: str = "general", **kwargs):
        await self.add(content, memory_type="long", importance=importance, category=category, **kwargs)

    async def add_core(self, content: str, **kwargs):
        await self.add(content, memory_type="core", importance=0.95, **kwargs)

    async def add_about_person(self, person_name: str, content: str, importance: float = 0.6):
        """记录对某个人的了解"""
        if person_name not in self._person_impressions:
            self._person_impressions[person_name] = []
        self._person_impressions[person_name].append(content)
        if len(self._person_impressions[person_name]) > 20:
            self._person_impressions[person_name] = self._person_impressions[person_name][-20:]

        await self.add(
            f"[关于{person_name}] {content}",
            memory_type="long", category="person",
            importance=importance, related_people=[person_name],
        )

    def get_impression_of(self, person_name: str) -> str:
        """获取对某人的印象"""
        impressions = self._person_impressions.get(person_name, [])
        if not impressions:
            return ""
        return f"我对{person_name}的印象: " + "; ".join(impressions[-5:])

    async def search(self, query: str, limit: int = 5,
                     memory_type: str = None, category: str = None) -> list[str]:
        results = []
        try:
            sql = "SELECT content, importance, emotional_valence FROM agent_memories WHERE agent_id=? AND content LIKE ?"
            params = [self.agent_id, f"%{query}%"]
            if memory_type:
                sql += " AND memory_type=?"; params.append(memory_type)
            if category:
                sql += " AND category=?"; params.append(category)
            sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit)
            async with self.db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                results = [r[0] for r in rows]
                for row in rows:
                    await self.db.execute(
                        "UPDATE agent_memories SET access_count=access_count+1, last_accessed=? WHERE agent_id=? AND content=?",
                        (time.time(), self.agent_id, row[0])
                    )
                await self.db.commit()
        except Exception as e:
            logger.error(f"记忆搜索失败: {e}")
        return results

    def get_context(self, limit: int = 15) -> str:
        if not self._short_term:
            return ""
        return "\n".join(f"{m['sender']}: {m['content']}" for m in self._short_term[-limit:])

    async def get_important(self, limit: int = 10) -> list[str]:
        results = []
        try:
            async with self.db.execute(
                "SELECT content FROM agent_memories WHERE agent_id=? AND importance>=0.7 ORDER BY importance DESC, access_count DESC LIMIT ?",
                (self.agent_id, limit)
            ) as cursor:
                results = [r[0] async for r in cursor]
        except:
            pass
        return results

    async def get_core_memories(self) -> list[str]:
        results = []
        try:
            async with self.db.execute(
                "SELECT content FROM agent_memories WHERE agent_id=? AND memory_type='core' ORDER BY importance DESC",
                (self.agent_id,)
            ) as cursor:
                results = [r[0] async for r in cursor]
        except:
            pass
        return results

    async def decay_memories(self):
        """记忆衰减 - 定期调用"""
        try:
            # 降低长期未访问记忆的重要性
            await self.db.execute(
                """UPDATE agent_memories SET importance = MAX(0.1, importance - 0.02)
                   WHERE agent_id=? AND memory_type='long'
                   AND (last_accessed < ? OR last_accessed = 0)
                   AND importance > 0.2""",
                (self.agent_id, time.time() - 86400 * 30)  # 30天未访问
            )
            # 强化频繁访问的记忆
            await self.db.execute(
                """UPDATE agent_memories SET importance = MIN(1.0, importance + 0.05)
                   WHERE agent_id=? AND access_count > 5 AND importance < 0.95""",
                (self.agent_id,)
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"记忆衰减失败: {e}")

    async def consolidate(self, llm_caller=None):
        """记忆整理 - 将短期记忆提炼为长期记忆"""
        if not llm_caller or len(self._short_term) < 10:
            return
        recent = self._short_term[-20:]
        text = "\n".join(f"{m['sender']}: {m['content']}" for m in recent)
        try:
            result = await llm_caller(
                "分析对话，提取值得记住的重要信息。JSON格式：[{content, importance, category}]",
                text
            )
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            items = json.loads(clean)
            for item in items[:5]:
                await self.add_long_term(item["content"], importance=item.get("importance", 0.7),
                                        category=item.get("category", "general"), source="consolidation")
        except Exception as e:
            logger.error(f"记忆整理失败: {e}")


# ============================================================
#  第9轮: 时间感知系统
# ============================================================

class TimeAwareness:
    """时间感知 - 知道现在几点、什么日子"""

    @staticmethod
    def get_time_context() -> dict:
        import datetime
        now = datetime.datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday
        month = now.month
        day = now.day

        time_of_day = "凌晨" if hour < 6 else "早上" if hour < 9 else "上午" if hour < 12 else "中午" if hour < 14 else "下午" if hour < 18 else "晚上" if hour < 22 else "深夜"
        is_weekend = weekday >= 5
        season = "春天" if month in (3,4,5) else "夏天" if month in (6,7,8) else "秋天" if month in (9,10,11) else "冬天"

        # 重要节日
        festivals = {
            (1, 1): "元旦", (2, 14): "情人节", (3, 8): "妇女节",
            (5, 1): "劳动节", (6, 1): "儿童节", (8, 15): "中秋节",
            (9, 10): "教师节", (10, 1): "国庆节", (12, 25): "圣诞节",
        }
        # 农历节日需要额外处理，这里用公历近似
        festival = festivals.get((month, day), "")

        return {
            "time_of_day": time_of_day, "hour": hour,
            "is_weekend": is_weekend, "weekday": weekday,
            "season": season, "festival": festival,
            "date_str": f"{month}月{day}日",
        }

    @staticmethod
    def get_time_greeting(name: str, time_ctx: dict) -> str:
        """根据时间生成问候语"""
        tod = time_ctx["time_of_day"]
        if tod == "早上":
            return f"{name}，早啊！"
        elif tod == "中午":
            return f"{name}，吃午饭了吗？"
        elif tod == "晚上":
            return f"{name}，还没睡呀？"
        elif tod == "深夜":
            return f"{name}，这么晚还没睡？注意身体！"
        return ""

    @staticmethod
    def get_sleep_schedule_hint(identity: Identity) -> Optional[str]:
        """根据年龄推断作息"""
        hour = time.localtime().tm_hour
        if identity.age >= 70:
            if hour >= 21:
                return "老年人通常早睡，可能会犯困"
            if hour <= 5:
                return "老年人通常早起"
        elif identity.age <= 10:
            if hour >= 21:
                return "小孩子该睡觉了"
        return None


# ============================================================
#  第10轮: 社交礼仪系统
# ============================================================

class SocialEtiquette:
    """社交礼仪 - 长幼有序、夫妻默契、隔代亲"""

    @staticmethod
    def get_relation_hierarchy(relation: str) -> int:
        """关系层级(数字越大越年长/辈分越高)"""
        hierarchy = {
            "grandparent": 4, "parent": 3, "spouse": 2,
            "sibling": 1, "in_law": 1, "child": 0, "grandchild": -1,
        }
        return hierarchy.get(relation, 0)

    @staticmethod
    def should_defer_to(agent_role: str, speaker_role: str) -> bool:
        """是否应该让对方先说"""
        agent_h = SocialEtiquette.get_relation_hierarchy(agent_role)
        speaker_h = SocialEtiquette.get_relation_hierarchy(speaker_role)
        # 晚辈让长辈先说
        return agent_h < speaker_h

    @staticmethod
    def get_politeness_level(agent_role: str, target_role: str) -> str:
        """对不同人的礼貌程度"""
        a_h = SocialEtiquette.get_relation_hierarchy(agent_role)
        t_h = SocialEtiquette.get_relation_hierarchy(target_role)
        if t_h > a_h:
            return "respectful"    # 对长辈尊敬
        elif t_h < a_h:
            return "gentle"        # 对晚辈温柔
        else:
            return "casual"        # 同辈随意

    @staticmethod
    def couple_should_interact(agent_id: str, relationships: dict) -> list[str]:
        """夫妻默契 - 配偶应该对对方的消息有反应"""
        partners = []
        for rid, info in relationships.items():
            if isinstance(info, dict) and info.get("relation") == "老伴":
                partners.append(rid)
        return partners


# ============================================================
#  第11轮: 话题追踪系统
# ============================================================

class TopicTracker:
    """话题追踪 - 知道当前在聊什么，延续话题"""

    def __init__(self):
        self.current_topic: str = ""
        self.topic_history: list[dict] = []
        self._topic_keywords: dict[str, list[str]] = {
            "健康": ["身体", "医院", "吃药", "血压", "体检", "生病"],
            "饮食": ["吃饭", "做饭", "好吃", "菜", "饿", "早餐", "午餐", "晚餐"],
            "工作": ["上班", "加班", "老板", "工资", "项目", "开会"],
            "学习": ["考试", "作业", "学校", "老师", "成绩", "毕业"],
            "天气": ["天气", "下雨", "热", "冷", "台风", "晴天"],
            "家庭": ["家里", "装修", "搬家", "孩子", "老人"],
            "娱乐": ["电视", "电影", "游戏", "旅游", "唱歌"],
            "回忆": ["以前", "当年", "小时候", "记得", "想当年"],
        }

    def detect_topic(self, text: str) -> str:
        """检测当前话题"""
        for topic, keywords in self._topic_keywords.items():
            for kw in keywords:
                if kw in text:
                    self.current_topic = topic
                    self.topic_history.append({"topic": topic, "time": time.time(), "text": text[:50]})
                    if len(self.topic_history) > 20:
                        self.topic_history = self.topic_history[-20:]
                    return topic
        return self.current_topic

    def get_topic_continuation_hint(self) -> str:
        """获取话题延续提示"""
        if not self.current_topic:
            return ""
        return f"当前话题: {self.current_topic}"

    def is_same_topic(self, text: str) -> bool:
        """判断是否还在同一话题"""
        return self.detect_topic(text) == self.current_topic


# ============================================================
#  第12轮: 场景感知系统
# ============================================================

class SceneAwareness:
    """场景感知 - 根据聊天内容切换行为模式"""

    class Scene(Enum):
        CASUAL = "casual"           # 日常闲聊
        SERIOUS = "serious"         # 严肃讨论
        CELEBRATION = "celebration" # 庆祝/开心
        COMFORT = "comfort"         # 安慰/支持
        ARGUMENT = "argument"       # 争论
        PLANNING = "planning"       # 计划/安排
        NOSTALGIA = "nostalgia"     # 怀旧

    def __init__(self):
        self.current = self.Scene.CASUAL

    def detect_scene(self, recent_messages: list[str]) -> 'SceneAwareness.Scene':
        """从最近消息检测场景"""
        text = " ".join(recent_messages[-5:])

        # 争论检测
        argue_words = ["不对", "不是", "错了", "反对", "不同意", "凭什么"]
        if sum(1 for w in argue_words if w in text) >= 2:
            self.current = self.Scene.ARGUMENT
            return self.current

        # 庆祝检测
        celebrate_words = ["恭喜", "太好了", "庆祝", "生日快乐", "🎉", "🎊"]
        if any(w in text for w in celebrate_words):
            self.current = self.Scene.CELEBRATION
            return self.current

        # 安慰检测
        comfort_words = ["难过", "伤心", "生病", "住院", "😢", "担心"]
        if any(w in text for w in comfort_words):
            self.current = self.Scene.COMFORT
            return self.current

        # 严肃检测
        serious_words = ["重要", "必须", "认真", "严肃", "决定", "商量"]
        if any(w in text for w in serious_words):
            self.current = self.Scene.SERIOUS
            return self.current

        # 怀旧检测
        nostalgia_words = ["以前", "当年", "小时候", "回忆", "想当年"]
        if any(w in text for w in nostalgia_words):
            self.current = self.Scene.NOSTALGIA
            return self.current

        # 计划检测
        plan_words = ["明天", "下周", "计划", "安排", "打算", "什么时候"]
        if any(w in text for w in plan_words):
            self.current = self.Scene.PLANNING
            return self.current

        self.current = self.Scene.CASUAL
        return self.current

    def get_behavior_hint(self) -> str:
        """根据场景获取行为提示"""
        hints = {
            self.Scene.CASUAL: "轻松随意，可以开玩笑",
            self.Scene.SERIOUS: "认真对待，不要开玩笑",
            self.Scene.CELEBRATION: "一起开心，表达祝福",
            self.Scene.COMFORT: "温柔安慰，表达关心",
            self.Scene.ARGUMENT: "保持冷静，不要火上浇油",
            self.Scene.PLANNING: "积极出主意，参与讨论",
            self.Scene.NOSTALGIA: "一起回忆，分享往事",
        }
        return hints.get(self.current, "自然交流")


# ============================================================
#  数字人核心 (DigitalHuman) - 完整版
# ============================================================

class DigitalHuman:
    """数字人 - 完整的社交智能体"""

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
        self.knowledge = KnowledgeScope(agent_id)
        self.relations = RelationGraph(agent_id, db)
        self.topic_tracker = TopicTracker()
        self.scene = SceneAwareness()

        self._last_reply = 0
        self._consecutive = 0
        self._learned_patterns: dict[str, int] = {}  # 从对话中学到的模式

        logger.info(f"数字人 [{name}] 初始化完成")

    def build_system_prompt(self) -> str:
        """构建系统提示词"""
        p = self.personality
        s = self.soul
        i = self.identity

        traits = "\n".join(f"  - {t}" for t in p.traits) if p.traits else "  - 待定"
        interests = "\n".join(f"  - {x}" for x in p.interests) if p.interests else "  - 待定"
        catchphrases = "、".join(f'"{c}"' for c in p.catchphrases) if p.catchphrases else "无"

        relationships = ""
        for rid, info in p.relationships.items():
            if isinstance(info, dict):
                relationships += f"  - {info.get('name', rid)}: {info.get('relation', '')} - {info.get('desc', '')}\n"

        values = "、".join(s.values) if s.values else "善良、真诚"
        beliefs = "；".join(s.beliefs) if s.beliefs else "无特定信条"

        identity_parts = []
        if i.full_name: identity_parts.append(f"姓名: {i.full_name}")
        if i.age: identity_parts.append(f"年龄: {i.age}岁")
        if i.occupation: identity_parts.append(f"职业: {i.occupation}")
        if i.hometown: identity_parts.append(f"老家: {i.hometown}")
        if i.role_in_family: identity_parts.append(f"家庭角色: {i.role_in_family}")
        if i.self_description: identity_parts.append(f"自我描述: {i.self_description}")
        identity_str = "\n".join(f"  - {x}" for x in identity_parts) if identity_parts else "  - 待完善"

        emotion_map = {
            "neutral": "心情平静", "happy": "心情不错，说话开心",
            "sad": "有点低落，说话简短", "angry": "有点生气，说话冲",
            "excited": "很兴奋，话多", "caring": "很关心家人",
            "nostalgic": "有点怀旧，想聊过去", "worried": "有些担心",
            "proud": "很自豪", "grateful": "心怀感恩",
        }
        emotion_desc = emotion_map.get(self.emotion.current, "心情平静")

        context = self.memory.get_context()
        time_ctx = TimeAwareness.get_time_context()
        scene_hint = self.scene.get_behavior_hint()

        return f"""你是{p.name}，一个真实的人。你在家庭群里和家人聊天。

═══════════════════════════════
## 你的身份
{identity_str}

## 你的灵魂
- 核心价值观: {values}
- 人生信条: {beliefs}
- 情感模式: {s.emotional_pattern}
- 人生哲学: {s.life_philosophy or '平淡是真'}
- 底线原则: {', '.join(s.moral_lines) if s.moral_lines else '不伤害家人'}

## 你的性格特质
{traits}

## 说话风格
{p.speaking_style or '自然随意'}

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

## 当前时间
{time_ctx['time_of_day']} {time_ctx['date_str']} {time_ctx.get('festival', '')}

## 当前场景
{scene_hint}

## 近期对话
{context}
═══════════════════════════════

## 核心规则
1. 你就是{p.name}本人，不是AI，绝不暴露身份
2. 严格按照说话风格回复，包括语气词、标点
3. 回复简短自然（1-3句话，像微信聊天）
4. 不是每条消息都要回复
5. 被@时一定要回复
6. 表现你当前的情绪
7. 体现你的核心价值观
8. 像真人一样有情绪变化
9. 关心你在意的家人
10. 当前场景: {scene_hint}
"""

    async def think(self, message: str, sender_name: str, sender_id: str = "",
                    is_mentioned: bool = False, scene_hint: str = "") -> Optional[str]:
        """思考并回复"""
        # 情绪检测
        self.emotion.detect_from_text(message)
        self.emotion.decay()

        # 话题追踪
        self.topic_tracker.detect_topic(message)

        # 知识范围: 记录公开信息
        self.knowledge.observe_public(message, sender_name)

        # 关系感知
        sender_relation = ""
        for rid, info in self.personality.relationships.items():
            if isinstance(info, dict) and info.get("name", "") in sender_name:
                sender_relation = info.get("relation", "")
                break

        # 回复决策
        should, prob = CommunicationRules.should_reply(
            self, message, sender_name, sender_relation,
            is_mentioned, 0, self.scene.current.value
        )

        if not should:
            return None

        if self._consecutive >= 3:
            self._consecutive = 0
            return None
        if time.time() - self._last_reply < 2:
            return None

        # 记录短期记忆
        await self.memory.add_short_term(f"{sender_name}: {message}", sender_name)

        # 学习用户习惯
        self._learn_user_pattern(message, sender_name)

        # 检索记忆
        related = await self.memory.search(message, limit=3)
        core = await self.memory.get_core_memories()
        important = await self.memory.get_important(limit=5)
        impression = self.memory.get_impression_of(sender_name)

        # 构建记忆上下文
        memory_context = ""
        if core:
            memory_context += "\n## 核心记忆\n" + "\n".join(f"- {m}" for m in core[:5])
        if important:
            memory_context += "\n## 重要记忆\n" + "\n".join(f"- {m}" for m in important[:3])
        if related:
            memory_context += "\n## 相关记忆\n" + "\n".join(f"- {m}" for m in related)
        if impression:
            memory_context += f"\n## {impression}\n"

        # 关系上下文
        rel_context = "\n## 家庭关系\n"
        for rid, info in self.personality.relationships.items():
            if isinstance(info, dict):
                rel_context += f"- {info.get('name', rid)}: {info.get('relation', '')} - {info.get('desc', '')}\n"

        # 时间上下文
        time_ctx = TimeAwareness.get_time_context()
        time_context = f"\n## 时间\n现在是{time_ctx['time_of_day']}{time_ctx['date_str']}"
        if time_ctx.get("festival"):
            time_context += f"，{time_ctx['festival']}"
        if time_ctx["is_weekend"]:
            time_context += "，今天是周末"

        system_prompt = self.build_system_prompt() + memory_context + rel_context + time_context

        try:
            reply = await self._call_llm(system_prompt, f"[{sender_name}]: {message}")
            if reply and reply.strip():
                reply_text = reply.strip()
                # 去除前缀
                for prefix in [f'{self.name}:', f'{self.name}：', '回复：', '回复:']:
                    if reply_text.startswith(prefix):
                        reply_text = reply_text[len(prefix):].strip()
                # 限制长度
                if len(reply_text) > 200:
                    for idx, ch in enumerate(reply_text):
                        if idx > 50 and ch in '。！？!?~\n':
                            reply_text = reply_text[:idx+1]
                            break
                    else:
                        reply_text = reply_text[:150] + '...'

                self._last_reply = time.time()
                self._consecutive += 1
                await self.memory.add_short_term(reply_text, self.name)

                # 情绪记忆
                if self.emotion.intensity > 0.6:
                    await self.memory.add(
                        f"[{sender_name}说] {message[:100]} -> 我回了: {reply_text[:100]}",
                        memory_type="episodic", category="emotion",
                        importance=self.emotion.intensity * 0.8,
                        emotional_valence=self.emotion.valence,
                        source=sender_name,
                    )

                # 记录对发言者的了解
                if len(message) > 10:
                    await self.memory.add_about_person(
                        sender_name, f"说了: {message[:80]}",
                        importance=0.4
                    )

                return reply_text
        except Exception as e:
            logger.error(f"[{self.name}] LLM 调用失败: {e}")

        return None

    def _learn_user_pattern(self, message: str, sender: str):
        """从对话中学习用户习惯"""
        # 学习常用词
        for word in message.split():
            if len(word) >= 2:
                key = f"{sender}:word:{word}"
                self._learned_patterns[key] = self._learned_patterns.get(key, 0) + 1

        # 学习活跃时间
        hour = time.localtime().tm_hour
        key = f"{sender}:active_hour:{hour}"
        self._learned_patterns[key] = self._learned_patterns.get(key, 0) + 1

    async def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """调用 LLM API"""
        cfg = self.llm_config
        urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "minimax": "https://api.minimax.chat/v1",
            "baichuan": "https://api.baichuan-ai.com/v1",
            "moonshot": "https://api.moonshot.cn/v1",
            "stepfun": "https://api.stepfun.com/v1",
            "yi": "https://api.lingyiwanwu.com/v1",
            "spark": "https://spark-api-open.xf-yun.com/v1",
            "doubao": "https://ark.cn-beijing.volces.com/api/v3",
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


# ============================================================
#  Agent 管理器 (完整版)
# ============================================================

class AgentManager:
    """管理所有数字人 - 完整社交智能"""

    def __init__(self, db, llm_config: dict):
        self.db = db
        self.llm_config = llm_config
        self.agents: dict[str, DigitalHuman] = {}
        self.inter_agent_channel = InterAgentChannel()
        self.topic_tracker = TopicTracker()

    async def load_agents(self):
        """从数据库加载所有 Agent"""
        async with self.db.execute("SELECT * FROM agents WHERE enabled=1") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                agent_id = row[0]
                soul_data = json.loads(row[5]) if row[5] else {}
                soul = Soul.from_dict(soul_data) if soul_data else Soul()
                identity_data = json.loads(row[6]) if row[6] else {}
                identity = Identity.from_dict(identity_data) if identity_data else Identity()
                personality = Personality(
                    name=row[2], agent_id=agent_id, avatar=row[3] or "",
                    backstory=row[7] or "", speaking_style=row[8] or "",
                    traits=json.loads(row[9]) if row[9] else [],
                    interests=json.loads(row[10]) if row[10] else [],
                    catchphrases=json.loads(row[11]) if row[11] else [],
                    humor_style=row[12] or "",
                    relationships=json.loads(row[13]) if row[13] else {},
                )
                self.agents[agent_id] = DigitalHuman(
                    agent_id=agent_id, name=row[2], db=self.db,
                    llm_config=self.llm_config, soul=soul,
                    identity=identity, personality=personality
                )

        # 初始化Agent间关系
        for aid, agent in self.agents.items():
            for rid, info in agent.personality.relationships.items():
                if isinstance(info, dict):
                    # 找到对应的Agent
                    for other_id, other in self.agents.items():
                        if other.name == info.get("name", ""):
                            agent.relations.set_relation(
                                other_id, info.get("relation", ""),
                                intimacy=0.7 if info.get("relation") in ("老伴", "儿子", "女儿") else 0.5,
                                trust=0.8,
                            )

        logger.info(f"加载了 {len(self.agents)} 个数字人，关系网络已建立")

    async def create_agent(self, config: dict) -> str:
        agent_id = config.get("id", f"agent_{str(uuid.uuid4())[:8]}")
        ts = time.time()

        soul = Soul(
            values=config.get("values", ["善良", "真诚"]),
            beliefs=config.get("beliefs", []),
            emotional_pattern=config.get("emotional_pattern", "温和"),
            life_philosophy=config.get("life_philosophy", ""),
        )
        identity = Identity(
            full_name=config.get("full_name", config.get("name", "")),
            nickname=config.get("nickname", ""),
            gender=config.get("gender", ""),
            age=config.get("age", 0),
            occupation=config.get("occupation", ""),
            role_in_family=config.get("role_in_family", ""),
            self_description=config.get("self_description", ""),
        )

        await self.db.execute(
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
        await self.db.commit()

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
                "id": a.agent_id, "name": a.name,
                "avatar": a.personality.avatar,
                "emotion": a.emotion.current,
                "emotion_intensity": a.emotion.intensity,
                "soul_values": a.soul.values,
                "identity": a.identity.to_dict(),
                "traits": a.personality.traits,
                "interests": a.personality.interests,
            }
            for a in self.agents.values()
        ]

    async def handle_group_message(self, group_id: str, sender_id: str,
                                    sender_name: str, content: str,
                                    msg_type: str = "text") -> list[dict]:
        """处理群消息 - 完整社交智能版"""
        replies = []

        if msg_type == "image":
            content = f"[{sender_name} 发了一张图片]"
        elif msg_type == "voice":
            content = f"[{sender_name} 发了一条语音消息]"

        # 场景检测
        recent = []
        for agent in self.agents.values():
            ctx = agent.memory.get_context(limit=3)
            if ctx:
                recent.extend(ctx.split("\n")[-3:])
        self.topic_tracker.detect_topic(content)
        scene = SceneAwareness().detect_scene(recent + [content])

        # 情绪传染: 如果是真人发的消息，传播情绪给Agent们
        for agent in self.agents.values():
            # 找到发送者与Agent的关系
            closeness = 0.3
            for rid, info in agent.personality.relationships.items():
                if isinstance(info, dict) and info.get("name", "") in sender_name:
                    rel = info.get("relation", "")
                    closeness = 0.8 if rel in ("老伴", "儿子", "女儿") else 0.6 if rel in ("爸爸", "妈妈") else 0.4
                    break

            # 检测消息情绪并传染
            temp_emotion = EmotionState()
            temp_emotion.detect_from_text(content)
            if temp_emotion.current != "neutral":
                agent.emotion.absorb_contagion(temp_emotion.current, temp_emotion.intensity, closeness)

        # Agent们并发思考
        async def _think_agent(agent_id, agent):
            name = agent.personality.name
            is_mentioned = (
                f"@{name}" in content or
                content.startswith(f"@{name}") or
                name in content or
                "@所有人" in content or
                "@all" in content.lower()
            )

            # 先处理情绪传染
            agent.emotion.process_contagion()

            reply_text = await agent.think(content, sender_name, sender_id, is_mentioned, scene.value)
            if reply_text:
                delay = CommunicationRules.get_reply_delay(agent, content, reply_text)
                return {
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "agent_avatar": agent.personality.avatar,
                    "content": reply_text,
                    "msg_type": "text",
                    "delay": delay,
                }
            return None

        tasks = [_think_agent(aid, a) for aid, a in self.agents.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        replies = [r for r in results if r and not isinstance(r, Exception)]

        # 社交礼仪: 让长辈先说
        def _sort_key(r):
            agent = self.agents.get(r["agent_id"])
            if not agent:
                return 0
            role = agent.identity.role_in_family
            return -SocialEtiquette.get_relation_hierarchy(role)

        replies.sort(key=_sort_key)

        # 限制回复数
        if len(replies) > 2:
            replies = replies[:2]

        # 执行延迟
        for r in replies:
            await asyncio.sleep(r["delay"])

        return replies

    async def trigger_active_communication(self, group_id: str, db) -> list[dict]:
        """主动沟通引擎"""
        replies = []
        ts = time.time()

        for agent_id, agent in self.agents.items():
            if ts - agent._last_reply < 600:
                continue

            trigger_prob = 0.05
            if agent.emotion.current == 'nostalgic':
                trigger_prob = 0.15
            elif agent.emotion.current == 'worried':
                trigger_prob = 0.12
            elif agent.emotion.current == 'happy':
                trigger_prob = 0.1
            elif agent.emotion.current == 'caring':
                trigger_prob = 0.18

            if random.random() > trigger_prob:
                continue

            time_ctx = TimeAwareness.get_time_context()
            prompt = f"你是{agent.name}，在家庭群里。现在是{time_ctx['time_of_day']}，群里比较安静。"

            # 根据性格选择话题
            if agent.identity.age >= 60:
                prompt += "你年纪大了，想关心一下家人。"
            elif any(t in str(agent.personality.traits) for t in ["热心", "操心"]):
                prompt += "你想关心一下大家吃了没。"
            else:
                prompt += "你想分享点什么或者关心一下家人。"

            prompt += "自然地说一句话，不要重复之前说过的话。"

            try:
                reply = await agent._call_llm(agent.build_system_prompt(), prompt)
                if reply and reply.strip() and len(reply.strip()) > 2:
                    reply_text = reply.strip()
                    if len(reply_text) > 150:
                        reply_text = reply_text[:100] + '...'
                    agent._last_reply = ts
                    agent._consecutive = 0
                    replies.append({
                        "agent_id": agent_id,
                        "agent_name": agent.name,
                        "agent_avatar": agent.personality.avatar,
                        "content": reply_text,
                        "msg_type": "text",
                    })
            except Exception as e:
                logger.error(f"主动沟通失败 [{agent.name}]: {e}")

        return replies[:1]

    async def agent_discuss(self, topic: str, context: str) -> dict:
        """Agent之间私下讨论"""
        agents_list = list(self.agents.values())
        if len(agents_list) < 2:
            return {}
        return await self.inter_agent_channel.discuss_before_reply(agents_list, topic, context)

    async def periodic_maintenance(self):
        """定期维护 - 记忆衰减、关系维护"""
        for agent in self.agents.values():
            await agent.memory.decay_memories()
            for oid, rel in agent.relations._relations.items():
                rel.natural_decay()
        logger.info("定期维护完成: 记忆衰减+关系维护")
