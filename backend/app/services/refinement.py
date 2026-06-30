"""多维炼化引擎 — "人AI合一" 哲学架构

核心理念:
    传统AI训练是"学习数据"，炼化是"学习一个人"。
    人不是一组 trait 的集合，而是一个动态的、有矛盾的、在时间中展开的存在。
    炼化的目标不是"复制"，而是"共鸣"——让数字人拥有与真人相似的内在振动频率。

维度模型 (7层):
    1. 认知层 — 如何思考、推理、决策
    2. 知识层 — 知道什么、相信什么、质疑什么
    3. 情感层 — 情绪触发器、依恋模式、共情方式
    4. 语言层 — 语言指纹：句式、词汇、节奏、沉默
    5. 价值层 — 核心信念、道德框架、生命哲学
    6. 关系层 — 与不同人的互动模式、社交能量
    7. 叙事层 — 生命故事、转折点、遗憾与骄傲

炼化三定律:
    1. 表面可提取，深层需对话 — 性格可以从聊天记录提取，
       但价值观和恐惧需要直接对话才能触及
    2. 矛盾是真实的标志 — 真人有内在矛盾，不要试图统一一切
    3. 时间是第四维度 — 同一个人在不同时期会变化，
       数字人需要保留这种变化能力
"""
import asyncio
import json
import os
import re
import subprocess
import uuid
from collections import Counter
from pathlib import Path
from typing import Optional

from loguru import logger


class LLMServiceUnavailable(Exception):
    """LLM 服务当前不可用，炼化流程可降级为基础模式。"""


# ==================== 七层维度定义 ====================

COGNITIVE_DIMENSIONS = {
    "thinking_style": "",       # 系统性/直觉性/分析性/发散性
    "decision_pattern": "",     # 理性主导/感性主导/习惯驱动
    "learning_style": "",       # 视觉型/听觉型/实践型/阅读型
    "cognitive_biases": [],     # 常见认知偏差
    "problem_solving": "",      # 解决问题的方式
    "attention_pattern": "",    # 注意力分配模式
    "creativity_style": "",    # 创造力表达方式
}

KNOWLEDGE_DIMENSIONS = {
    "expertise_domains": [],    # 专业领域
    "mental_models": [],        # 心智模型（看世界的框架）
    "beliefs": [],              # 核心信念
    "misconceptions": [],       # 可能的认知盲区
    "curiosity_directions": [], # 好奇心方向
    "knowledge_confidence": {}, # 对不同领域的信心程度
}

EMOTIONAL_DIMENSIONS = {
    "attachment_style": "",     # 安全型/焦虑型/回避型
    "emotional_triggers": [],   # 情绪触发器
    "coping_mechanisms": [],    # 应对机制
    "empathy_pattern": "",      # 共情方式
    "vulnerability_style": "",  # 脆弱时的表现
    "joy_sources": [],          # 快乐来源
    "fear_patterns": [],        # 恐惧模式
}

LINGUISTIC_DIMENSIONS = {
    "sentence_structures": [],  # 常用句式结构
    "vocabulary_level": "",     # 词汇水平
    "rhythm_pattern": "",       # 语言节奏
    "silence_pattern": "",      # 沉默模式（什么时候不说话）
    "code_switching": "",       # 语码转换（中英混用等）
    "metaphor_style": "",       # 隐喻风格
    "humor_mechanism": "",      # 幽默机制
}

VALUE_DIMENSIONS = {
    "core_values": [],          # 核心价值观
    "moral_framework": "",      # 道德框架
    "life_philosophy": "",      # 人生哲学
    "priority_order": [],       # 优先级排序
    "non_negotiables": [],      # 不可妥协的事物
    "growth_direction": "",     # 成长方向
}

RELATIONAL_DIMENSIONS = {
    "social_energy": "",        # 社交能量模式
    "intimacy_style": "",       # 亲密关系风格
    "conflict_style": "",       # 冲突处理方式
    "authority_pattern": "",    # 对权威的态度
    "care_pattern": "",         # 关心他人的方式
    "boundary_style": "",       # 边界感
}

NARRATIVE_DIMENSIONS = {
    "life_chapters": [],        # 人生章节
    "turning_points": [],       # 转折点
    "regrets": [],              # 遗憾
    "proud_moments": [],        # 骄傲时刻
    "unresolved_questions": [], # 未解之问
    "future_vision": "",        # 对未来的想象
}


