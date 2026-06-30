import base64
import mimetypes
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx
from loguru import logger


class ChatMultimodalAnalyzer:
    def __init__(self, llm_config: dict):
        self.llm_config = llm_config
        self.data_dir = Path("data")
        self.upload_dir = self.data_dir / "uploads"
        self.voice_dir = self.data_dir / "voices"
        self.tmp_dir = self.data_dir / "tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    async def analyze_message(self, msg_type: str, media_url: str = "",
                              content: str = "", sender_name: str = "") -> dict:
        if msg_type == "voice":
            return await self._analyze_voice(media_url or content, sender_name)
        if msg_type == "image":
            return await self._analyze_image(media_url or content, sender_name)
        return {"type": msg_type or "text", "text": content or "", "status": "skipped"}

    async def _analyze_voice(self, media_url: str, sender_name: str = "") -> dict:
        path = self._resolve_media_path(media_url, "voice")
        if not path or not path.exists():
            text = "语音消息：" + (sender_name or "对方") + "发来一条语音，但本地音频文件暂不可读。"
            return {"type": "voice", "text": text, "status": "missing_file"}
        transcript = await self._transcribe_audio(path)
        if transcript:
            text = "语音识别：" + transcript
            return {"type": "voice", "text": text, "transcript": transcript, "status": "transcribed"}
        text = "语音消息：已收到一条语音；当前未配置可用 STT_API_URL 或识别失败，暂时无法转写内容。"
        return {"type": "voice", "text": text, "transcript": "", "status": "stt_unavailable"}

    async def _analyze_image(self, media_url: str, sender_name: str = "") -> dict:
        path = self._resolve_media_path(media_url, "image")
        if not path or not path.exists():
            text = "图片消息：" + (sender_name or "对方") + "发来一张图片，但本地图片文件暂不可读。"
            return {"type": "image", "text": text, "status": "missing_file"}
        description = await self._describe_image(path)
        if description:
            text = "图片识别：" + description
            return {
                "type": "image",
                "text": text,
                "description": description,
                "status": "described",
                "filename": path.name,
            }
        size_kb = max(1, round(path.stat().st_size / 1024))
        text = "图片消息：收到一张图片/照片，文件 " + path.name + "，约 " + str(size_kb) + "KB。当前视觉模型不可用或不支持图片，已作为视觉记忆线索保存。"
        return {"type": "image", "text": text, "description": "", "status": "vision_unavailable", "filename": path.name}

    def _resolve_media_path(self, media_url: str, media_type: str):
        if not media_url:
            return None
        parsed_path = urlparse(media_url).path if "://" in media_url else media_url
        parsed_path = parsed_path.split("?", 1)[0]
        if "/api/uploads/" in parsed_path:
            filename = Path(parsed_path.split("/api/uploads/", 1)[1]).name
            return self.upload_dir / filename
        if "/api/voice/" in parsed_path:
            filename = Path(parsed_path.split("/api/voice/", 1)[1]).name
            return self.voice_dir / filename
        candidate = Path(parsed_path)
        if candidate.is_absolute() and candidate.exists():
            return candidate
        if media_type == "image":
            return self.upload_dir / candidate.name
        if media_type == "voice":
            return self.voice_dir / candidate.name
        return None

    async def _transcribe_audio(self, audio_path: Path) -> str:
        stt_url = os.getenv("STT_API_URL", "").strip()
        if not stt_url:
            return ""
        wav_path = self.tmp_dir / (audio_path.stem + "_chat_stt.wav")
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-y", str(wav_path)],
                capture_output=True,
                timeout=35,
            )
            if result.returncode != 0 or not wav_path.exists():
                logger.warning("聊天语音转码失败")
                return ""
            headers = {}
            stt_key = os.getenv("STT_API_KEY", "").strip()
            if stt_key:
                headers["Authorization"] = "Bearer " + stt_key
            with open(wav_path, "rb") as file_obj:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        stt_url,
                        files={"file": ("audio.wav", file_obj, "audio/wav")},
                        headers=headers,
                    )
            if resp.status_code != 200:
                logger.warning("聊天语音 STT 失败(" + str(resp.status_code) + "): " + resp.text[:160])
                return ""
            data = resp.json()
            return (data.get("text") or data.get("transcript") or data.get("result") or "").strip()
        except Exception as exc:
            logger.warning("聊天语音识别跳过: " + str(exc))
            return ""
        finally:
            try:
                if wav_path.exists():
                    wav_path.unlink()
            except OSError:
                pass

    async def _describe_image(self, image_path: Path) -> str:
        cfg = self.llm_config or {}
        api_key = (cfg.get("api_key") or "").strip()
        if not api_key or "***" in api_key or api_key.startswith("sk-your"):
            return ""
        base_url = (cfg.get("base_url") or self._default_base_url(cfg.get("provider", ""))).rstrip("/")
        if not base_url:
            return ""
        try:
            mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            prompt = (
                "请客观描述这张家庭聊天图片，输出中文 80-180 字。"
                "重点识别：人物数量、可见特征、场景、文字、是否像旧照片/自拍/工作截图、情绪氛围。"
                "不要臆造具体身份；如果只能推测，请使用可能。"
                "这些描述会作为数字人的视觉记忆，用于以后在同一个群里回忆类似照片。"
            )
            payload = {
                "model": cfg.get("model", "deepseek-v4-flash"),
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": "data:" + mime_type + ";base64," + encoded}},
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 600,
            }
            async with httpx.AsyncClient(timeout=35) as client:
                resp = await client.post(
                    base_url + "/chat/completions",
                    headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
                    json=payload,
                )
            if resp.status_code >= 400:
                logger.warning("图片识别模型不可用(" + str(resp.status_code) + "): " + resp.text[:180])
                return ""
            message = resp.json()["choices"][0]["message"]
            return ((message.get("content") or message.get("reasoning_content") or "").strip())[:800]
        except Exception as exc:
            logger.warning("图片识别跳过: " + str(exc))
            return ""

    @staticmethod
    def _default_base_url(provider: str) -> str:
        urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "local": "http://localhost:11434/v1",
        }
        return urls.get(provider or "", "")
