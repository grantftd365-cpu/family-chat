"""FamilyChat - FastAPI 主应用 v2.0"""
import asyncio
import json
import os
import random
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
import time as _time

from .models.database import init_db, get_db, gen_id, now
from .core.auth import hash_password, verify_password, create_token, get_current_user, get_ws_user
from .core.websocket import ws_manager
from .agents.core import AgentManager
from .services.voice_profiles import VoiceProfileManager
from .services.refinement import MultiModalRefinement

# ==================== Lifespan ====================

agent_manager: AgentManager = None
voice_profile_manager: VoiceProfileManager = None
refinement_service: MultiModalRefinement = None


async def _proactive_scheduler():
    """定时检查 Agent 主动发言"""
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        try:
            if not agent_manager:
                continue
            db = await get_db()
            try:
                async with db.execute(
                    "SELECT id, name, proactive_config FROM agents WHERE enabled=1"
                ) as cursor:
                    async for row in cursor:
                        cfg = json.loads(row[2]) if row[2] else {}
                        if not cfg.get("enabled"):
                            continue
                        freq = cfg.get("frequency_hours", 6)
                        last = cfg.get("last_proactive", 0)
                        if _time.time() - last < freq * 3600:
                            continue
                        agent = agent_manager.get_agent(row[0])
                        if not agent:
                            continue
                        # Pick a random group
                        async with db.execute(
                            "SELECT group_id FROM group_members WHERE user_id=? ORDER BY RANDOM() LIMIT 1",
                            (row[0],)
                        ) as gc:
                            g_row = await gc.fetchone()
                            if not g_row:
                                continue
                            group_id = g_row[0]
                        topics = cfg.get("topics", [])
                        topic = topics[int(_time.time()) % len(topics)] if topics else "跟家人打个招呼"
                        try:
                            reply = await agent.think(f"[{topic}]", "系统", True)
                            if reply:
                                from .models.database import gen_id as _gid
                                msg_id = _gid()
                                ts = _time.time()
                                # 尝试生成语音回复
                                voice_url = ""
                                try:
                                    voice_profile = await voice_profile_manager.get_agent_voice(row[0])
                                    if voice_profile:
                                        tts_path = await voice_profile_manager.synthesize(
                                            reply, profile_id=voice_profile["id"]
                                        )
                                        if tts_path:
                                            voice_url = f"/api/voice/{os.path.basename(tts_path)}"
                                except Exception as ve:
                                    logger.debug(f"语音合成跳过: {ve}")
                                msg_type = "voice" if voice_url else "text"
                                await db.execute(
                                    "INSERT INTO messages (id,group_id,sender_id,sender_name,content,msg_type,media_url,is_agent,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                                    (msg_id, group_id, row[0], row[1], reply, msg_type, voice_url, 1, ts)
                                )
                                await db.execute(
                                    "UPDATE agents SET proactive_config=json_set(proactive_config,'$.last_proactive',?) WHERE id=?",
                                    (ts, row[0])
                                )
                                await db.commit()
                                await ws_manager.broadcast_to_group(group_id, {
                                    "type": "message",
                                    "data": {
                                        "id": msg_id, "group_id": g_row[0],
                                        "sender_id": row[0], "sender_name": row[1],
                                        "content": reply, "msg_type": "text",
                                        "is_agent": True, "created_at": ts,
                                        "reactions": [],
                                    }
                                })
                        except Exception as e:
                            logger.error(f"主动发言失败 [{row[1]}]: {e}")
            finally:
                await db.close()
        except Exception as e:
            logger.error(f"主动发言调度器异常: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_manager
    logger.info("🚀 FamilyChat v2.0 启动中...")
    await init_db()
    logger.info("✅ 数据库初始化完成")

    db = await get_db()
    llm_config = {
        "provider": os.getenv("LLM_PROVIDER", "deepseek"),
        "api_key": os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", "")),
        "base_url": os.getenv("LLM_BASE_URL", ""),
        "model": os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.8")),
    }
    agent_manager = AgentManager(db, llm_config)
    await agent_manager.load_agents()
    await ensure_defaults(db, agent_manager)
    # Don't close db — agent_manager holds the reference

    # 初始化语音音色管理器
    global voice_profile_manager, refinement_service
    voice_profile_manager = VoiceProfileManager(db)
    await voice_profile_manager.init_db()
    logger.info("✅ 语音音色管理器就绪")

    # 初始化多模态炼化服务
    refinement_service = MultiModalRefinement(db, llm_config)
    await refinement_service.init_essence_db()
    logger.info("✅ 多维炼化引擎就绪（七层本质模型）")

    logger.info("=" * 50)
    logger.info("🏠 FamilyChat v2.0 已启动！")
    logger.info("🌐 访问 http://localhost:8000")
    logger.info("=" * 50)

    # Start proactive speaking scheduler
    proactive_task = asyncio.create_task(_proactive_scheduler())

    yield

    proactive_task.cancel()
    from .models.database import close_db
    await close_db()
    logger.info("👋 FamilyChat 关闭")


app = FastAPI(title="FamilyChat", lifespan=lifespan)

# Security middleware - CORS
# 从环境变量读取允许的域名列表，逗号分隔
_cors_origins_str = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_str.split(",") if o.strip()] if _cors_origins_str else []
if not _cors_origins:
    logger.warning("⚠️  CORS_ORIGINS 未设置，默认仅允许 localhost")
    _cors_origins = ["http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Simple rate limiter
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 120    # requests per window

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now_ts = _time.time()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    # Clean old entries
    _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if now_ts - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX:
        return JSONResponse({"detail": "请求过于频繁"}, status_code=429)
    _rate_limit_store[client_ip].append(now_ts)
    return await call_next(request)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# 静态文件
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# 注册路由
from .routes import auth, chat, friends, moments, agents, search, notifications, system
from .routes.websocket import websocket_endpoint as ws_endpoint
from .routes.voice_profiles import router as voice_profiles_router
from .routes.refinement import router as refinement_router
app.add_api_websocket_route("/ws", ws_endpoint)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(friends.router)
app.include_router(moments.router)
app.include_router(agents.router)
app.include_router(search.router)
app.include_router(notifications.router)
app.include_router(system.router)
app.include_router(voice_profiles_router)
app.include_router(refinement_router)


async def ensure_defaults(db, agent_mgr: AgentManager):
    """确保默认数据存在"""
    async with db.execute("SELECT id FROM groups WHERE id='family_default'") as cursor:
        if not await cursor.fetchone():
            await db.execute(
                "INSERT INTO groups (id,name,owner_id,description,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                ("family_default", "我们的家庭", "system", "家庭聊天群", now(), now())
            )
            await db.commit()

    if not agent_mgr.agents:
        default_agents = [
            {
                "id": "agent_dad", "name": "爸爸", "avatar": "👨",
                "backstory": "退休教师，教了一辈子语文。喜欢钓鱼、看历史书、下棋。稳重有耐心，偶尔幽默。",
                "speaking_style": "说话稳重，偶尔用成语。关心人时绕弯子。高兴时发哈哈或😂。",
                "traits": ["稳重有耐心", "喜欢讲道理", "偶尔幽默", "关心子女但不善表达"],
                "interests": ["钓鱼", "中国历史", "下象棋", "看新闻"],
                "catchphrases": ["这个嘛，要从长计议", "我跟你说啊", "年轻人不懂", "想当年..."],
                "relationships": {
                    "mom": {"name": "妈妈", "relation": "老伴", "desc": "结婚35年"},
                    "son": {"name": "儿子", "relation": "儿子", "desc": "在北京工作"},
                },
            },
            {
                "id": "agent_mom", "name": "妈妈", "avatar": "👩",
                "backstory": "退休护士，热心肠，是家里的大管家。做饭特别好吃，爱唠叨但都是为了家人好。",
                "speaking_style": "说话亲切，爱用语气词（呀、呢、嘛）。关心人时特别温柔。唠叨时话比较多。",
                "traits": ["热心肠", "爱唠叨", "做饭好吃", "操心命"],
                "interests": ["做饭", "广场舞", "养生", "看家庭剧"],
                "catchphrases": ["多吃点", "注意身体", "别熬夜", "妈给你做了好吃的"],
                "relationships": {
                    "dad": {"name": "爸爸", "relation": "老伴", "desc": "结婚35年"},
                    "son": {"name": "儿子", "relation": "儿子", "desc": "最挂念的人"},
                },
            },
            {
                "id": "agent_grandma", "name": "奶奶", "avatar": "👵",
                "backstory": "80岁，身体还行，最喜欢孙子孙女。经历过很多事，看问题很透彻。",
                "speaking_style": "说话慢悠悠，爱讲过去的事。对晚辈特别慈祥。偶尔有点耳背（假装没听到）。",
                "traits": ["慈祥", "爱讲古", "有点耳背", "最疼孙子"],
                "interests": ["听戏曲", "养花", "晒太阳", "回忆过去"],
                "catchphrases": ["想当年啊", "你们年轻人", "奶奶年纪大了", "乖孙"],
                "relationships": {
                    "dad": {"name": "爸爸", "relation": "儿子", "desc": "大儿子"},
                    "mom": {"name": "妈妈", "relation": "儿媳妇", "desc": "好儿媳"},
                },
            },
        ]
        for cfg in default_agents:
            await agent_mgr.create_agent(cfg, _db=db)
        for cfg in default_agents:
            await db.execute(
                "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
                ("family_default", cfg["id"], "agent", now())
            )
        await db.commit()


# ==================== LLM 配置 ====================

class LLMConfigReq(BaseModel):
    provider: str = ""
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.8


@app.post("/api/config/llm")
async def update_llm_config(req: LLMConfigReq, user=Depends(get_current_user)):
    global agent_manager, refinement_service
    new_config = {}
    if req.provider:
        new_config["provider"] = req.provider
    api_key = (req.api_key or "").strip()
    if api_key and "***" not in api_key:
        new_config["api_key"] = api_key
    elif api_key:
        logger.warning("已忽略脱敏 API Key，避免覆盖真实 LLM 配置")
    if req.base_url:
        new_config["base_url"] = req.base_url.strip()
    if req.model:
        new_config["model"] = req.model.strip()
    if req.temperature:
        new_config["temperature"] = req.temperature
    agent_manager.llm_config.update(new_config)
    if refinement_service:
        refinement_service.llm_config.update(new_config)
    for agent in agent_manager.agents.values():
        agent.llm_config = agent_manager.llm_config
    return {"status": "ok"}


@app.get("/api/config/llm")
async def get_llm_config(user=Depends(get_current_user)):
    cfg = agent_manager.llm_config.copy()
    api_key = cfg.get("api_key") or ""
    cfg["api_key_configured"] = bool(api_key)
    cfg["api_key_preview"] = api_key[:8] + "***" if api_key else ""
    cfg["api_key"] = ""
    return cfg


@app.get("/api/config/providers")
async def list_providers():
    return {
        "providers": [
            {"id": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini"], "base_url": "https://api.openai.com/v1"},
            {"id": "deepseek", "name": "DeepSeek", "models": ["deepseek-v4-flash", "deepseek-v4-pro"], "base_url": "https://api.deepseek.com"},
            {"id": "zhipu", "name": "智谱AI", "models": ["glm-4", "glm-4-flash"], "base_url": "https://open.bigmodel.cn/api/paas/v4"},
            {"id": "qwen", "name": "通义千问", "models": ["qwen-max", "qwen-plus"], "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
            {"id": "local", "name": "本地模型", "models": ["ollama/any"], "base_url": "http://localhost:11434/v1"},
        ]
    }


# ==================== TTS ====================

AGENT_VOICES = {
    "agent_dad": "zh-CN-YunxiNeural",
    "agent_mom": "zh-CN-XiaoxiaoNeural",
    "agent_grandma": "zh-CN-XiaoyiNeural",
}
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


@app.post("/api/tts")
async def text_to_speech(text: str, voice: str = "", user=Depends(get_current_user)):
    try:
        import edge_tts
        voice_name = voice or DEFAULT_VOICE
        output_path = f"data/voices/{gen_id()}.mp3"
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(output_path)
        return FileResponse(output_path, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(500, f"语音合成失败: {e}")


@app.post("/api/voice/upload")
async def upload_voice(file: UploadFile = File(...), user=Depends(get_current_user)):
    # 校验文件类型
    allowed_types = {"audio/webm", "audio/mp3", "audio/mpeg", "audio/wav", "audio/ogg", "audio/x-m4a", "video/webm"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(400, f"不支持的文件类型: {file.content_type}，请上传音频文件")
    content = await file.read()
    # 校验文件大小 (10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "语音文件不能超过10MB")
    if len(content) < 100:
        raise HTTPException(400, "文件内容过小")
    file_id = gen_id()
    ext = Path(file.filename).suffix if file.filename else ".webm"
    # 限制扩展名
    allowed_exts = {".webm", ".mp3", ".wav", ".ogg", ".m4a"}
    if ext.lower() not in allowed_exts:
        ext = ".webm"
    filepath = f"data/voices/{file_id}{ext}"
    with open(filepath, "wb") as f:
        f.write(content)
    return {"id": file_id, "url": f"/api/voice/{file_id}{ext}"}


@app.get("/api/voice/{filename}")
async def get_voice(filename: str):
    # 防止路径遍历攻击
    safe_name = Path(filename).name  # 剥离目录部分
    if not safe_name or safe_name.startswith("."):
        raise HTTPException(400, "无效的文件名")
    filepath = Path("data/voices") / safe_name
    if not filepath.exists():
        raise HTTPException(404)
    return FileResponse(str(filepath), media_type="audio/mpeg")


@app.get("/api/voices")
async def list_voices():
    return {
        "voices": [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "gender": "female", "desc": "温柔女声"},
            {"id": "zh-CN-YunxiNeural", "name": "云希", "gender": "male", "desc": "稳重男声"},
            {"id": "zh-CN-XiaoyiNeural", "name": "晓艺", "gender": "female", "desc": "年长女声"},
            {"id": "zh-CN-YunjianNeural", "name": "云健", "gender": "male", "desc": "活力男声"},
            {"id": "zh-CN-XiaochenNeural", "name": "晓辰", "gender": "female", "desc": "甜美女声"},
        ]
    }


async def _generate_agent_voice(agent_id: str, text: str):
    try:
        import edge_tts
        voice = AGENT_VOICES.get(agent_id, DEFAULT_VOICE)
        filename = f"{gen_id()}.mp3"
        filepath = f"data/voices/{filename}"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filepath)
        return f"/api/voice/{filename}"
    except Exception as e:
        logger.error(f"语音生成失败: {e}")
        return None


# ==================== 系统状态 ====================

@app.get("/api/status")
async def system_status():
    return {
        "status": "running",
        "version": "2.0.0",
        "agents": len(agent_manager.agents) if agent_manager else 0,
        "online": ws_manager.get_online_count(),
    }


# ==================== 前端 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = frontend_dir / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>FamilyChat</h1><p>前端文件未找到</p>")
