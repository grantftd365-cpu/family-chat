"""FamilyChat - FastAPI 主应用 v2.0"""
import asyncio
import json
import os
import random
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from loguru import logger

from .models.database import init_db, get_db, gen_id, now
from .core.auth import hash_password, verify_password, create_token, get_current_user, get_ws_user
from .core.websocket import ws_manager
from .agents.core import AgentManager

# ==================== Lifespan ====================

agent_manager: AgentManager = None


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
        "model": os.getenv("LLM_MODEL", "deepseek-chat"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.8")),
    }
    agent_manager = AgentManager(db, llm_config)
    await agent_manager.load_agents()
    await ensure_defaults(db, agent_manager)
    await db.close()

    logger.info("=" * 50)
    logger.info("🏠 FamilyChat v2.0 已启动！")
    logger.info("🌐 访问 http://localhost:8000")
    logger.info("=" * 50)
    yield
    logger.info("👋 FamilyChat 关闭")


app = FastAPI(title="FamilyChat", lifespan=lifespan)

# 静态文件
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# 注册路由
from .routes import auth, chat, friends, moments, agents, search, notifications
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(friends.router)
app.include_router(moments.router)
app.include_router(agents.router)
app.include_router(search.router)
app.include_router(notifications.router)


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
            await agent_mgr.create_agent(cfg)
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
    global agent_manager
    new_config = {}
    if req.provider:
        new_config["provider"] = req.provider
    if req.api_key:
        new_config["api_key"] = req.api_key
    if req.base_url:
        new_config["base_url"] = req.base_url
    if req.model:
        new_config["model"] = req.model
    if req.temperature:
        new_config["temperature"] = req.temperature
    agent_manager.llm_config.update(new_config)
    for agent in agent_manager.agents.values():
        agent.llm_config = agent_manager.llm_config
    return {"status": "ok"}


@app.get("/api/config/llm")
async def get_llm_config(user=Depends(get_current_user)):
    cfg = agent_manager.llm_config.copy()
    if cfg.get("api_key"):
        cfg["api_key"] = cfg["api_key"][:8] + "***"
    return cfg


@app.get("/api/config/providers")
async def list_providers():
    return {
        "providers": [
            {"id": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini"], "base_url": "https://api.openai.com/v1"},
            {"id": "deepseek", "name": "DeepSeek", "models": ["deepseek-chat", "deepseek-reasoner"], "base_url": "https://api.deepseek.com/v1"},
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
    file_id = gen_id()
    ext = Path(file.filename).suffix or ".webm"
    filepath = f"data/voices/{file_id}{ext}"
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return {"id": file_id, "url": f"/api/voice/{file_id}{ext}"}


@app.get("/api/voice/{filename}")
async def get_voice(filename: str):
    filepath = f"data/voices/{filename}"
    if not Path(filepath).exists():
        raise HTTPException(404)
    return FileResponse(filepath, media_type="audio/mpeg")


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


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query("")):
    user = await get_ws_user(websocket)
    if not user:
        await websocket.close(code=4001)
        return

    user_id = user["user_id"]
    await ws_manager.connect(user_id, websocket)

    # 更新在线状态
    db = await get_db()
    await db.execute("UPDATE users SET online_status='online', last_seen=? WHERE id=?", (now(), user_id))
    await db.commit()

    try:
        async with db.execute("SELECT group_id FROM group_members WHERE user_id=?", (user_id,)) as c:
            async for row in c:
                await ws_manager.join_group(user_id, row[0])
    finally:
        await db.close()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg.get("type") == "typing":
                    await ws_manager.broadcast_to_group(
                        msg.get("group_id", ""),
                        {"type": "typing", "data": {"user_id": user_id, "user_name": msg.get("name", "")}},
                        exclude_user=user_id
                    )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, websocket)
        db = await get_db()
        await db.execute("UPDATE users SET online_status='offline', last_seen=? WHERE id=?", (now(), user_id))
        await db.commit()
        await db.close()


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
