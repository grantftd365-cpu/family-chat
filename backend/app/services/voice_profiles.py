"""语音音色管理服务 - 支持录音/上传/分析/克隆/声音克隆引擎"""
import json
import os
import uuid
import subprocess
import asyncio
from pathlib import Path
from loguru import logger
import httpx

# 音频存储目录
VOICE_DIR = "data/voice_profiles"
TTS_DIR = "data/voices"
os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

# ElevenLabs 配置
elevenlabs_base = "https://api.elevenlabs.io/v1"

# edge-tts 预设音色库
EDGE_TTS_VOICES = {
    "zh-CN-XiaoxiaoNeural": {"name": "晓晓", "gender": "female", "pitch": 0.6, "speed": 1.0, "desc": "温柔女声"},
    "zh-CN-YunxiNeural": {"name": "云希", "gender": "male", "pitch": 0.4, "speed": 1.0, "desc": "稳重男声"},
    "zh-CN-XiaoyiNeural": {"name": "晓艺", "gender": "female", "pitch": 0.5, "speed": 0.9, "desc": "年长女声"},
    "zh-CN-YunjianNeural": {"name": "云健", "gender": "male", "pitch": 0.35, "speed": 1.1, "desc": "活力男声"},
    "zh-CN-XiaochenNeural": {"name": "晓辰", "gender": "female", "pitch": 0.65, "speed": 1.0, "desc": "甜美女声"},
    "zh-CN-XiaomoNeural": {"name": "晓墨", "gender": "female", "pitch": 0.5, "speed": 0.95, "desc": "知性女声"},
    "zh-CN-YunyangNeural": {"name": "云扬", "gender": "male", "pitch": 0.45, "speed": 1.0, "desc": "新闻男声"},
    "zh-CN-XiaoxuanNeural": {"name": "晓萱", "gender": "female", "pitch": 0.55, "speed": 1.0, "desc": "活力女声"},
    "zh-CN-XiaohanNeural": {"name": "晓涵", "gender": "female", "pitch": 0.5, "speed": 0.95, "desc": "温暖女声"},
    "zh-CN-YunfengNeural": {"name": "云枫", "gender": "male", "pitch": 0.4, "speed": 1.05, "desc": "磁性男声"},
    "zh-CN-XiaomengNeural": {"name": "晓梦", "gender": "female", "pitch": 0.7, "speed": 1.0, "desc": "萌系女声"},
    "zh-CN-YunzeNeural": {"name": "云泽", "gender": "male", "pitch": 0.38, "speed": 0.95, "desc": "成熟男声"},
}


class VoiceProfile:
    """语音音色配置"""

    def __init__(self, profile_id: str, name: str, edge_voice_id: str,
                 original_file: str = "", pitch: float = 0.5,
                 speed: float = 1.0, gender: str = "",
                 duration: float = 0, sample_rate: int = 16000,
                 metadata: dict = None, voice_engine: str = "edge-tts",
                 clone_voice_id: str = ""):
        self.id = profile_id
        self.name = name
        self.edge_voice_id = edge_voice_id
        self.original_file = original_file
        self.pitch = pitch
        self.speed = speed
        self.gender = gender
        self.duration = duration
        self.sample_rate = sample_rate
        self.metadata = metadata or {}
        self.voice_engine = voice_engine  # "edge-tts" | "elevenlabs"
        self.clone_voice_id = clone_voice_id  # ElevenLabs voice ID for cloned voices

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "edge_voice_id": self.edge_voice_id,
            "edge_voice_name": EDGE_TTS_VOICES.get(self.edge_voice_id, {}).get("name", ""),
            "original_file": self.original_file,
            "pitch": self.pitch,
            "speed": self.speed,
            "gender": self.gender,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "metadata": self.metadata,
            "voice_engine": self.voice_engine,
            "clone_voice_id": self.clone_voice_id,
            "is_cloned": self.voice_engine == "elevenlabs" and bool(self.clone_voice_id),
        }