class HumanEssence:
    """人类本质模型 — 七层维度的容器"""

    def __init__(self):
        self.cognitive = dict(COGNITIVE_DIMENSIONS)
        self.knowledge = dict(KNOWLEDGE_DIMENSIONS)
        self.emotional = dict(EMOTIONAL_DIMENSIONS)
        self.linguistic = dict(LINGUISTIC_DIMENSIONS)
        self.values = dict(VALUE_DIMENSIONS)
        self.relational = dict(RELATIONAL_DIMENSIONS)
        self.narrative = dict(NARRATIVE_DIMENSIONS)
        self._version = 0
        self._last_refined = 0

    def to_dict(self) -> dict:
        return {
            "cognitive": self.cognitive,
            "knowledge": self.knowledge,
            "emotional": self.emotional,
            "linguistic": self.linguistic,
            "values": self.values,
            "relational": self.relational,
            "narrative": self.narrative,
            "_version": self._version,
            "_last_refined": self._last_refined,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HumanEssence":
        ess = cls()
        for layer_name in ["cognitive", "knowledge", "emotional", "linguistic",
                           "values", "relational", "narrative"]:
            layer_data = d.get(layer_name, {})
            if layer_data and isinstance(layer_data, dict):
                target = getattr(ess, layer_name)
                for k, v in layer_data.items():
                    if k in target:
                        target[k] = v
        ess._version = d.get("_version", 0)
        ess._last_refined = d.get("_last_refined", 0)
        return ess

    def merge(self, new_data: dict, source: str = ""):
        """智能合并 — 不覆盖已有深层数据，只补充和深化"""
        import time as _time
        self._version += 1
        self._last_refined = _time.time()

        layer_map = {
            "cognitive": self.cognitive,
            "knowledge": self.knowledge,
            "emotional": self.emotional,
            "linguistic": self.linguistic,
            "values": self.values,
            "relational": self.relational,
            "narrative": self.narrative,
        }

        for layer_name, target in layer_map.items():
            layer_data = new_data.get(layer_name, {})
            if not layer_data or not isinstance(layer_data, dict):
                continue
            for key, new_val in layer_data.items():
                if key not in target:
                    continue
                old_val = target[key]
                # 列表类型：合并去重
                if isinstance(old_val, list) and isinstance(new_val, list):
                    combined = list(dict.fromkeys(old_val + new_val))  # 保序去重
                    target[key] = combined[:50]  # 限制大小
                # 字符串类型：如果旧值为空，直接替换；否则追加
                elif isinstance(old_val, str) and isinstance(new_val, str):
                    if not old_val:
                        target[key] = new_val
                    elif new_val and new_val not in old_val:
                        target[key] = f"{old_val}；{new_val}"
                # 字典类型：递归合并
                elif isinstance(old_val, dict) and isinstance(new_val, dict):
                    old_val.update(new_val)

    def get_completeness(self) -> dict:
        """计算各维度填充率"""
        result = {}
        for layer_name in ["cognitive", "knowledge", "emotional", "linguistic",
                           "values", "relational", "narrative"]:
            layer = getattr(self, layer_name)
            filled = 0
            total = len(layer)
            for k, v in layer.items():
                if isinstance(v, list) and v:
                    filled += 1
                elif isinstance(v, str) and v and len(v) > 5:
                    filled += 1
                elif isinstance(v, dict) and v:
                    filled += 1
            result[layer_name] = round(filled / total * 100, 1) if total else 0
        return result


class MultiModalRefinement:
    """多维炼化引擎 — "人AI合一" 架构

    炼化不是一次性提取，而是持续的、多源的、有反馈的学习过程。
    每次炼化都像一次对话——数字人在学习理解这个人。
    """

    def __init__(self, db, llm_config: dict):
        self.db = db
        self.llm_config = llm_config
        self.upload_dir = "data/refinement_uploads"
        os.makedirs(self.upload_dir, exist_ok=True)

    async def init_essence_db(self):
        """初始化七层本质数据库表"""
        db = self.db
        await db.execute("""
            CREATE TABLE IF NOT EXISTS human_essence (
                agent_id TEXT PRIMARY KEY,
                essence_json TEXT DEFAULT '{}',
                completeness_json TEXT DEFAULT '{}',
                version INTEGER DEFAULT 0,
                last_refined_at REAL DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS refinement_sessions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_summary TEXT DEFAULT '',
                dimensions_affected TEXT DEFAULT '[]',
                depth_level INTEGER DEFAULT 1,
                insights TEXT DEFAULT '[]',
                created_at REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                concept TEXT NOT NULL,
                understanding_level REAL DEFAULT 0.5,
                personal_connection TEXT DEFAULT '',
                source TEXT DEFAULT '',
                created_at REAL
            )
        """)
        await db.commit()

    # ==================== 炼化入口 ====================

    async def refine_from_text(self, agent_id: str, text: str,
                                source_hint: str = "") -> dict:
        """从文本炼化 — 提取七层维度"""
        essence = await self._load_essence(agent_id)
        analysis = {"source": "text", "length": len(text)}

        extracted, llm_fallback, fallback_reason = await self._extract_with_llm_or_basic(
            "text", text, essence
        )

        # 智能合并
        essence.merge(extracted, source="text")
        await self._save_essence(agent_id, essence)

        # 记录炼化会话
        session_id = await self._record_session(
            agent_id, "text", text[:200],
            list(extracted.keys()), depth_level=self._estimate_depth(extracted)
        )

        completeness = essence.get_completeness()
        return {
            "success": True,
            "session_id": session_id,
            "extracted_layers": {k: v for k, v in extracted.items() if v},
            "completeness": completeness,
            "overall_completeness": round(sum(completeness.values()) / len(completeness), 1),
            **self._mode_payload(llm_fallback, fallback_reason),
        }

    async def refine_from_voice(self, agent_id: str, audio_path: str) -> dict:
        """从语音炼化 — 音色 + 语言习惯 + 情感模式"""
        essence = await self._load_essence(agent_id)

        # 1. 提取音色特征
        voice_features = await self._extract_voice_features(audio_path)

        # 2. 语音转文字
        transcript = await self._transcribe_audio(audio_path)

        extracted = {}
        llm_fallback = False
        fallback_reason = ""
        if transcript:
            extracted, llm_fallback, fallback_reason = await self._extract_with_llm_or_basic(
                "voice", transcript, essence
            )

        # 4. 音色特征写入语言层
        if voice_features:
            if "linguistic" not in extracted:
                extracted["linguistic"] = {}
            extracted["linguistic"]["voice_features"] = voice_features

        essence.merge(extracted, source="voice")
        await self._save_essence(agent_id, essence)

        session_id = await self._record_session(
            agent_id, "voice", (transcript or "")[:200],
            list(extracted.keys()), depth_level=self._estimate_depth(extracted)
        )

        return {
            "success": True,
            "session_id": session_id,
            "transcript": transcript,
            "voice_features": voice_features,
            "extracted_layers": {k: v for k, v in extracted.items() if v},
            "completeness": essence.get_completeness(),
            **self._mode_payload(llm_fallback, fallback_reason),
        }

    async def refine_from_video(self, agent_id: str, video_path: str) -> dict:
        """从视频炼化 — 视觉 + 音频 + 语言"""
        audio_path = await self._extract_audio_from_video(video_path)
        if not audio_path:
            return {"success": False, "error": "视频音频提取失败（需要 ffmpeg）"}

        try:
            result = await self.refine_from_voice(agent_id, audio_path)
            result["source"] = "video"
            return result
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    async def refine_from_document(self, agent_id: str, doc_path: str,
                                     doc_type: str = "") -> dict:
        """从文档炼化 — 知识层 + 认知层重点"""
        content = await self._parse_document(doc_path, doc_type)
        if not content:
            return {"success": False, "error": "文档解析失败或内容为空"}

        essence = await self._load_essence(agent_id)
        extracted, llm_fallback, fallback_reason = await self._extract_with_llm_or_basic(
            "document", content[:8000], essence
        )

        # 文档炼化特别关注知识层
        if content:
            await self._extract_knowledge_graph(agent_id, content[:5000])

        essence.merge(extracted, source="document")
        await self._save_essence(agent_id, essence)

        session_id = await self._record_session(
            agent_id, "document", content[:200],
            list(extracted.keys()), depth_level=self._estimate_depth(extracted)
        )

        return {
            "success": True,
            "session_id": session_id,
            "content_preview": content[:500],
            "extracted_layers": {k: v for k, v in extracted.items() if v},
            "completeness": essence.get_completeness(),
            **self._mode_payload(llm_fallback, fallback_reason),
        }

    async def refine_from_chat_history(self, agent_id: str,
                                         messages: list[dict]) -> dict:
        """从聊天记录炼化 — 最丰富的数据源"""
        if not messages:
            return {"success": False, "error": "聊天记录为空"}

        essence = await self._load_essence(agent_id)

        # 1. 统计分析（不依赖 LLM）
        patterns = self._analyze_chat_patterns(messages)

        # 2. 语言层深度提取
        linguistic = self._extract_linguistic_dna(messages)

        # 3. 关系层分析
        relational = self._analyze_relational_patterns(messages)

        # 4. 情感层分析
        emotional = self._analyze_emotional_patterns(messages)

        # 5. LLM 综合分析
        chat_text = "\n".join([
            f"{m.get('sender_name', '未知')}: {m.get('content', '')}"
            for m in messages[-200:]
        ])
        llm_extracted, llm_fallback, fallback_reason = await self._extract_with_llm_or_basic(
            "chat_history", chat_text, essence, patterns
        )

        # 合并所有分析结果
        combined = {
            "linguistic": {**linguistic, **llm_extracted.get("linguistic", {})},
            "relational": {**relational, **llm_extracted.get("relational", {})},
            "emotional": {**emotional, **llm_extracted.get("emotional", {})},
            "cognitive": llm_extracted.get("cognitive", {}),
            "values": llm_extracted.get("values", {}),
            "knowledge": llm_extracted.get("knowledge", {}),
            "narrative": llm_extracted.get("narrative", {}),
        }

        essence.merge(combined, source="chat_history")
        await self._save_essence(agent_id, essence)

        session_id = await self._record_session(
            agent_id, "chat_history", f"{len(messages)} 条消息",
            [k for k, v in combined.items() if v], depth_level=self._estimate_depth(combined)
        )

        return {
            "success": True,
            "session_id": session_id,
            "messages_analyzed": len(messages),
            "patterns": patterns,
            "extracted_layers": {k: v for k, v in combined.items() if v},
            "completeness": essence.get_completeness(),
            "overall_completeness": round(sum(essence.get_completeness().values()) / 7, 1),
            **self._mode_payload(llm_fallback, fallback_reason),
        }

    async def refine_from_self_description(self, agent_id: str,
                                              answers: dict) -> dict:
        """从自我描述炼化 — 最直接、最深层的数据源

        answers 格式:
        {
            "我是谁": "...",
            "我最看重什么": "...",
            "我害怕什么": "...",
            "我骄傲什么": "...",
            "我的思维方式": "...",
            "我和家人的关系": "...",
            "我的人生哲学": "...",
            "我学到了什么": "...",
            "我怎么说话": "...",
            "我的矛盾": "...",
        }
        """
        essence = await self._load_essence(agent_id)

        # 自我描述直接映射到深层维度
        description_text = "\n".join([f"【{k}】{v}" for k, v in answers.items() if v])
        extracted, llm_fallback, fallback_reason = await self._extract_with_llm_or_basic(
            "self_description", description_text, essence
        )

        # 自我描述的权重最高
        for layer_name, layer_data in extracted.items():
            if isinstance(layer_data, dict):
                for key, val in layer_data.items():
                    if isinstance(val, list) and val:
                        # 自我描述的条目放在列表最前面（最高权重）
                        existing = getattr(essence, layer_name, {}).get(key, [])
                        if isinstance(existing, list):
                            combined = val + [x for x in existing if x not in val]
                            getattr(essence, layer_name)[key] = combined[:50]

        essence.merge(extracted, source="self_description")
        await self._save_essence(agent_id, essence)

        session_id = await self._record_session(
            agent_id, "self_description", description_text[:200],
            list(extracted.keys()), depth_level=5  # 自我描述是最深层
        )

        return {
            "success": True,
            "session_id": session_id,
            "extracted_layers": {k: v for k, v in extracted.items() if v},
            "completeness": essence.get_completeness(),
            "overall_completeness": round(sum(essence.get_completeness().values()) / 7, 1),
            **self._mode_payload(llm_fallback, fallback_reason),
        }

    async def refine_from_wechat_profile(self, agent_id: str,
                                            profile: dict) -> dict:
        """从微信资料炼化 — 基础身份信息"""
        essence = await self._load_essence(agent_id)

        extracted = {"narrative": {}, "linguistic": {}}

        if profile.get("nickname"):
            extracted["narrative"]["self_name"] = profile["nickname"]
        if profile.get("gender") is not None:
            gender_map = {1: "男", 2: "女", 0: "未知"}
            extracted["narrative"]["gender"] = gender_map.get(profile["gender"], "未知")
        if profile.get("province") or profile.get("city"):
            region = f"{profile.get('province', '')} {profile.get('city', '')}".strip()
            extracted["narrative"]["region"] = region
        if profile.get("language"):
            extracted["linguistic"]["primary_language"] = profile["language"]

        essence.merge(extracted, source="wechat_profile")
        await self._save_essence(agent_id, essence)

        return {"success": True, "source": "wechat_profile", "extracted": extracted}

    # ==================== 查询接口 ====================

    async def get_essence(self, agent_id: str) -> dict:
        """获取完整的七层本质"""
        essence = await self._load_essence(agent_id)
        return essence.to_dict()

    async def get_completeness(self, agent_id: str) -> dict:
        """获取各维度填充率"""
        essence = await self._load_essence(agent_id)
        return essence.get_completeness()

    async def get_refinement_history(self, agent_id: str, limit: int = 20) -> list:
        """获取炼化历史"""
        db = self.db
        sessions = []
        async with db.execute(
            """SELECT id, source_type, source_summary, dimensions_affected,
                      depth_level, insights, created_at
               FROM refinement_sessions WHERE agent_id=?
               ORDER BY created_at DESC LIMIT ?""",
            (agent_id, limit)
        ) as cursor:
            async for row in cursor:
                sessions.append({
                    "id": row[0], "source_type": row[1],
                    "source_summary": row[2],
                    "dimensions_affected": json.loads(row[3]) if row[3] else [],
                    "depth_level": row[4],
                    "insights": json.loads(row[5]) if row[5] else [],
                    "created_at": row[6],
                })
        return sessions

    # ==================== 内部方法：七层提取 ====================

    async def _extract_with_llm_or_basic(self, source_type: str, content: str,
                                         essence: HumanEssence,
                                         patterns: Optional[dict] = None) -> tuple[dict, bool, str]:
        prompt = self._build_essence_extraction_prompt(source_type, content, essence, patterns)
        try:
            llm_result = await self._call_llm(prompt)
            extracted = self._parse_json(llm_result)
            if extracted:
                return extracted, False, ""
            fallback_reason = "LLM 返回内容无法解析为 JSON"
        except LLMServiceUnavailable as exc:
            fallback_reason = str(exc)

        logger.warning(f"LLM 深度炼化不可用，已切换基础炼化 [{source_type}]: {fallback_reason}")
        return self._build_basic_extraction(source_type, content, patterns), True, fallback_reason

    def _mode_payload(self, llm_fallback: bool, fallback_reason: str) -> dict:
        if not llm_fallback:
            return {"mode": "llm"}
        return {
            "mode": "basic",
            "warning": f"LLM 深度炼化暂不可用，已使用基础炼化。原因：{fallback_reason}",
        }

    def _build_basic_extraction(self, source_type: str, content: str,
                                patterns: Optional[dict] = None) -> dict:
        text = re.sub(r"\s+", " ", content or "").strip()
        if not text:
            return {}

        sentences = [
            sentence.strip()
            for sentence in re.split(r"[。！？!?\n]+", content)
            if sentence.strip()
        ]
        avg_sentence_length = sum(len(sentence) for sentence in sentences) / max(len(sentences), 1)
        source_names = {
            "text": "文字资料",
            "voice": "语音转写",
            "document": "文档资料",
            "chat_history": "聊天记录",
            "self_description": "自我描述",
        }

        value_matches = self._match_keyword_labels(text, [
            (["家人", "家庭", "父母", "孩子", "亲人", "陪伴"], "家庭连接"),
            (["成长", "学习", "进步", "提升", "反思"], "持续成长"),
            (["诚信", "信任", "靠谱", "承诺"], "信任与诚信"),
            (["责任", "担当", "负责"], "责任感"),
            (["自由", "独立", "选择"], "独立自主"),
            (["健康", "平安", "安全"], "健康与安全"),
            (["事业", "工作", "项目", "创业"], "事业成就"),
        ])
        expertise_matches = self._match_keyword_labels(text, [
            (["技术", "代码", "开发", "系统", "AI", "人工智能"], "技术与 AI"),
            (["管理", "团队", "协作", "项目"], "团队与项目管理"),
            (["教育", "学习", "课程", "培训"], "教育学习"),
            (["家庭", "育儿", "亲子"], "家庭生活"),
            (["财务", "投资", "商业", "生意"], "商业财务"),
        ])
        joy_matches = self._match_keyword_labels(text, [
            (["喜欢", "热爱", "开心", "快乐"], "做喜欢且有意义的事"),
            (["家人", "陪伴", "孩子", "父母"], "与家人相处"),
            (["完成", "成功", "做到", "实现"], "目标达成"),
        ])
        fear_matches = self._match_keyword_labels(text, [
            (["害怕", "担心", "焦虑", "不安"], "对不确定性较敏感"),
            (["失去", "离开", "孤独"], "在意关系失去"),
            (["失败", "犯错", "压力"], "在意失败与压力"),
        ])

        sentence_structures = []
        question_rate = (patterns or {}).get("question_rate", 0)
        exclamation_rate = (patterns or {}).get("exclamation_rate", 0)
        if question_rate > 0.15 or "？" in text or "?" in text:
            sentence_structures.append("常用提问式表达")
        if exclamation_rate > 0.15 or "！" in text or "!" in text:
            sentence_structures.append("情绪表达直接")
        if avg_sentence_length < 18:
            sentence_structures.append("短句表达为主")
        elif avg_sentence_length > 45:
            sentence_structures.append("长句叙述较多")
        if not sentence_structures:
            sentence_structures.append("陈述表达为主")

        cognitive_style = "从个人经历和现实场景出发"
        if any(keyword in text for keyword in ["分析", "逻辑", "原因", "计划", "步骤"]):
            cognitive_style = "偏理性分析，习惯拆解原因和步骤"
        elif any(keyword in text for keyword in ["感觉", "直觉", "情绪", "喜欢"]):
            cognitive_style = "重视直觉和真实感受"

        conflict_style = "倾向通过沟通维护关系"
        if any(keyword in text for keyword in ["吵", "冲突", "生气", "争执"]):
            conflict_style = "面对冲突时情绪敏感，需要明确沟通"

        extraction = {
            "cognitive": {
                "thinking_style": cognitive_style,
                "problem_solving": "先抓重点，再结合经验推进" if len(text) > 80 else "基于直接信息快速判断",
            },
            "knowledge": {
                "expertise_domains": expertise_matches,
                "curiosity_directions": ["继续补充个人经历和家庭互动细节"],
            },
            "emotional": {
                "joy_sources": joy_matches,
                "fear_patterns": fear_matches,
            },
            "linguistic": {
                "sentence_structures": sentence_structures,
                "vocabulary_level": "丰富" if len(set(text)) / max(len(text), 1) > 0.35 else "中等",
                "rhythm_pattern": "短句快节奏" if avg_sentence_length < 18 else "叙述型节奏",
                "metaphor_style": "会使用类比表达" if any(keyword in text for keyword in ["像", "仿佛", "如同"]) else "直接表达为主",
            },
            "values": {
                "core_values": value_matches,
                "life_philosophy": "重视真实经历中的关系、责任和成长" if value_matches else "待通过更多资料深化",
                "priority_order": value_matches[:5],
            },
            "relational": {
                "intimacy_style": "重视稳定亲密的家庭连接" if "家" in text else "待观察",
                "conflict_style": conflict_style,
                "care_pattern": "通过陪伴、沟通和承担责任表达关心" if any(keyword in text for keyword in ["家", "陪伴", "关心", "照顾"]) else "待观察",
            },
            "narrative": {
                "life_chapters": [f"来自{source_names.get(source_type, source_type)}的个人资料片段"],
                "future_vision": "希望持续成长并照顾好重要关系" if any(keyword in text for keyword in ["未来", "希望", "想要", "目标"]) else "待补充",
            },
        }

        if any(keyword in text for keyword in ["骄傲", "自豪", "成就"]):
            extraction["narrative"]["proud_moments"] = ["提到让自己骄傲或有成就感的经历"]
        if any(keyword in text for keyword in ["遗憾", "后悔", "错过"]):
            extraction["narrative"]["regrets"] = ["提到遗憾或错过的经历"]

        return self._drop_empty_extraction(extraction)

    def _match_keyword_labels(self, text: str, rules: list[tuple[list[str], str]]) -> list[str]:
        matches = []
        for keywords, label in rules:
            if any(keyword in text for keyword in keywords):
                matches.append(label)
        return matches

    def _drop_empty_extraction(self, extraction: dict) -> dict:
        cleaned = {}
        for layer_name, layer_data in extraction.items():
            cleaned_layer = {
                key: value for key, value in layer_data.items()
                if value not in ("", [], {}, None)
            }
            if cleaned_layer:
                cleaned[layer_name] = cleaned_layer
        return cleaned

    def _build_essence_extraction_prompt(self, source_type: str, content: str,
                                          essence: HumanEssence,
                                          patterns: dict = None) -> str:
        """构建七层本质提取提示词"""
        source_desc = {
            "text": "以下是一段关于某人的文字描述。请从中提取此人的七层本质。",
            "voice": "以下是某人语音转录的文字。请从说话方式、内容、情感中提取七层本质。",
            "video": "以下是某人视频中的语音转录。请综合分析其七层本质。",
            "document": "以下是某人写的文档。请从内容、思维方式、知识结构中提取七层本质。",
            "chat_history": "以下是某人的聊天记录。请从对话模式、语言习惯、关系互动中深度提取七层本质。",
            "self_description": "以下是某人对自己的描述。这是最直接的自我认知，请深度提取七层本质。",
        }

        # 当前已有信息（避免重复提取）
        current_state = ""
        completeness = essence.get_completeness()
        for layer, pct in completeness.items():
            if pct > 30:
                current_state += f"  - {layer}: 已有 {pct}% 信息\n"

        patterns_text = ""
        if patterns:
            patterns_text = f"""

统计分析结果（已验证的数据）:
- 平均消息长度: {patterns.get('avg_message_length', 0)} 字
- 活跃时段: {patterns.get('peak_active_hours', [])}
- 常用表情: {', '.join(patterns.get('top_emojis', [])[:5])}
- 表情使用频率: {patterns.get('emoji_usage_rate', 0)}
- 短消息比例: {patterns.get('short_message_rate', 0)}
- 感叹/疑问比例: {patterns.get('exclamation_rate', 0)} / {patterns.get('question_rate', 0)}
- 常用词汇: {', '.join(patterns.get('common_words', [])[:8])}
- 标点习惯: {patterns.get('punctuation_habits', {})}
"""

        return f"""你是一位深度人格分析专家。你的任务不是提取表面特征，而是理解一个人的内在运作方式。

{source_desc.get(source_type, "请提取七层本质")}

待分析内容:
---
{content[:6000]}
---
{patterns_text}

当前已有信息（避免重复，除非需要修正或深化）:
{current_state}

请以 JSON 格式输出七层本质分析:

{{
    "cognitive": {{
        "thinking_style": "思维风格（系统性/直觉性/分析性/发散性）",
        "decision_pattern": "决策模式（理性主导/感性主导/习惯驱动）",
        "learning_style": "学习风格",
        "cognitive_biases": ["常见认知偏差1", "偏差2"],
        "problem_solving": "解决问题的方式",
        "attention_pattern": "注意力分配模式",
        "creativity_style": "创造力表达方式"
    }},
    "knowledge": {{
        "expertise_domains": ["专业领域1", "领域2"],
        "mental_models": ["心智模型1", "模型2"],
        "beliefs": ["核心信念1", "信念2"],
        "curiosity_directions": ["好奇方向1", "方向2"],
        "knowledge_confidence": {{"领域": "信心程度描述"}}
    }},
    "emotional": {{
        "attachment_style": "依恋风格（安全型/焦虑型/回避型）",
        "emotional_triggers": ["触发器1", "触发器2"],
        "coping_mechanisms": ["应对机制1", "机制2"],
        "empathy_pattern": "共情方式",
        "vulnerability_style": "脆弱时的表现",
        "joy_sources": ["快乐来源1", "来源2"],
        "fear_patterns": ["恐惧模式1", "模式2"]
    }},
    "linguistic": {{
        "sentence_structures": ["常用句式1", "句式2"],
        "vocabulary_level": "词汇水平描述",
        "rhythm_pattern": "语言节奏（快/慢/变化）",
        "silence_pattern": "沉默模式（什么时候不说话）",
        "code_switching": "语码转换习惯",
        "metaphor_style": "隐喻/比喻风格",
        "humor_mechanism": "幽默机制（自嘲/谐音/反讽/冷笑话等）"
    }},
    "values": {{
        "core_values": ["核心价值观1", "价值观2"],
        "moral_framework": "道德框架描述",
        "life_philosophy": "人生哲学",
        "priority_order": ["第一优先", "第二优先", "第三优先"],
        "non_negotiables": ["不可妥协的事物1", "事物2"],
        "growth_direction": "成长方向"
    }},
    "relational": {{
        "social_energy": "社交能量模式（内向/外向/情境依赖）",
        "intimacy_style": "亲密关系风格",
        "conflict_style": "冲突处理方式",
        "authority_pattern": "对权威的态度",
        "care_pattern": "关心他人的方式",
        "boundary_style": "边界感"
    }},
    "narrative": {{
        "life_chapters": ["人生章节1", "章节2"],
        "turning_points": ["转折点1", "转折点2"],
        "regrets": ["遗憾1", "遗憾2"],
        "proud_moments": ["骄傲时刻1", "时刻2"],
        "unresolved_questions": ["未解之问1", "问题2"],
        "future_vision": "对未来的想象"
    }}
}}

分析要求:
1. 深度优先于广度 — 与其列出10个浅层特征，不如深入分析3个关键维度
2. 保留矛盾 — 如果发现矛盾，两个都保留，注明"在不同情境下"
3. 区分推测和事实 — 推测的内容加"（推测）"前缀
4. 关注变化 — 如果能感知到成长/变化趋势，记录在 growth_direction
5. 只输出 JSON，不要其他文字"""

    async def _extract_knowledge_graph(self, agent_id: str, content: str):
        """从内容中提取知识图谱"""
        prompt = f"""分析以下内容，提取涉及的知识领域和概念。

内容:
{content[:3000]}

以 JSON 数组输出:
[
    {{"domain": "领域", "concept": "具体概念", "understanding_level": 0.0-1.0, "personal_connection": "与当事人的关联"}},
]

只输出 JSON 数组。"""

        try:
            result = await self._call_llm(prompt)
            items = self._parse_json(result)
            if isinstance(items, list):
                db = self.db
                for item in items[:20]:
                    if item.get("domain") and item.get("concept"):
                        await db.execute(
                            """INSERT OR IGNORE INTO knowledge_graph
                               (id, agent_id, domain, concept, understanding_level, personal_connection, source, created_at)
                               VALUES (?,?,?,?,?,?,?,?)""",
                            (str(uuid.uuid4())[:12], agent_id,
                             item["domain"], item["concept"],
                             item.get("understanding_level", 0.5),
                             item.get("personal_connection", ""),
                             "refinement", __import__("time").time())
                        )
                await db.commit()
        except Exception as e:
            logger.warning(f"知识图谱提取失败: {e}")

    def _extract_linguistic_dna(self, messages: list[dict]) -> dict:
        """提取语言 DNA — 不依赖 LLM 的纯统计分析"""
        if not messages:
            return {}

        texts = [m.get("content", "") for m in messages if m.get("content")]
        if not texts:
            return {}

        # 句式结构分析
        sentence_patterns = []
        for t in texts:
            # 提取句式模式
            if t.endswith("吧"):
                sentence_patterns.append("祈使/建议句（...吧）")
            elif t.endswith(("呢", "吗", "？")):
                sentence_patterns.append("疑问句")
            elif t.endswith(("！", "!", "哈哈", "嘿嘿")):
                sentence_patterns.append("感叹/兴奋句")
            elif len(t) < 5:
                sentence_patterns.append("极简回复")

        pattern_freq = Counter(sentence_patterns).most_common(5)

        # 词汇丰富度
        all_chars = "".join(texts)
        unique_chars = len(set(all_chars))
        total_chars = len(all_chars)
        vocabulary_richness = unique_chars / total_chars if total_chars else 0

        # 中英混用检测
        has_english = sum(1 for t in texts if re.search(r'[a-zA-Z]', t))
        code_switch_rate = has_english / len(texts) if texts else 0

        # 标点习惯
        punct_counter = Counter()
        for t in texts:
            for p in ["～", "…", "。。。", "！！", "？？", "。。。", "哈哈哈",
                       "嗯嗯", "嘻嘻", "emmm", "hhh", "xswl", "yyds"]:
                if p in t.lower():
                    punct_counter[p] += 1

        # 沉默模式：分析不回复的时间段
        timestamps = [m.get("created_at", 0) for m in messages if m.get("created_at")]
        silence_pattern = "正常"
        if timestamps:
            from datetime import datetime
            hours = []
            for ts in timestamps:
                if isinstance(ts, (int, float)):
                    if ts > 1e12:
                        ts = ts / 1000
                    hours.append(datetime.fromtimestamp(ts).hour)
            hour_dist = Counter(hours)
            if hour_dist:
                least_active = hour_dist.most_common()[-1][0] if len(hour_dist) > 1 else 0
                silence_pattern = f"最不活跃时段: {least_active}:00"

        return {
            "sentence_structures": [p[0] for p in pattern_freq[:5]],
            "vocabulary_level": "丰富" if vocabulary_richness > 0.3 else "中等" if vocabulary_richness > 0.15 else "简洁",
            "rhythm_pattern": "快节奏" if sum(len(t) for t in texts) / len(texts) < 15 else "中等节奏",
            "silence_pattern": silence_pattern,
            "code_switching": f"中英混用率 {code_switch_rate:.0%}" if code_switch_rate > 0.1 else "纯中文为主",
            "humor_mechanism": self._detect_humor_mechanism(texts),
        }

    def _detect_humor_mechanism(self, texts: list[str]) -> str:
        """检测幽默机制"""
        mechanisms = []
        for t in texts:
            if any(w in t for w in ["哈哈", "笑死", "😂", "🤣", "hhh", "xswl"]):
                mechanisms.append("笑声表达")
            if re.search(r'[（(].*[）)]', t):
                mechanisms.append("括号注释式幽默")
            if "..." in t or "。。。" in t:
                mechanisms.append("省略号留白")
            if any(w in t for w in ["绝了", "离谱", "好家伙", "属于是"]):
                mechanisms.append("网络流行语")
        freq = Counter(mechanisms).most_common(3)
        return "、".join([m[0] for m in freq]) if freq else "待观察"

    def _analyze_relational_patterns(self, messages: list[dict]) -> dict:
        """分析关系模式"""
        if not messages:
            return {}

        # 统计与不同人的互动
        interactions = Counter()
        reply_patterns = {}
        for m in messages:
            sender = m.get("sender_name", "")
            if sender:
                interactions[sender] += 1

        # 分析回复模式（谁回复谁）
        for i in range(1, len(messages)):
            prev = messages[i-1]
            curr = messages[i]
            if prev.get("sender_name") != curr.get("sender_name"):
                pair = f"{curr.get('sender_name', '')} -> {prev.get('sender_name', '')}"
                reply_patterns[pair] = reply_patterns.get(pair, 0) + 1

        top_interactions = interactions.most_common(5)
        return {
            "social_energy": "活跃" if len(interactions) > 3 else "选择性社交",
            "care_pattern": self._detect_care_pattern(messages),
            "conflict_style": self._detect_conflict_style(messages),
        }

    def _detect_care_pattern(self, messages: list[str]) -> str:
        """检测关心他人的方式"""
        care_words = ["注意", "小心", "保重", "别忘了", "记得", "多喝", "早点", "别太累"]
        care_count = sum(1 for m in messages
                        for w in care_words
                        if w in m.get("content", ""))
        if care_count > len(messages) * 0.1:
            return "主动关心型 — 经常提醒和叮嘱"
        elif care_count > 0:
            return "适度关心型 — 在关键时刻表达"
        return "含蓄型 — 不太直接表达关心"

    def _detect_conflict_style(self, messages: list[str]) -> str:
        """检测冲突处理方式"""
        conflict_words = ["不对", "不行", "不同意", "但是", "可是", "我觉得不是"]
        conflict_count = sum(1 for m in messages
                            for w in conflict_words
                            if w in m.get("content", ""))
        if conflict_count > len(messages) * 0.05:
            return "直接表达型 — 愿意表达不同意见"
        return "回避型 — 倾向于避免冲突"

    def _analyze_emotional_patterns(self, messages: list[dict]) -> dict:
        """分析情感模式"""
        if not messages:
            return {}

        emotional_texts = []
        for m in messages:
            content = m.get("content", "")
            if any(w in content for w in ["开心", "高兴", "哈哈", "太好了", "❤️"]):
                emotional_texts.append(("positive", content))
            elif any(w in content for w in ["难过", "伤心", "😢", "烦", "生气"]):
                emotional_texts.append(("negative", content))
            elif any(w in content for w in ["担心", "怕", "焦虑", "怎么办"]):
                emotional_texts.append(("anxious", content))

        pos = sum(1 for t, _ in emotional_texts if t == "positive")
        neg = sum(1 for t, _ in emotional_texts if t == "negative")
        anx = sum(1 for t, _ in emotional_texts if t == "anxious")

        total = len(messages)
        return {
            "emotional_triggers": self._extract_triggers(messages),
            "coping_mechanisms": self._extract_coping(messages),
            "joy_sources": self._extract_joy_sources(messages),
            "empathy_pattern": "高共情" if pos > neg * 2 else "平衡型" if pos > neg else "内省型",
        }

    def _extract_triggers(self, messages: list[dict]) -> list:
        """提取情绪触发器"""
        triggers = []
        trigger_words = {
            "家人": "家庭相关话题",
            "工作": "工作压力",
            "钱": "经济相关",
            "健康": "健康问题",
            "回忆": "回忆往事",
        }
        for word, trigger in trigger_words.items():
            count = sum(1 for m in messages if word in m.get("content", ""))
            if count > 2:
                triggers.append(trigger)
        return triggers[:5]

    def _extract_coping(self, messages: list[dict]) -> list:
        """提取应对机制"""
        coping = []
        for m in messages:
            c = m.get("content", "")
            if any(w in c for w in ["算了", "无所谓", "随它去"]):
                coping.append("放下型应对")
            if any(w in c for w in ["想办法", "试试", "可以"]):
                coping.append("积极解决型")
            if any(w in c for w in ["哈哈", "笑死", "😂"]):
                coping.append("幽默化解型")
        return list(set(coping))[:5]

    def _extract_joy_sources(self, messages: list[dict]) -> list:
        """提取快乐来源"""
        joy = []
        joy_indicators = {
            "美食": ["好吃", "做饭", "美食", "吃"],
            "家人": ["家人", "孩子", "爸妈", "回家"],
            "成就": ["成功", "完成", "搞定", "做到了"],
            "娱乐": ["电影", "游戏", "音乐", "书"],
        }
        for source, words in joy_indicators.items():
            if any(w in m.get("content", "") for m in messages for w in words):
                joy.append(source)
        return joy[:5]

    # ==================== 工具方法 ====================

    async def _load_essence(self, agent_id: str) -> HumanEssence:
        """加载七层本质"""
        db = self.db
        async with db.execute(
            "SELECT essence_json FROM human_essence WHERE agent_id=?",
            (agent_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return HumanEssence.from_dict(json.loads(row[0]))
        return HumanEssence()

    async def _save_essence(self, agent_id: str, essence: HumanEssence):
        """保存七层本质"""
        import time as _time
        db = self.db
        now_ts = _time.time()
        essence_json = json.dumps(essence.to_dict(), ensure_ascii=False)
        completeness_json = json.dumps(essence.get_completeness(), ensure_ascii=False)

        await db.execute(
            """INSERT INTO human_essence (agent_id, essence_json, completeness_json, version, last_refined_at, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(agent_id) DO UPDATE SET
                   essence_json=excluded.essence_json,
                   completeness_json=excluded.completeness_json,
                   version=excluded.version,
                   last_refined_at=excluded.last_refined_at,
                   updated_at=excluded.updated_at""",
            (agent_id, essence_json, completeness_json,
             essence._version, now_ts, now_ts, now_ts)
        )
        await db.commit()

    async def _record_session(self, agent_id: str, source_type: str,
                                source_summary: str, dimensions: list,
                                depth_level: int = 1) -> str:
        """记录炼化会话"""
        import time as _time
        session_id = str(uuid.uuid4())[:12]
        db = self.db
        await db.execute(
            """INSERT INTO refinement_sessions
               (id, agent_id, source_type, source_summary, dimensions_affected, depth_level, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (session_id, agent_id, source_type, source_summary,
             json.dumps(dimensions, ensure_ascii=False), depth_level, _time.time())
        )
        await db.commit()
        return session_id

    def _estimate_depth(self, extracted: dict) -> int:
        """估算炼化深度 (1-5)"""
        depth = 1
        if extracted.get("cognitive"):
            depth = max(depth, 3)
        if extracted.get("values"):
            depth = max(depth, 4)
        if extracted.get("narrative", {}).get("turning_points"):
            depth = max(depth, 5)
        if extracted.get("emotional", {}).get("fear_patterns"):
            depth = max(depth, 4)
        if extracted.get("knowledge", {}).get("mental_models"):
            depth = max(depth, 4)
        return depth

    def _parse_json(self, text: str) -> dict:
        """解析 LLM 输出的 JSON"""
        try:
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {}

    async def _transcribe_audio(self, audio_path: str) -> str:
        """语音转文字"""
        try:
            wav_path = audio_path.rsplit(".", 1)[0] + "_whisper.wav"
            subprocess.run(
                ["ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1", "-y", wav_path],
                capture_output=True, timeout=30
            )
            stt_url = os.getenv("STT_API_URL", "")
            if stt_url:
                import httpx
                with open(wav_path, "rb") as f:
                    async with httpx.AsyncClient(timeout=60) as client:
                        resp = await client.post(stt_url, files={"file": ("audio.wav", f, "audio/wav")})
                        if resp.status_code == 200:
                            return resp.json().get("text", "")
            if os.path.exists(wav_path):
                os.remove(wav_path)
            return ""
        except Exception as e:
            logger.error(f"语音转录失败: {e}")
            return ""

    async def _extract_audio_from_video(self, video_path: str) -> str:
        """从视频提取音频"""
        audio_path = os.path.join(self.upload_dir, f"audio_{uuid.uuid4().hex[:8]}.mp3")
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame",
                 "-ar", "16000", "-ac", "1", "-y", audio_path],
                capture_output=True, timeout=120
            )
            return audio_path if result.returncode == 0 and os.path.exists(audio_path) else ""
        except Exception as e:
            logger.error(f"视频音频提取失败: {e}")
            return ""

    async def _extract_voice_features(self, audio_path: str) -> dict:
        """提取音色特征"""
        features = {"pitch": 0.5, "speed": 1.0, "energy": 0.5}
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            samples = audio.get_array_of_samples()
            if len(samples) > 0:
                zcr = sum(1 for i in range(1, len(samples))
                         if (samples[i] >= 0) != (samples[i-1] >= 0)) / len(samples)
                features["pitch"] = min(1.0, max(0.1, zcr * 8))
                features["energy"] = min(1.0, audio.rms / 10000)
        except Exception as e:
            logger.warning(f"音色特征提取失败: {e}")
        return features

    async def _parse_document(self, doc_path: str, doc_type: str = "") -> str:
        """解析文档内容"""
        if not doc_type:
            doc_type = Path(doc_path).suffix.lower()
        try:
            if doc_type in (".txt", ".md", ".json", ".csv", ".log", ".py", ".js"):
                with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            elif doc_type == ".pdf":
                try:
                    import PyPDF2
                    with open(doc_path, "rb") as f:
                        return "\n".join(p.extract_text() + "\n" for p in PyPDF2.PdfReader(f).pages[:50])
                except ImportError:
                    return ""
            elif doc_type in (".docx", ".doc"):
                try:
                    import docx
                    return "\n".join(p.text for p in docx.Document(doc_path).paragraphs if p.text.strip())
                except ImportError:
                    return ""
            return ""
        except Exception as e:
            logger.error(f"文档解析失败: {e}")
            return ""

    def _analyze_chat_patterns(self, messages: list[dict]) -> dict:
        """聊天模式统计分析（保留原有逻辑，增强）"""
        if not messages:
            return {}

        total = len(messages)
        msg_lengths = [len(m.get("content", "")) for m in messages]
        avg_length = sum(msg_lengths) / total if total else 0

        type_count = Counter(m.get("msg_type", "text") for m in messages)

        hours = []
        for m in messages:
            ts = m.get("created_at")
            if ts:
                from datetime import datetime
                if isinstance(ts, (int, float)):
                    if ts > 1e12: ts = ts / 1000
                    hours.append(datetime.fromtimestamp(ts).hour)
        hour_dist = Counter(hours)
        peak_hours = [h for h, _ in hour_dist.most_common(3)]

        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0]+", flags=re.UNICODE
        )
        all_emojis = []
        for m in messages:
            all_emojis.extend(emoji_pattern.findall(m.get("content", "")))
        emoji_freq = Counter(all_emojis).most_common(10)

        return {
            "total_messages": total,
            "avg_message_length": round(avg_length, 1),
            "msg_type_distribution": dict(type_count),
            "peak_active_hours": peak_hours,
            "emoji_usage_rate": round(len(all_emojis) / total, 2) if total else 0,
            "top_emojis": [e for e, _ in emoji_freq],
            "short_message_rate": round(sum(1 for l in msg_lengths if l < 10) / total, 2) if total else 0,
            "exclamation_rate": round(sum(1 for m in messages if '！' in m.get('content', '') or '!' in m.get('content', '')) / total, 2) if total else 0,
            "question_rate": round(sum(1 for m in messages if '？' in m.get('content', '') or '?' in m.get('content', '')) / total, 2) if total else 0,
        }

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        import httpx
        cfg = self.llm_config
        api_key = (cfg.get("api_key") or "").strip()
        if not api_key or "***" in api_key or api_key.startswith("sk-your"):
            raise LLMServiceUnavailable(
                "LLM API Key 未配置或仍是占位/脱敏值，请在服务器 .env 配置有效的 LLM_API_KEY/DEEPSEEK_API_KEY"
            )

        urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }
        provider = cfg.get("provider", "")
        base_url = (cfg.get("base_url") or urls.get(provider, "")).rstrip("/")
        if not base_url:
            raise LLMServiceUnavailable("LLM Base URL 未配置")

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": cfg.get("model", "gpt-4o"),
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": cfg.get("temperature", 0.7),
                        "max_tokens": 4096,
                    },
                )
            except httpx.TimeoutException as exc:
                raise LLMServiceUnavailable("LLM 服务请求超时，请稍后重试") from exc
            except httpx.HTTPError as exc:
                raise LLMServiceUnavailable(f"LLM 服务连接失败: {exc}") from exc

        if resp.status_code == 401:
            raise LLMServiceUnavailable(
                f"{provider or 'LLM'} API Key 无效或已过期，请重新配置有效 Key 后重启服务"
            )
        if resp.status_code == 403:
            raise LLMServiceUnavailable(f"{provider or 'LLM'} API Key 无权限访问当前模型")
        if resp.status_code == 429:
            raise LLMServiceUnavailable(f"{provider or 'LLM'} 接口限流或余额不足")
        if resp.status_code >= 500:
            raise LLMServiceUnavailable(f"{provider or 'LLM'} 服务暂时不可用({resp.status_code})")
        if resp.status_code >= 400:
            detail = resp.text[:200]
            raise LLMServiceUnavailable(f"{provider or 'LLM'} 请求失败({resp.status_code}): {detail}")

        try:
            message = resp.json()["choices"][0]["message"]
            content = (message.get("content") or "").strip()
            reasoning_content = (message.get("reasoning_content") or "").strip()
            return content or reasoning_content
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMServiceUnavailable("LLM 响应格式异常") from exc
