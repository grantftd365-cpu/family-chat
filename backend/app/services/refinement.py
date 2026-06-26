"""多模态炼化服务 - 支持语音/视频/文档/聊天记录炼化数字人"""
import asyncio
import json
import os
import subprocess
import uuid
from pathlib import Path
from loguru import logger


class MultiModalRefinement:
    """多模态炼化引擎"""

    def __init__(self, db, llm_config: dict):
        self.db = db
        self.llm_config = llm_config
        self.upload_dir = "data/refinement_uploads"
        os.makedirs(self.upload_dir, exist_ok=True)

    async def refine_from_text(self, agent_id: str, text: str) -> dict:
        """从文本炼化数字人"""
        prompt = self._build_extraction_prompt("text", text)
        result = await self._call_llm(prompt)
        traits = self._parse_traits(result)
        await self._apply_traits(agent_id, traits)
        return {"success": True, "traits": traits, "source": "text"}

    async def refine_from_voice(self, agent_id: str, audio_path: str) -> dict:
        """从语音炼化数字人
        流程: 语音 -> 文字转录 -> 性格提取 -> 应用
        如果转录服务不可用，直接分析音频特征
        """
        # 1. 语音转文字
        transcript = await self._transcribe_audio(audio_path)

        # 2. 提取音色特征
        voice_features = await self._extract_voice_features(audio_path)

        if not transcript:
            # 转录不可用，使用音频特征进行基本分析
            logger.info("语音转录不可用，使用音频特征分析")
            traits = {
                "voice_features": voice_features,
                "speaking_style": "根据音频特征分析",
            }
            await self._apply_traits(agent_id, traits)
            return {"success": True, "traits": traits, "transcript": "", "source": "voice", "note": "语音转录服务未配置，已提取音色特征"}

        # 3. 从转录文本提取性格
        prompt = self._build_extraction_prompt("voice_transcript", transcript)
        result = await self._call_llm(prompt)
        traits = self._parse_traits(result)
        traits["voice_features"] = voice_features

        await self._apply_traits(agent_id, traits)
        return {"success": True, "traits": traits, "transcript": transcript, "source": "voice"}

    async def refine_from_video(self, agent_id: str, video_path: str) -> dict:
        """从视频炼化数字人
        流程: 视频 -> 提取音频 -> 语音转文字 + 音色提取 -> 性格提取 -> 应用
        """
        # 1. 提取音频
        audio_path = await self._extract_audio_from_video(video_path)
        if not audio_path:
            return {"success": False, "error": "视频音频提取失败（需要安装 ffmpeg）"}

        try:
            # 2. 语音转文字
            transcript = await self._transcribe_audio(audio_path)

            # 3. 提取音色特征
            voice_features = await self._extract_voice_features(audio_path)

            if not transcript:
                # 转录不可用，使用音频特征
                logger.info("语音转录不可用，使用视频音频特征分析")
                traits = {
                    "voice_features": voice_features,
                    "speaking_style": "根据视频音频特征分析",
                }
                await self._apply_traits(agent_id, traits)
                return {"success": True, "traits": traits, "transcript": "",
                        "voice_features": voice_features, "source": "video",
                        "note": "语音转录服务未配置，已提取音色特征"}

            # 4. 从转录文本提取性格
            prompt = self._build_extraction_prompt("video_transcript", transcript)
            result = await self._call_llm(prompt)
            traits = self._parse_traits(result)
            traits["voice_features"] = voice_features

            await self._apply_traits(agent_id, traits)

            return {"success": True, "traits": traits, "transcript": transcript,
                    "voice_features": voice_features, "source": "video"}
        finally:
            # 5. 清理临时文件
            if os.path.exists(audio_path):
                os.remove(audio_path)

    async def refine_from_document(self, agent_id: str, doc_path: str,
                                     doc_type: str = "") -> dict:
        """从文档炼化数字人
        支持: txt, pdf, docx, md, json
        """
        # 1. 解析文档内容
        content = await self._parse_document(doc_path, doc_type)
        if not content:
            return {"success": False, "error": "文档解析失败或内容为空"}

        # 2. 从文档内容提取性格
        prompt = self._build_extraction_prompt("document", content[:5000])  # 限制长度
        result = await self._call_llm(prompt)
        traits = self._parse_traits(result)
        await self._apply_traits(agent_id, traits)
        return {"success": True, "traits": traits, "content_preview": content[:500], "source": "document"}

    async def refine_from_chat_history(self, agent_id: str, messages: list[dict]) -> dict:
        """从聊天记录炼化数字人
        分析消息模式、说话习惯、性格特征
        """
        # 1. 分析聊天模式
        analysis = self._analyze_chat_patterns(messages)

        # 2. 构建分析文本
        chat_text = "\n".join([
            f"{m.get('sender_name', '未知')}: {m.get('content', '')}"
            for m in messages[-100:]  # 最近100条
        ])

        # 3. 提取性格
        prompt = self._build_extraction_prompt("chat_history", chat_text, analysis)
        result = await self._call_llm(prompt)
        traits = self._parse_traits(result)
        traits["chat_analysis"] = analysis

        await self._apply_traits(agent_id, traits)
        return {"success": True, "traits": traits, "analysis": analysis, "source": "chat_history"}

    # ========== 内部方法 ==========

    async def _transcribe_audio(self, audio_path: str) -> str:
        """语音转文字 - 使用 Whisper 或简单的音频分析"""
        try:
            # 尝试使用 ffmpeg 转换格式后用简单方法
            wav_path = audio_path.rsplit(".", 1)[0] + "_whisper.wav"
            subprocess.run(
                ["ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1",
                 "-y", wav_path],
                capture_output=True, timeout=30
            )

            # 如果有 whisper 或其他 STT 服务可用
            stt_url = os.getenv("STT_API_URL", "")
            if stt_url:
                import httpx
                with open(wav_path, "rb") as f:
                    async with httpx.AsyncClient(timeout=60) as client:
                        resp = await client.post(
                            stt_url,
                            files={"file": ("audio.wav", f, "audio/wav")},
                        )
                        if resp.status_code == 200:
                            return resp.json().get("text", "")

            # 后备方案：返回提示
            logger.warning("语音转录服务未配置，使用 LLM 分析替代")
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
            if result.returncode == 0 and os.path.exists(audio_path):
                return audio_path
            logger.error(f"ffmpeg 提取音频失败: {result.stderr}")
            return ""
        except FileNotFoundError:
            logger.error("ffmpeg 未安装，无法从视频提取音频")
            return ""
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
                # Zero crossing rate
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
                        reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in reader.pages[:50]:  # 最多50页
                            text += page.extract_text() + "\n"
                        return text
                except ImportError:
                    logger.warning("PyPDF2 未安装，无法解析 PDF")
                    return ""

            elif doc_type in (".docx", ".doc"):
                try:
                    import docx
                    doc = docx.Document(doc_path)
                    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                except ImportError:
                    logger.warning("python-docx 未安装，无法解析 Word 文档")
                    return ""

            elif doc_type in (".xlsx", ".xls"):
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(doc_path, read_only=True)
                    text = ""
                    for sheet in wb.worksheets[:5]:
                        for row in sheet.iter_rows(max_row=100, values_only=True):
                            text += " | ".join(str(c) if c else "" for c in row) + "\n"
                    return text
                except ImportError:
                    logger.warning("openpyxl 未安装，无法解析 Excel")
                    return ""

            else:
                logger.warning(f"不支持的文档格式: {doc_type}")
                return ""

        except Exception as e:
            logger.error(f"文档解析失败: {e}")
            return ""

    def _analyze_chat_patterns(self, messages: list[dict]) -> dict:
        """分析聊天模式 - 深度习惯学习"""
        if not messages:
            return {}

        import re
        from collections import Counter

        total = len(messages)
        msg_lengths = [len(m.get("content", "")) for m in messages]
        avg_length = sum(msg_lengths) / total if total else 0

        # 消息类型分布
        type_count = Counter(m.get("msg_type", "text") for m in messages)

        # 活跃时间分析
        hours = []
        for m in messages:
            ts = m.get("created_at")
            if ts:
                from datetime import datetime
                if isinstance(ts, (int, float)):
                    if ts > 1e12: ts = ts / 1000
                    hours.append(datetime.fromtimestamp(ts).hour)
                elif isinstance(ts, str):
                    try: hours.append(datetime.fromisoformat(ts).hour)
                    except: pass
        hour_dist = Counter(hours)
        peak_hours = [h for h, _ in hour_dist.most_common(3)]

        # 表情使用分析
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001f926-\U0001f937"
            "\U00010000-\U0010ffff]+", flags=re.UNICODE
        )
        all_emojis = []
        for m in messages:
            content = m.get("content", "")
            all_emojis.extend(emoji_pattern.findall(content))
        emoji_freq = Counter(all_emojis).most_common(10)
        emoji_rate = round(len(all_emojis) / total, 2) if total else 0

        # 常用词汇和短语分析
        all_words = []
        all_phrases = []
        for m in messages:
            content = m.get("content", "").strip()
            if not content or content.startswith('['): continue
            # 提取常用词（2-4字）
            for i in range(len(content)-1):
                for l in range(2, min(5, len(content)-i+1)):
                    word = content[i:i+l]
                    if not re.match(r'^[\s\W]+$', word):
                        all_words.append(word)
            # 提取完整短语（标点分割）
            phrases = re.split(r'[，。！？,.!?]', content)
            all_phrases.extend([p.strip() for p in phrases if 2 <= len(p.strip()) <= 20])

        word_freq = Counter(all_words).most_common(20)
        phrase_freq = Counter(all_phrases).most_common(10)

        # 语气和风格分析
        exclamation_rate = sum(1 for m in messages if '！' in m.get('content','') or '!' in m.get('content','')) / total if total else 0
        question_rate = sum(1 for m in messages if '？' in m.get('content','') or '?' in m.get('content','')) / total if total else 0
        short_msg_rate = sum(1 for l in msg_lengths if l < 10) / total if total else 0

        # 标点习惯
        punct_counter = Counter()
        for m in messages:
            c = m.get('content', '')
            for p in ['～', '…', '。。。', '！！', '？？', '哈哈', '嗯嗯', '嘻嘻']:
                if p in c:
                    punct_counter[p] += 1

        return {
            "total_messages": total,
            "avg_message_length": round(avg_length, 1),
            "msg_type_distribution": dict(type_count),
            "peak_active_hours": peak_hours,
            "emoji_usage_rate": emoji_rate,
            "top_emojis": [e for e, _ in emoji_freq],
            "short_message_rate": round(short_msg_rate, 2),
            "exclamation_rate": round(exclamation_rate, 2),
            "question_rate": round(question_rate, 2),
            "common_words": [w for w, _ in word_freq[:10]],
            "common_phrases": [p for p, _ in phrase_freq[:5]],
            "punctuation_habits": dict(punct_counter.most_common(5)),
        }

    def _build_extraction_prompt(self, source_type: str, content: str,
                                  analysis: dict = None) -> str:
        """构建性格提取提示词 - 深度习惯学习"""
        source_desc = {
            "text": "以下是一段文字描述，请从中提取人物的性格特征",
            "voice_transcript": "以下是语音转录的文字，请从中提取说话者的性格特征",
            "video_transcript": "以下是视频中提取的语音转录，请从中提取说话者的性格特征",
            "document": "以下是文档内容，请从中提取人物的性格特征",
            "chat_history": "以下是聊天记录，请深度分析发送者的性格特征、说话习惯、用词偏好、表情使用习惯",
        }

        analysis_text = ""
        if analysis:
            analysis_text = f"""\n\n聊天习惯分析:
- 平均消息长度: {analysis.get('avg_message_length', 0)} 字
- 活跃时段: {analysis.get('peak_active_hours', [])}
- 常用表情: {', '.join(analysis.get('top_emojis', [])[:5])}
- 表情使用频率: {analysis.get('emoji_usage_rate', 0)}
- 短消息比例: {analysis.get('short_message_rate', 0)}
- 感叹句比例: {analysis.get('exclamation_rate', 0)}
- 疑问句比例: {analysis.get('question_rate', 0)}
- 常用词汇: {', '.join(analysis.get('common_words', [])[:8])}
- 常用短语: {', '.join(analysis.get('common_phrases', [])[:3])}
- 标点习惯: {analysis.get('punctuation_habits', {})}
"""

        return f"""{source_desc.get(source_type, "请提取性格特征")}

内容:
---
{content[:4000]}
---
{analysis_text}

请以 JSON 格式输出分析结果:
{{
    "name": "推测的姓名或昵称",
    "personality_traits": ["性格特征1", "性格特征2"],
    "speaking_style": "说话风格描述（要详细，包括语气、节奏、用词偏好）",
    "interests": ["兴趣1", "兴趣2"],
    "catchphrases": ["口头禅1", "口头禅2"],
    "humor_style": "幽默风格",
    "emotional_pattern": "情感模式",
    "backstory": "背景故事推测",
    "values": ["价值观1", "价值观2"],
    "age_range": "推测年龄段",
    "gender": "推测性别",
    "emoji_habits": "表情使用习惯描述",
    "response_style": "回复风格（简短/详细、快/慢、主动/被动）",
    "typical_responses": ["典型回复1", "典型回复2"]
}}

只输出 JSON，不要其他文字。"""

    def _parse_traits(self, llm_output: str) -> dict:
        """解析 LLM 输出的性格特征"""
        try:
            clean = llm_output.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(clean)
        except json.JSONDecodeError:
            # 尝试提取 JSON 部分
            import re
            match = re.search(r'\{[^{}]*\}', llm_output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {"raw": llm_output}

    async def _apply_traits(self, agent_id: str, traits: dict):
        """将提取的性格特征应用到数字人"""
        db = self.db

        # 构建更新字段
        updates = []
        params = []

        if traits.get("personality_traits"):
            updates.append("traits=?")
            params.append(json.dumps(traits["personality_traits"], ensure_ascii=False))

        if traits.get("speaking_style"):
            updates.append("speaking_style=?")
            params.append(traits["speaking_style"])

        if traits.get("interests"):
            updates.append("interests=?")
            params.append(json.dumps(traits["interests"], ensure_ascii=False))

        if traits.get("catchphrases"):
            updates.append("catchphrases=?")
            params.append(json.dumps(traits["catchphrases"], ensure_ascii=False))

        if traits.get("humor_style"):
            updates.append("humor_style=?")
            params.append(traits["humor_style"])

        if traits.get("emotional_pattern"):
            updates.append("emotional_pattern=?")
            params.append(traits["emotional_pattern"])

        if traits.get("backstory"):
            updates.append("backstory=?")
            params.append(traits["backstory"])

        # 如果只提取了名字但没有其他特征，跳过更新
        if traits.get("name") and not any([traits.get("personality_traits"), traits.get("speaking_style"), traits.get("interests")]):
            logger.info(f"提取了名字但无性格特征: {traits.get('name')}")

        if not updates:
            logger.warning(f"没有可应用的性格特征: {agent_id}")
            return

        from ..models.database import now
        updates.append("updated_at=?")
        params.append(now())
        params.append(agent_id)

        await db.execute(
            f"UPDATE agents SET {', '.join(updates)} WHERE id=?",
            params
        )
        await db.commit()

        logger.info(f"数字人 {agent_id} 已应用 {len(updates)-1} 项性格特征")

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        import httpx
        cfg = self.llm_config
        api_key = cfg.get("api_key", "")
        if not api_key:
            raise ValueError("LLM API Key 未配置")

        urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }
        base_url = cfg.get("base_url") or urls.get(cfg.get("provider", ""), "")
        if not base_url:
            raise ValueError("LLM Base URL 未配置")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": cfg.get("model", "gpt-4o"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