class VoiceProfileManager:
    """语音音色管理器"""

    def __init__(self, db):
        self.db = db
        self._profiles: dict[str, VoiceProfile] = {}
        # agent_id -> profile_id 映射
        self._agent_voice_map: dict[str, str] = {}

    async def init_db(self):
        """初始化数据库表"""
        db = self.db
        await db.execute("""
            CREATE TABLE IF NOT EXISTS voice_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                edge_voice_id TEXT NOT NULL,
                original_file TEXT DEFAULT '',
                pitch REAL DEFAULT 0.5,
                speed REAL DEFAULT 1.0,
                gender TEXT DEFAULT '',
                duration REAL DEFAULT 0,
                sample_rate INTEGER DEFAULT 16000,
                metadata TEXT DEFAULT '{}',
                voice_engine TEXT DEFAULT 'edge-tts',
                clone_voice_id TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_voice_map (
                agent_id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES voice_profiles(id)
            )
        """)
        await db.commit()
        await self._load_profiles()

    async def _load_profiles(self):
        """从数据库加载音色配置"""
        db = self.db
        async with db.execute("SELECT * FROM voice_profiles") as cursor:
            columns = [d[0] for d in cursor.description]
            async for row in cursor:
                data = dict(zip(columns, row))
                meta = {}
                try:
                    meta = json.loads(data.get("metadata", "{}"))
                except:
                    pass
                self._profiles[data["id"]] = VoiceProfile(
                    profile_id=data["id"],
                    name=data["name"],
                    edge_voice_id=data["edge_voice_id"],
                    original_file=data.get("original_file", ""),
                    pitch=data.get("pitch", 0.5),
                    speed=data.get("speed", 1.0),
                    gender=data.get("gender", ""),
                    duration=data.get("duration", 0),
                    sample_rate=data.get("sample_rate", 16000),
                    metadata=meta,
                    voice_engine=data.get("voice_engine", "edge-tts"),
                    clone_voice_id=data.get("clone_voice_id", ""),
                )

        async with db.execute("SELECT * FROM agent_voice_map") as cursor:
            async for row in cursor:
                self._agent_voice_map[row[0]] = row[1]

        logger.info(f"加载了 {len(self._profiles)} 个语音音色配置")

    async def create_profile(self, name: str, audio_file_path: str = "",
                              edge_voice_id: str = "", gender: str = "",
                              voice_engine: str = "edge-tts",
                              clone_voice_id: str = "") -> VoiceProfile:
        """创建语音音色配置
        如果 voice_engine='elevenlabs' 且提供了 clone_voice_id，直接使用克隆声音
        如果提供了音频文件且 voice_engine='elevenlabs'，自动克隆
        否则匹配 edge-tts 预设声音
        """
        profile_id = f"vp_{uuid.uuid4().hex[:12]}"
        pitch = 0.5
        speed = 1.0
        duration = 0
        original_file = ""

        if audio_file_path:
            # 保存音频文件
            ext = Path(audio_file_path).suffix or ".mp3"
            saved_path = os.path.join(VOICE_DIR, f"{profile_id}{ext}")
            if os.path.exists(audio_file_path):
                import shutil
                shutil.copy2(audio_file_path, saved_path)
                original_file = saved_path

            if voice_engine == "elevenlabs":
                # ElevenLabs 声音克隆
                if not clone_voice_id:
                    clone_voice_id = await self._clone_elevenlabs_voice(saved_path, name)
                    if not clone_voice_id:
                        logger.warning("ElevenLabs 声音克隆失败，回退到 edge-tts")
                        voice_engine = "edge-tts"

            if voice_engine != "elevenlabs":
                # 分析音频特征（容错处理）
                try:
                    features = await self._analyze_audio(saved_path)
                    pitch = features.get("pitch", 0.5)
                    speed = features.get("speed", 1.0)
                    duration = features.get("duration", 0)
                    if not gender:
                        gender = features.get("gender", "")
                except Exception as e:
                    logger.warning(f"音频分析失败，使用默认值: {e}")

                # 匹配最接近的 edge-tts 声音
                if not edge_voice_id:
                    edge_voice_id = self._match_voice(pitch, speed, gender)

        if not edge_voice_id and voice_engine != "elevenlabs":
            edge_voice_id = "zh-CN-XiaoxiaoNeural"

        profile = VoiceProfile(
            profile_id=profile_id,
            name=name,
            edge_voice_id=edge_voice_id,
            original_file=original_file,
            pitch=pitch,
            speed=speed,
            gender=gender,
            duration=duration,
            voice_engine=voice_engine,
            clone_voice_id=clone_voice_id,
        )

        # 存入数据库
        db = self.db
        from ..models.database import now
        await db.execute(
            """INSERT INTO voice_profiles (id, name, edge_voice_id, original_file, pitch, speed, gender, duration, sample_rate, metadata, voice_engine, clone_voice_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (profile.id, profile.name, profile.edge_voice_id, profile.original_file,
             profile.pitch, profile.speed, profile.gender, profile.duration,
             profile.sample_rate, json.dumps(profile.metadata),
             profile.voice_engine, profile.clone_voice_id, now(), now())
        )
        await db.commit()

        self._profiles[profile_id] = profile
        engine_desc = "ElevenLabs 克隆" if voice_engine == "elevenlabs" else "edge-tts"
        logger.info(f"创建语音音色: {name} -> {engine_desc} ({edge_voice_id or clone_voice_id})")
        return profile

    async def _clone_elevenlabs_voice(self, audio_path: str, name: str) -> str:
        """使用 ElevenLabs API 克隆声音
        上传音频文件 -> 创建克隆声音 -> 返回 voice_id
        """
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            logger.warning("ELEVENLABS_API_KEY 未配置，无法克隆声音")
            return ""

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with open(audio_path, "rb") as f:
                    audio_data = f.read()

                # 检查文件大小 (ElevenLabs 需要至少 1KB)
                if len(audio_data) < 1024:
                    logger.warning("音频文件太短，无法克隆")
                    return ""

                resp = await client.post(
                    f"{elevenlabs_base}/voices/add",
                    headers={"xi-api-key": api_key},
                    files={
                        "files": (Path(audio_path).name, audio_data, "audio/mpeg"),
                    },
                    data={
                        "name": f"FamilyChat_{name}_{uuid.uuid4().hex[:6]}",
                        "description": f"FamilyChat 克隆音色 - {name}",
                    },
                )

                if resp.status_code == 200:
                    result = resp.json()
                    voice_id = result.get("voice_id", "")
                    logger.info(f"ElevenLabs 声音克隆成功: {voice_id}")
                    return voice_id
                else:
                    logger.error(f"ElevenLabs 克隆失败: {resp.status_code} {resp.text}")
                    return ""

        except Exception as e:
            logger.error(f"ElevenLabs 克隆异常: {e}")
            return ""

    async def _analyze_audio(self, audio_path: str) -> dict:
        """分析音频文件的音色特征"""
        features = {"pitch": 0.5, "speed": 1.0, "duration": 0, "gender": ""}

        try:
            # 使用 ffprobe 获取音频信息
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", audio_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                features["duration"] = float(info.get("format", {}).get("duration", 0))

                # 获取采样率
                for stream in info.get("streams", []):
                    if stream.get("codec_type") == "audio":
                        features["sample_rate"] = int(stream.get("sample_rate", 16000))
                        break
        except FileNotFoundError:
            logger.warning("ffprobe 未安装，跳过音频元信息分析")
        except Exception as e:
            logger.warning(f"ffprobe 分析失败: {e}")

        try:
            # 使用 pydub 分析音高和速度
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)

            # 分析音量和音高
            loudness = audio.rms
            # 简单的音高估计：通过 zero crossing rate
            samples = audio.get_array_of_samples()
            if len(samples) > 0:
                # Zero crossing rate 作为音高的粗略估计
                zero_crossings = sum(1 for i in range(1, len(samples))
                                    if (samples[i] >= 0) != (samples[i-1] >= 0))
                zcr = zero_crossings / len(samples)
                # 归一化到 0-1 范围 (典型 ZCR 范围 0.01-0.15)
                features["pitch"] = min(1.0, max(0.1, zcr * 8))

                # 估计语速：通过音量变化的频率
                chunk_size = 1600  # 100ms at 16kHz
                energy_changes = 0
                prev_energy = 0
                for i in range(0, len(samples) - chunk_size, chunk_size):
                    chunk = samples[i:i + chunk_size]
                    energy = sum(abs(s) for s in chunk) / len(chunk)
                    if abs(energy - prev_energy) > 500:
                        energy_changes += 1
                    prev_energy = energy
                duration = features["duration"] or (len(samples) / 16000)
                if duration > 0:
                    syllable_rate = energy_changes / duration
                    # 归一化：正常语速约 3-5 音节/秒
                    features["speed"] = min(1.3, max(0.7, syllable_rate / 4))

            # 简单的性别判断：基于音高
            if features["pitch"] < 0.35:
                features["gender"] = "male"
            elif features["pitch"] > 0.55:
                features["gender"] = "female"

        except ImportError:
            logger.warning("pydub 未安装，跳过详细音频分析")
        except Exception as e:
            logger.warning(f"音频分析失败: {e}")

        return features

    def _match_voice(self, pitch: float, speed: float, gender: str = "") -> str:
        """根据音频特征匹配最接近的 edge-tts 声音"""
        candidates = EDGE_TTS_VOICES

        # 如果判断了性别，优先匹配同性别
        if gender:
            same_gender = {k: v for k, v in candidates.items() if v["gender"] == gender}
            if same_gender:
                candidates = same_gender

        # 计算距离，找最接近的声音
        best_voice = None
        best_distance = float("inf")

        for voice_id, info in candidates.items():
            dist = abs(info["pitch"] - pitch) * 2 + abs(info["speed"] - speed)
            if dist < best_distance:
                best_distance = dist
                best_voice = voice_id

        return best_voice or "zh-CN-XiaoxiaoNeural"

    async def get_profile(self, profile_id: str) -> VoiceProfile | None:
        return self._profiles.get(profile_id)

    async def list_profiles(self) -> list[dict]:
        return [p.to_dict() for p in self._profiles.values()]

    async def delete_profile(self, profile_id: str) -> bool:
        if profile_id not in self._profiles:
            return False

        profile = self._profiles[profile_id]

        # 删除音频文件
        if profile.original_file and os.path.exists(profile.original_file):
            os.remove(profile.original_file)

        # 从数据库删除
        db = self.db
        await db.execute("DELETE FROM voice_profiles WHERE id=?", (profile_id,))
        await db.execute("DELETE FROM agent_voice_map WHERE profile_id=?", (profile_id,))
        await db.commit()

        del self._profiles[profile_id]
        # 清理 agent 映射
        for aid, pid in list(self._agent_voice_map.items()):
            if pid == profile_id:
                del self._agent_voice_map[aid]

        return True

    async def update_profile(self, profile_id: str, **kwargs) -> bool:
        if profile_id not in self._profiles:
            return False

        profile = self._profiles[profile_id]
        db = self.db

        updates = []
        params = []
        for key in ["name", "edge_voice_id", "pitch", "speed", "gender"]:
            if key in kwargs:
                setattr(profile, key, kwargs[key])
                updates.append(f"{key}=?")
                params.append(kwargs[key])

        if not updates:
            return True

        from ..models.database import now
        updates.append("updated_at=?")
        params.append(now())
        params.append(profile_id)

        await db.execute(
            f"UPDATE voice_profiles SET {', '.join(updates)} WHERE id=?",
            params
        )
        await db.commit()
        return True

    async def assign_to_agent(self, agent_id: str, profile_id: str) -> bool:
        """将音色配置分配给数字人"""
        if profile_id not in self._profiles:
            return False

        db = self.db
        await db.execute(
            "INSERT OR REPLACE INTO agent_voice_map (agent_id, profile_id) VALUES (?,?)",
            (agent_id, profile_id)
        )
        await db.commit()
        self._agent_voice_map[agent_id] = profile_id

        # 更新 agent 的 voice_config
        profile = self._profiles[profile_id]
        await db.execute(
            "UPDATE agents SET voice_config=? WHERE id=?",
            (json.dumps({
                "profile_id": profile_id,
                "edge_voice_id": profile.edge_voice_id,
                "pitch": profile.pitch,
                "speed": profile.speed,
            }), agent_id)
        )
        await db.commit()

        logger.info(f"数字人 {agent_id} 使用音色: {profile.name}")
        return True

    async def get_agent_voice(self, agent_id: str) -> dict | None:
        """获取数字人关联的音色配置"""
        profile_id = self._agent_voice_map.get(agent_id)
        if not profile_id:
            return None
        profile = self._profiles.get(profile_id)
        if not profile:
            return None
        return profile.to_dict()

    async def synthesize(self, text: str, profile_id: str = "",
                          edge_voice_id: str = "") -> str:
        """使用指定音色合成语音，返回文件路径
        优先使用 ElevenLabs（如果音色是克隆的），否则用 edge-tts
        """
        profile = None
        if profile_id:
            profile = self._profiles.get(profile_id)

        # ElevenLabs 克隆声音合成
        if profile and profile.voice_engine == "elevenlabs" and profile.clone_voice_id:
            result = await self._synthesize_elevenlabs(text, profile.clone_voice_id)
            if result:
                return result
            logger.warning("ElevenLabs 合成失败，回退到 edge-tts")

        # edge-tts 合成
        if profile:
            edge_voice_id = profile.edge_voice_id
        if not edge_voice_id:
            edge_voice_id = "zh-CN-XiaoxiaoNeural"

        output_path = os.path.join(TTS_DIR, f"tts_{uuid.uuid4().hex[:8]}.mp3")

        try:
            import edge_tts
            voice_info = EDGE_TTS_VOICES.get(edge_voice_id, {})
            rate = f"+0%"
            if voice_info:
                speed_diff = voice_info.get("speed", 1.0) - 1.0
                rate = f"{int(speed_diff * 100)}%"

            communicate = edge_tts.Communicate(text, edge_voice_id, rate=rate)
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return ""

    async def _synthesize_elevenlabs(self, text: str, voice_id: str) -> str:
        """使用 ElevenLabs API 合成语音"""
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            return ""

        output_path = os.path.join(TTS_DIR, f"el_{uuid.uuid4().hex[:8]}.mp3")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{elevenlabs_base}/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                            "style": 0.0,
                            "use_speaker_boost": True,
                        },
                    },
                )

                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    return output_path
                else:
                    logger.error(f"ElevenLabs 合成失败: {resp.status_code}")
                    return ""

        except Exception as e:
            logger.error(f"ElevenLabs 合成异常: {e}")
            return ""

    def get_available_voices(self) -> list[dict]:
        """获取所有可用的 edge-tts 声音"""
        return [
            {"id": vid, **info}
            for vid, info in EDGE_TTS_VOICES.items()
        ]
