"""FamilyChat - FastAPI 主应用"""
import asyncio
import json
import os
import time
import uuid
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
    
    logger.info("🚀 FamilyChat 启动中...")
    
    # 初始化数据库
    await init_db()
    logger.info("✅ 数据库初始化完成")
    
    # 初始化 Agent 管理器
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
    
    # 创建默认群和默认 Agent
    await ensure_defaults(db, agent_manager)
    
    logger.info("✅ Agent 系统初始化完成")
    logger.info("=" * 50)
    logger.info("🏠 FamilyChat 已启动！")
    logger.info("🌐 访问 http://localhost:8000")
    logger.info("=" * 50)
    
    yield
    
    logger.info("👋 FamilyChat 关闭")


app = FastAPI(title="FamilyChat", lifespan=lifespan)

# 静态文件
Path("data/uploads").mkdir(parents=True, exist_ok=True)
Path("data/voices").mkdir(parents=True, exist_ok=True)

# 挂载前端
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


# ==================== 辅助函数 ====================

async def ensure_defaults(db, agent_mgr: AgentManager):
    """确保默认数据存在"""
    # 检查是否有默认群
    async with db.execute("SELECT id FROM groups WHERE id='family_default'") as cursor:
        if not await cursor.fetchone():
            await db.execute(
                "INSERT INTO groups (id, name, owner_id, description, created_at) VALUES (?,?,?,?,?)",
                ("family_default", "我们的家庭", "system", "家庭聊天群", now())
            )
            await db.commit()
    
    # 如果没有 Agent，创建示例
    if not agent_mgr.agents:
        default_agents = [
            {
                "id": "agent_dad",
                "name": "爸爸",
                "avatar": "👨",
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
                "id": "agent_mom",
                "name": "妈妈",
                "avatar": "👩",
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
                "id": "agent_grandma",
                "name": "奶奶",
                "avatar": "👵",
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
        
        # 将 Agent 加入默认群
        for cfg in default_agents:
            await db.execute(
                "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
                ("family_default", cfg["id"], "agent", now())
            )
        await db.commit()


# ==================== Pydantic 模型 ====================

class RegisterReq(BaseModel):
    username: str
    password: str
    nickname: str

class LoginReq(BaseModel):
    username: str
    password: str

class CreateGroupReq(BaseModel):
    name: str
    description: str = ""

class SendMessageReq(BaseModel):
    group_id: str
    content: str
    msg_type: str = "text"

class CreateAgentReq(BaseModel):
    name: str
    avatar: str = "🤖"
    backstory: str = ""
    speaking_style: str = ""
    traits: list = []
    interests: list = []
    catchphrases: list = []
    relationships: dict = {}


# ==================== 前端页面 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端页面"""
    html_path = frontend_dir / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>FamilyChat</h1><p>前端文件未找到</p>")


# ==================== 认证 API ====================

@app.post("/api/register")
async def register(req: RegisterReq):
    db = await get_db()
    try:
        # 检查用户名
        async with db.execute("SELECT id FROM users WHERE username=?", (req.username,)) as c:
            if await c.fetchone():
                raise HTTPException(400, "用户名已存在")
        
        user_id = gen_id()
        await db.execute(
            "INSERT INTO users (id, username, nickname, password_hash, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (user_id, req.username, req.nickname, hash_password(req.password), now(), now())
        )
        # 加入默认群
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
            ("family_default", user_id, "member", now())
        )
        await db.commit()
        
        token = create_token(user_id, req.username)
        return {"token": token, "user": {"id": user_id, "username": req.username, "nickname": req.nickname}}
    finally:
        await db.close()


@app.post("/api/login")
async def login(req: LoginReq):
    db = await get_db()
    try:
        async with db.execute("SELECT id, nickname, password_hash FROM users WHERE username=?", (req.username,)) as c:
            row = await c.fetchone()
            if not row or not verify_password(req.password, row[2]):
                raise HTTPException(401, "用户名或密码错误")
        
        token = create_token(row[0], req.username)
        return {"token": token, "user": {"id": row[0], "username": req.username, "nickname": row[1]}}
    finally:
        await db.close()


# ==================== 用户 API ====================

@app.get("/api/me")
async def get_me(user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT id, username, nickname, avatar FROM users WHERE id=?", (user["user_id"],)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "用户不存在")
            return {"id": row[0], "username": row[1], "nickname": row[2], "avatar": row[3] or "😀"}
    finally:
        await db.close()


# ==================== 群组 API ====================

@app.get("/api/groups")
async def list_groups(user=Depends(get_current_user)):
    db = await get_db()
    try:
        groups = []
        async with db.execute("""
            SELECT g.id, g.name, g.avatar, g.description,
                   (SELECT COUNT(*) FROM group_members WHERE group_id=g.id) as member_count,
                   (SELECT content FROM messages WHERE group_id=g.id ORDER BY created_at DESC LIMIT 1) as last_msg,
                   (SELECT created_at FROM messages WHERE group_id=g.id ORDER BY created_at DESC LIMIT 1) as last_time
            FROM groups g
            JOIN group_members gm ON g.id=gm.group_id
            WHERE gm.user_id=?
            ORDER BY last_time DESC
        """, (user["user_id"],)) as cursor:
            async for row in cursor:
                groups.append({
                    "id": row[0], "name": row[1], "avatar": row[2] or "👥",
                    "description": row[3], "member_count": row[4],
                    "last_message": row[5] or "", "last_time": row[6] or 0,
                })
        return groups
    finally:
        await db.close()


@app.post("/api/groups")
async def create_group(req: CreateGroupReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        group_id = gen_id()
        await db.execute(
            "INSERT INTO groups (id, name, owner_id, description, created_at) VALUES (?,?,?,?,?)",
            (group_id, req.name, user["user_id"], req.description, now())
        )
        await db.execute(
            "INSERT INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
            (group_id, user["user_id"], "owner", now())
        )
        # 自动加入所有 Agent
        for agent_id in agent_manager.agents:
            await db.execute(
                "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
                (group_id, agent_id, "agent", now())
            )
        await db.commit()
        return {"id": group_id, "name": req.name}
    finally:
        await db.close()


@app.get("/api/groups/{group_id}/members")
async def group_members(group_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        members = []
        async with db.execute("""
            SELECT gm.user_id, gm.role,
                   COALESCE(u.nickname, a.name) as name,
                   COALESCE(u.avatar, a.avatar) as avatar
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id=u.id
            LEFT JOIN agents a ON gm.user_id=a.id
            WHERE gm.group_id=?
        """, (group_id,)) as cursor:
            async for row in cursor:
                members.append({
                    "id": row[0], "role": row[1],
                    "name": row[2] or row[0], "avatar": row[3] or "😀",
                    "is_agent": row[1] == "agent",
                })
        return members
    finally:
        await db.close()


# ==================== 消息 API ====================

@app.get("/api/messages/{group_id}")
async def get_messages(group_id: str, limit: int = 50, before: float = 0, user=Depends(get_current_user)):
    db = await get_db()
    try:
        messages = []
        if before > 0:
            async with db.execute(
                "SELECT id, group_id, sender_id, sender_name, content, msg_type, is_agent, created_at FROM messages WHERE group_id=? AND created_at<? ORDER BY created_at DESC LIMIT ?",
                (group_id, before, limit)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT id, group_id, sender_id, sender_name, content, msg_type, is_agent, created_at FROM messages WHERE group_id=? ORDER BY created_at DESC LIMIT ?",
                (group_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
        
        for row in reversed(rows):
            messages.append({
                "id": row[0], "group_id": row[1], "sender_id": row[2],
                "sender_name": row[3], "content": row[4], "msg_type": row[5],
                "is_agent": bool(row[6]), "created_at": row[7],
            })
        return messages
    finally:
        await db.close()


@app.post("/api/messages")
async def send_message(req: SendMessageReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        # 获取用户昵称
        async with db.execute("SELECT nickname FROM users WHERE id=?", (user["user_id"],)) as c:
            row = await c.fetchone()
            nickname = row[0] if row else user["username"]

        msg_id = gen_id()
        ts = now()
        
        await db.execute(
            "INSERT INTO messages (id, group_id, sender_id, sender_name, content, msg_type, is_agent, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (msg_id, req.group_id, user["user_id"], nickname, req.content, req.msg_type, 0, ts)
        )
        await db.commit()

        # 广播给群内其他用户
        msg_data = {
            "type": "message",
            "data": {
                "id": msg_id, "group_id": req.group_id,
                "sender_id": user["user_id"], "sender_name": nickname,
                "content": req.content, "msg_type": req.msg_type,
                "is_agent": False, "created_at": ts,
            }
        }
        await ws_manager.broadcast_to_group(req.group_id, msg_data, exclude_user=user["user_id"])

        # 触发 Agent 回复（异步）
        asyncio.create_task(_trigger_agent_replies(req.group_id, user["user_id"], nickname, req.content, db))

        return {"id": msg_id, "created_at": ts}
    finally:
        await db.close()


async def _trigger_agent_replies(group_id: str, sender_id: str, sender_name: str, content: str, db):
    """触发 Agent 回复"""
    try:
        replies = await agent_manager.handle_group_message(group_id, sender_id, sender_name, content)
        
        for reply in replies:
            agent_id = reply["agent_id"]
            msg_id = gen_id()
            ts = now()
            
            # 生成 Agent 语音（30% 概率发语音）
            voice_url = None
            if random.random() < 0.3 and len(reply["content"]) > 5:
                voice_url = await _generate_agent_voice(agent_id, reply["content"])
            
            msg_type = "voice" if voice_url else reply["msg_type"]
            
            await db.execute(
                "INSERT INTO messages (id, group_id, sender_id, sender_name, content, msg_type, is_agent, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (msg_id, group_id, agent_id, reply["agent_name"], reply["content"], msg_type, 1, ts)
            )
            await db.commit()
            
            # 广播
            msg_data = {
                "type": "message",
                "data": {
                    "id": msg_id, "group_id": group_id,
                    "sender_id": agent_id, "sender_name": reply["agent_name"],
                    "content": reply["content"], "msg_type": msg_type,
                    "is_agent": True, "created_at": ts,
                    "agent_avatar": reply.get("agent_avatar", "🤖"),
                    "voice_url": voice_url,
                }
            }
            await ws_manager.broadcast_to_group(group_id, msg_data)
            
    except Exception as e:
        logger.error(f"Agent 回复异常: {e}")


# ==================== Agent API ====================

@app.get("/api/agents")
async def list_agents(user=Depends(get_current_user)):
    return agent_manager.get_all()


@app.post("/api/agents")
async def create_agent(req: CreateAgentReq, user=Depends(get_current_user)):
    agent_id = await agent_manager.create_agent(req.dict())
    # 加入默认群
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
        ("family_default", agent_id, "agent", now())
    )
    await db.commit()
    await db.close()
    return {"id": agent_id, "name": req.name}


@app.get("/api/agents/{agent_id}/memories")
async def agent_memories(agent_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        memories = []
        async with db.execute(
            "SELECT id, content, importance, memory_type, created_at FROM agent_memories WHERE agent_id=? ORDER BY created_at DESC LIMIT 50",
            (agent_id,)
        ) as cursor:
            async for row in cursor:
                memories.append({
                    "id": row[0], "content": row[1], "importance": row[2],
                    "type": row[3], "created_at": row[4],
                })
        return memories
    finally:
        await db.close()


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query("")):
    user = await get_ws_user(websocket)
    if not user:
        await websocket.close(code=4001)
        return
    
    user_id = user["user_id"]
    await ws_manager.connect(user_id, websocket)
    
    # 自动加入所有群
    db = await get_db()
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
                # 处理不同类型的消息
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, websocket)


# ==================== 语音 API ====================

# Agent 语音映射
AGENT_VOICES = {
    "agent_dad": "zh-CN-YunxiNeural",      # 男声-稳重
    "agent_mom": "zh-CN-XiaoxiaoNeural",    # 女声-温柔
    "agent_grandma": "zh-CN-XiaoyiNeural",  # 女声-年长
}
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


@app.post("/api/tts")
async def text_to_speech(text: str, voice: str = "", user=Depends(get_current_user)):
    """文字转语音"""
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
    """上传语音消息"""
    file_id = gen_id()
    ext = Path(file.filename).suffix or ".webm"
    filepath = f"data/voices/{file_id}{ext}"
    
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    return {"id": file_id, "url": f"/api/voice/{file_id}{ext}"}


@app.get("/api/voice/{filename}")
async def get_voice(filename: str):
    """获取语音文件"""
    filepath = f"data/voices/{filename}"
    if not Path(filepath).exists():
        raise HTTPException(404, "语音文件不存在")
    return FileResponse(filepath, media_type="audio/mpeg")


async def _generate_agent_voice(agent_id: str, text: str) -> Optional[str]:
    """为 Agent 生成语音，返回文件路径"""
    try:
        import edge_tts
        
        voice = AGENT_VOICES.get(agent_id, DEFAULT_VOICE)
        filename = f"{gen_id()}.mp3"
        filepath = f"data/voices/{filename}"
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filepath)
        
        return f"/api/voice/{filename}"
    except Exception as e:
        logger.error(f"Agent 语音生成失败: {e}")
        return None


# ==================== 记忆 API ====================

@app.get("/api/memories/search")
async def search_memories(q: str, agent_id: str = "", user=Depends(get_current_user)):
    """搜索 Agent 记忆"""
    db = await get_db()
    try:
        results = []
        if agent_id:
            async with db.execute(
                "SELECT id, agent_id, content, importance, memory_type, created_at FROM agent_memories WHERE agent_id=? AND content LIKE ? ORDER BY importance DESC LIMIT 20",
                (agent_id, f"%{q}%")
            ) as cursor:
                async for row in cursor:
                    results.append({
                        "id": row[0], "agent_id": row[1], "content": row[2],
                        "importance": row[3], "type": row[4], "created_at": row[5],
                    })
        else:
            async with db.execute(
                "SELECT id, agent_id, content, importance, memory_type, created_at FROM agent_memories WHERE content LIKE ? ORDER BY importance DESC LIMIT 20",
                (f"%{q}%",)
            ) as cursor:
                async for row in cursor:
                    results.append({
                        "id": row[0], "agent_id": row[1], "content": row[2],
                        "importance": row[3], "type": row[4], "created_at": row[5],
                    })
        return results
    finally:
        await db.close()


@app.post("/api/memories")
async def add_memory(agent_id: str, content: str, importance: float = 0.7, user=Depends(get_current_user)):
    """手动添加 Agent 记忆"""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO agent_memories (id, agent_id, content, importance, memory_type, metadata, created_at) VALUES (?,?,?,?,?,?,?)",
            (gen_id(), agent_id, content, importance, "long", "{}", now())
        )
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


# ==================== 系统 API ====================

@app.get("/api/status")
async def system_status():
    return {
        "status": "running",
        "agents": len(agent_manager.agents) if agent_manager else 0,
        "online": ws_manager.get_online_count(),
        "version": "1.0.0",
    }


@app.get("/api/voices")
async def list_voices():
    """列出可用语音"""
    return {
        "voices": [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "gender": "female", "desc": "温柔女声"},
            {"id": "zh-CN-YunxiNeural", "name": "云希", "gender": "male", "desc": "稳重男声"},
            {"id": "zh-CN-XiaoyiNeural", "name": "晓艺", "gender": "female", "desc": "年长女声"},
            {"id": "zh-CN-YunjianNeural", "name": "云健", "gender": "male", "desc": "活力男声"},
            {"id": "zh-CN-XiaochenNeural", "name": "晓辰", "gender": "female", "desc": "甜美女声"},
        ]
    }
