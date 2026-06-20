"""FamilyChat - FastAPI 主应用 (v2 十轮优化版)"""
import asyncio
import json
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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

    logger.info("🚀 FamilyChat v2 启动中...")

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

    logger.info("✅ FamilyChat v2 已就绪！")

    yield

    logger.info("👋 FamilyChat 关闭")


app = FastAPI(title="FamilyChat", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path("data/uploads").mkdir(parents=True, exist_ok=True)
Path("data/voices").mkdir(parents=True, exist_ok=True)

frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


# ==================== 辅助 ====================

async def ensure_defaults(db, agent_mgr: AgentManager):
    async with db.execute("SELECT id FROM groups WHERE id='family_default'") as cursor:
        if not await cursor.fetchone():
            await db.execute(
                "INSERT INTO groups (id, name, owner_id, description, created_at) VALUES (?,?,?,?,?)",
                ("family_default", "我们的家庭", "system", "家庭聊天群", now())
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
                "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
                ("family_default", cfg["id"], "agent", now())
            )
        await db.commit()


def _get_agent_avatar(agent_id: str) -> str:
    if agent_manager and agent_id in agent_manager.agents:
        return agent_manager.agents[agent_id].personality.avatar
    return "🤖"


# ==================== Pydantic ====================

class RegisterReq(BaseModel):
    email: str
    username: str
    password: str
    nickname: str
    avatar: str = "😀"
    role_in_family: str = ""

class LoginReq(BaseModel):
    email: str
    password: str

class CreateGroupReq(BaseModel):
    name: str
    description: str = ""
    avatar: str = "👥"

class SendMessageReq(BaseModel):
    group_id: str
    content: str
    msg_type: str = "text"
    voice_url: str = ""
    reply_to: str = ""
    media_url: str = ""

class CreateAgentReq(BaseModel):
    name: str
    avatar: str = "🤖"
    backstory: str = ""
    speaking_style: str = ""
    traits: list = []
    interests: list = []
    catchphrases: list = []
    relationships: dict = {}

class FriendRequestReq(BaseModel):
    to_user_id: str
    message: str = ""

class UpdateProfileReq(BaseModel):
    nickname: str = ""
    avatar: str = ""
    phone: str = ""
    role_in_family: str = ""

class GroupNoticeReq(BaseModel):
    content: str

class MuteMemberReq(BaseModel):
    muted: int = 1  # 1=禁言, 0=解除

class ForwardMsgReq(BaseModel):
    message_id: str
    target_group_id: str

class RecallMsgReq(BaseModel):
    message_id: str


# ==================== 前端 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = frontend_dir / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>FamilyChat</h1>")


# ==================== 认证 ====================

@app.post("/api/register")
async def register(req: RegisterReq):
    db = await get_db()
    try:
        async with db.execute("SELECT id FROM users WHERE email=?", (req.email,)) as c:
            if await c.fetchone():
                raise HTTPException(400, "该邮箱已注册")
        async with db.execute("SELECT id FROM users WHERE username=?", (req.username,)) as c:
            if await c.fetchone():
                raise HTTPException(400, "用户名已存在")

        user_id = gen_id()
        ts = now()
        await db.execute(
            "INSERT INTO users (id, email, username, nickname, password_hash, avatar, role, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, req.email, req.username, req.nickname,
             hash_password(req.password), req.avatar, "member", ts, ts)
        )

        agent_id = f"agent_{user_id}"
        agent_config = {
            "id": agent_id, "user_id": user_id,
            "name": req.nickname, "avatar": req.avatar,
            "role_in_family": req.role_in_family,
            "backstory": f"{req.nickname}的数字分身",
            "speaking_style": "待炼化",
            "traits": [], "interests": [], "catchphrases": [],
        }
        await agent_manager.create_agent(agent_config)
        await db.execute("UPDATE users SET agent_id=? WHERE id=?", (agent_id, user_id))

        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
            ("family_default", user_id, "member", ts)
        )
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
            ("family_default", agent_id, "agent", ts)
        )

        # 初始化未读计数
        async with db.execute("SELECT id FROM groups") as cur:
            async for row in cur:
                await db.execute(
                    "INSERT OR IGNORE INTO conv_members (conv_id, user_id, role, unread_count, last_read_at, joined_at) VALUES (?,?,?,?,?,?)",
                    (row[0], user_id, "member", 0, ts, ts)
                )

        await db.commit()
        token = create_token(user_id, req.email)
        return {
            "token": token,
            "user": {"id": user_id, "email": req.email, "username": req.username, "nickname": req.nickname, "avatar": req.avatar, "agent_id": agent_id},
        }
    finally:
        await db.close()


@app.post("/api/login")
async def login(req: LoginReq):
    db = await get_db()
    try:
        async with db.execute("SELECT id, username, nickname, avatar, agent_id, password_hash FROM users WHERE email=?", (req.email,)) as c:
            row = await c.fetchone()
            if not row or not verify_password(req.password, row[5]):
                raise HTTPException(401, "邮箱或密码错误")

        # 更新在线状态
        await db.execute("UPDATE users SET status='online' WHERE id=?", (row[0],))
        await db.commit()

        token = create_token(row[0], req.email)
        return {
            "token": token,
            "user": {
                "id": row[0], "email": req.email,
                "username": row[1], "nickname": row[2],
                "avatar": row[3] or "😀", "agent_id": row[4] or "",
            }
        }
    finally:
        await db.close()


@app.post("/api/logout")
async def logout(user=Depends(get_current_user)):
    db = await get_db()
    await db.execute("UPDATE users SET status='offline' WHERE id=?", (user["user_id"],))
    await db.commit()
    await db.close()
    return {"status": "ok"}


# ==================== 用户 ====================

@app.get("/api/me")
async def get_me(user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT id, username, nickname, avatar, phone, role, agent_id, status FROM users WHERE id=?", (user["user_id"],)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "用户不存在")
            return {
                "id": row[0], "username": row[1], "nickname": row[2],
                "avatar": row[3] or "😀", "phone": row[4] or "",
                "role": row[5], "agent_id": row[6] or "", "status": row[7] or "offline",
            }
    finally:
        await db.close()


@app.put("/api/me")
async def update_me(req: UpdateProfileReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        updates = []
        params = []
        if req.nickname:
            updates.append("nickname=?"); params.append(req.nickname)
        if req.avatar:
            updates.append("avatar=?"); params.append(req.avatar)
        if req.phone:
            updates.append("phone=?"); params.append(req.phone)
        if not updates:
            return {"status": "no_change"}
        params.append(now())
        params.append(user["user_id"])
        await db.execute(f"UPDATE users SET {','.join(updates)}, updated_at=? WHERE id=?", params)
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@app.get("/api/users/{user_id}")
async def get_user_profile(user_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT id, username, nickname, avatar, role, status FROM users WHERE id=?", (user_id,)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "用户不存在")
            # 检查是否好友
        async with db.execute("SELECT status FROM friendships WHERE user_id=? AND friend_id=?", (user["user_id"], user_id)) as c:
            fr = await c.fetchone()
            friend_status = fr[0] if fr else "none"
        return {
            "id": row[0], "username": row[1], "nickname": row[2],
            "avatar": row[3] or "😀", "role": row[4], "status": row[5] or "offline",
            "friend_status": friend_status,
        }
    finally:
        await db.close()


@app.get("/api/users/search/{keyword}")
async def search_users(keyword: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        results = []
        async with db.execute(
            "SELECT id, username, nickname, avatar FROM users WHERE (username LIKE ? OR nickname LIKE ? OR email LIKE ?) AND id!=? LIMIT 20",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", user["user_id"])
        ) as c:
            async for row in c:
                results.append({"id": row[0], "username": row[1], "nickname": row[2], "avatar": row[3] or "😀"})
        return results
    finally:
        await db.close()


# ==================== 好友系统 ====================

@app.post("/api/friends/request")
async def send_friend_request(req: FriendRequestReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        uid = user["user_id"]
        if uid == req.to_user_id:
            raise HTTPException(400, "不能添加自己为好友")

        # 检查是否已是好友
        async with db.execute("SELECT status FROM friendships WHERE user_id=? AND friend_id=?", (uid, req.to_user_id)) as c:
            if await c.fetchone():
                raise HTTPException(400, "已经是好友了")

        # 检查是否已有待处理请求
        async with db.execute("SELECT id FROM friend_requests WHERE from_user_id=? AND to_user_id=? AND status='pending'", (uid, req.to_user_id)) as c:
            if await c.fetchone():
                raise HTTPException(400, "已发送过请求，请等待对方处理")

        rid = gen_id()
        await db.execute(
            "INSERT INTO friend_requests (id, from_user_id, to_user_id, message, status, created_at) VALUES (?,?,?,?,?,?)",
            (rid, uid, req.to_user_id, req.message, "pending", now())
        )
        await db.commit()

        # 通知对方
        await ws_manager.send_to_user(req.to_user_id, {
            "type": "friend_request",
            "data": {"id": rid, "from_user_id": uid, "message": req.message}
        })

        return {"id": rid, "status": "sent"}
    finally:
        await db.close()


@app.get("/api/friends/requests")
async def list_friend_requests(user=Depends(get_current_user)):
    db = await get_db()
    try:
        results = []
        async with db.execute("""
            SELECT fr.id, fr.from_user_id, fr.message, fr.created_at, fr.status,
                   u.nickname, u.avatar, u.username
            FROM friend_requests fr
            JOIN users u ON fr.from_user_id=u.id
            WHERE fr.to_user_id=? AND fr.status='pending'
            ORDER BY fr.created_at DESC
        """, (user["user_id"],)) as c:
            async for row in c:
                results.append({
                    "id": row[0], "from_user_id": row[1], "message": row[2],
                    "created_at": row[3], "status": row[4],
                    "nickname": row[5], "avatar": row[6] or "😀", "username": row[7],
                })
        return results
    finally:
        await db.close()


@app.post("/api/friends/requests/{request_id}/accept")
async def accept_friend_request(request_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        uid = user["user_id"]
        async with db.execute("SELECT from_user_id, to_user_id FROM friend_requests WHERE id=? AND to_user_id=? AND status='pending'", (request_id, uid)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "请求不存在或已处理")

        from_uid = row[0]
        ts = now()

        # 双向好友关系
        await db.execute("INSERT OR IGNORE INTO friendships (user_id, friend_id, status, created_at) VALUES (?,?,?,?)", (uid, from_uid, "accepted", ts))
        await db.execute("INSERT OR IGNORE INTO friendships (user_id, friend_id, status, created_at) VALUES (?,?,?,?)", (from_uid, uid, "accepted", ts))
        await db.execute("UPDATE friend_requests SET status='accepted' WHERE id=?", (request_id,))

        # 自动创建私聊会话
        conv_id = _private_conv_id(uid, from_uid)
        async with db.execute("SELECT id FROM conversations WHERE id=?", (conv_id,)) as c:
            if not await c.fetchone():
                await db.execute("INSERT INTO conversations (id, conv_type, created_at) VALUES (?,?,?)", (conv_id, "private", ts))
                await db.execute("INSERT OR IGNORE INTO conv_members (conv_id, user_id, role, joined_at) VALUES (?,?,?,?)", (conv_id, uid, "member", ts))
                await db.execute("INSERT OR IGNORE INTO conv_members (conv_id, user_id, role, joined_at) VALUES (?,?,?,?)", (conv_id, from_uid, "member", ts))

        await db.commit()

        # 通知对方
        await ws_manager.send_to_user(from_uid, {
            "type": "friend_accepted",
            "data": {"friend_id": uid, "conv_id": conv_id}
        })

        return {"status": "ok", "conv_id": conv_id}
    finally:
        await db.close()


@app.post("/api/friends/requests/{request_id}/reject")
async def reject_friend_request(request_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("UPDATE friend_requests SET status='rejected' WHERE id=? AND to_user_id=?", (request_id, user["user_id"]))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@app.get("/api/friends")
async def list_friends(user=Depends(get_current_user)):
    db = await get_db()
    try:
        friends = []
        async with db.execute("""
            SELECT f.friend_id, u.nickname, u.avatar, u.username, u.status, u.agent_id
            FROM friendships f
            JOIN users u ON f.friend_id=u.id
            WHERE f.user_id=? AND f.status='accepted'
            ORDER BY u.nickname
        """, (user["user_id"],)) as c:
            async for row in c:
                friends.append({
                    "id": row[0], "nickname": row[1], "avatar": row[2] or "😀",
                    "username": row[3], "status": row[4] or "offline", "agent_id": row[5] or "",
                })
        return friends
    finally:
        await db.close()


@app.delete("/api/friends/{friend_id}")
async def delete_friend(friend_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        uid = user["user_id"]
        await db.execute("DELETE FROM friendships WHERE user_id=? AND friend_id=?", (uid, friend_id))
        await db.execute("DELETE FROM friendships WHERE user_id=? AND friend_id=?", (friend_id, uid))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


def _private_conv_id(uid1: str, uid2: str) -> str:
    """生成确定性私聊会话ID"""
    parts = sorted([uid1, uid2])
    return f"pv_{parts[0]}_{parts[1]}"


# ==================== 会话系统（统一私聊+群聊） ====================

@app.get("/api/conversations")
async def list_conversations(user=Depends(get_current_user)):
    """获取所有会话列表（含未读数）"""
    db = await get_db()
    try:
        convs = []
        uid = user["user_id"]

        # 群聊会话
        async with db.execute("""
            SELECT g.id, g.name, g.avatar, g.description,
                   (SELECT COUNT(*) FROM group_members WHERE group_id=g.id) as member_count,
                   (SELECT content FROM messages WHERE group_id=g.id ORDER BY created_at DESC LIMIT 1) as last_msg,
                   (SELECT sender_name FROM messages WHERE group_id=g.id ORDER BY created_at DESC LIMIT 1) as last_sender,
                   (SELECT created_at FROM messages WHERE group_id=g.id ORDER BY created_at DESC LIMIT 1) as last_time,
                   (SELECT msg_type FROM messages WHERE group_id=g.id ORDER BY created_at DESC LIMIT 1) as last_type
            FROM groups g
            JOIN group_members gm ON g.id=gm.group_id
            WHERE gm.user_id=?
            ORDER BY last_time DESC
        """, (uid,)) as cursor:
            async for row in cursor:
                unread = 0
                async with db.execute("SELECT unread_count FROM conv_members WHERE conv_id=? AND user_id=?", (row[0], uid)) as uc:
                    ur = await uc.fetchone()
                    if ur: unread = ur[0]

                convs.append({
                    "id": row[0], "name": row[1], "avatar": row[2] or "👥",
                    "description": row[3], "member_count": row[4],
                    "last_message": row[5] or "", "last_sender": row[6] or "",
                    "last_time": row[7] or 0, "last_type": row[8] or "text",
                    "conv_type": "group", "unread_count": unread,
                })

        # 私聊会话
        async with db.execute("""
            SELECT c.id, c.created_at,
                   u.id as other_id, u.nickname, u.avatar, u.status,
                   (SELECT content FROM messages WHERE group_id=c.id ORDER BY created_at DESC LIMIT 1) as last_msg,
                   (SELECT created_at FROM messages WHERE group_id=c.id ORDER BY created_at DESC LIMIT 1) as last_time
            FROM conversations c
            JOIN conv_members cm ON c.id=cm.conv_id AND cm.user_id=?
            JOIN conv_members cm2 ON c.id=cm2.conv_id AND cm2.user_id!=?
            JOIN users u ON cm2.user_id=u.id
            WHERE c.conv_type='private'
            ORDER BY last_time DESC
        """, (uid, uid)) as cursor:
            async for row in cursor:
                unread = 0
                async with db.execute("SELECT unread_count FROM conv_members WHERE conv_id=? AND user_id=?", (row[0], uid)) as uc:
                    ur = await uc.fetchone()
                    if ur: unread = ur[0]

                convs.append({
                    "id": row[0], "name": row[3], "avatar": row[4] or "😀",
                    "conv_type": "private", "other_id": row[2],
                    "other_status": row[5] or "offline",
                    "last_message": row[6] or "", "last_time": row[7] or 0,
                    "unread_count": unread,
                })

        convs.sort(key=lambda x: x.get("last_time", 0), reverse=True)
        return convs
    finally:
        await db.close()


@app.post("/api/conversations/private")
async def create_private_conversation(to_user_id: str = Query(...), user=Depends(get_current_user)):
    """创建或获取私聊会话"""
    db = await get_db()
    try:
        uid = user["user_id"]
        conv_id = _private_conv_id(uid, to_user_id)
        ts = now()

        async with db.execute("SELECT id FROM conversations WHERE id=?", (conv_id,)) as c:
            if not await c.fetchone():
                await db.execute("INSERT INTO conversations (id, conv_type, created_at) VALUES (?,?,?)", (conv_id, "private", ts))
                await db.execute("INSERT OR IGNORE INTO conv_members (conv_id, user_id, role, joined_at) VALUES (?,?,?,?)", (conv_id, uid, "member", ts))
                await db.execute("INSERT OR IGNORE INTO conv_members (conv_id, user_id, role, joined_at) VALUES (?,?,?,?)", (conv_id, to_user_id, "member", ts))
                await db.commit()

        return {"id": conv_id, "conv_type": "private"}
    finally:
        await db.close()


# ==================== 群组 ====================

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
        ts = now()
        await db.execute(
            "INSERT INTO groups (id, name, avatar, owner_id, description, created_at) VALUES (?,?,?,?,?,?)",
            (group_id, req.name, req.avatar, user["user_id"], req.description, ts)
        )
        await db.execute(
            "INSERT INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
            (group_id, user["user_id"], "owner", ts)
        )
        for agent_id in agent_manager.agents:
            await db.execute(
                "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
                (group_id, agent_id, "agent", ts)
            )
        await db.commit()
        return {"id": group_id, "name": req.name}
    finally:
        await db.close()


@app.get("/api/groups/{group_id}")
async def get_group_detail(group_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT id, name, avatar, owner_id, description FROM groups WHERE id=?", (group_id,)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "群不存在")
        # 群公告
        notice = ""
        async with db.execute("SELECT content FROM group_notices WHERE group_id=? ORDER BY created_at DESC LIMIT 1", (group_id,)) as c:
            r = await c.fetchone()
            if r: notice = r[0]
        return {"id": row[0], "name": row[1], "avatar": row[2], "owner_id": row[3], "description": row[4], "notice": notice}
    finally:
        await db.close()


@app.put("/api/groups/{group_id}")
async def update_group(group_id: str, name: str = "", avatar: str = "", description: str = "", user=Depends(get_current_user)):
    db = await get_db()
    try:
        updates, params = [], []
        if name: updates.append("name=?"); params.append(name)
        if avatar: updates.append("avatar=?"); params.append(avatar)
        if description: updates.append("description=?"); params.append(description)
        if not updates: return {"status": "no_change"}
        params.append(group_id)
        await db.execute(f"UPDATE groups SET {','.join(updates)} WHERE id=?", params)
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@app.get("/api/groups/{group_id}/members")
async def group_members(group_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        members = []
        async with db.execute("""
            SELECT gm.user_id, gm.role, gm.muted,
                   COALESCE(u.nickname, a.name) as name,
                   COALESCE(u.avatar, a.avatar) as avatar,
                   COALESCE(u.status, '') as status
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id=u.id
            LEFT JOIN agents a ON gm.user_id=a.id
            WHERE gm.group_id=?
        """, (group_id,)) as cursor:
            async for row in cursor:
                members.append({
                    "id": row[0], "role": row[1], "muted": bool(row[2]),
                    "name": row[3] or row[0], "avatar": row[4] or "😀",
                    "is_agent": row[1] == "agent", "status": row[5] or "",
                })
        return members
    finally:
        await db.close()


@app.post("/api/groups/{group_id}/members")
async def add_group_member(group_id: str, user_id: str = Query(...), role: str = Query("member"), user=Depends(get_current_user)):
    db = await get_db()
    try:
        ts = now()
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at) VALUES (?,?,?,?)",
            (group_id, user_id, role, ts)
        )
        await db.execute(
            "INSERT OR IGNORE INTO conv_members (conv_id, user_id, role, joined_at) VALUES (?,?,?,?)",
            (group_id, user_id, role, ts)
        )
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@app.delete("/api/groups/{group_id}/members/{user_id}")
async def remove_group_member(group_id: str, user_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@app.post("/api/groups/{group_id}/mute/{user_id}")
async def mute_group_member(group_id: str, user_id: str, req: MuteMemberReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("UPDATE group_members SET muted=? WHERE group_id=? AND user_id=?", (req.muted, group_id, user_id))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@app.post("/api/groups/{group_id}/notice")
async def post_group_notice(group_id: str, req: GroupNoticeReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        nid = gen_id()
        await db.execute(
            "INSERT INTO group_notices (id, group_id, content, publisher_id, created_at) VALUES (?,?,?,?,?)",
            (nid, group_id, req.content, user["user_id"], now())
        )
        await db.commit()
        # 广播群公告
        await ws_manager.broadcast_to_group(group_id, {
            "type": "group_notice",
            "data": {"group_id": group_id, "content": req.content, "publisher_id": user["user_id"]}
        })
        return {"id": nid}
    finally:
        await db.close()


# ==================== 消息 ====================

@app.get("/api/messages/{group_id}")
async def get_messages(group_id: str, limit: int = 50, before: float = 0, user=Depends(get_current_user)):
    db = await get_db()
    try:
        messages = []
        if before > 0:
            sql = "SELECT id, group_id, sender_id, sender_name, content, msg_type, is_agent, media_url, reply_to, created_at FROM messages WHERE group_id=? AND created_at<? ORDER BY created_at DESC LIMIT ?"
            params = (group_id, before, limit)
        else:
            sql = "SELECT id, group_id, sender_id, sender_name, content, msg_type, is_agent, media_url, reply_to, created_at FROM messages WHERE group_id=? ORDER BY created_at DESC LIMIT ?"
            params = (group_id, limit)

        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        for row in reversed(rows):
            reply_info = None
            if row[8]:
                async with db.execute("SELECT id, sender_name, content FROM messages WHERE id=?", (row[8],)) as rc:
                    rr = await rc.fetchone()
                    if rr:
                        reply_info = {"id": rr[0], "sender_name": rr[1], "content": rr[2][:50]}

            messages.append({
                "id": row[0], "group_id": row[1], "sender_id": row[2],
                "sender_name": row[3], "content": row[4], "msg_type": row[5],
                "is_agent": bool(row[6]), "media_url": row[7] or "",
                "reply_to": reply_info, "created_at": row[9],
                "agent_avatar": _get_agent_avatar(row[2]) if row[6] else "",
            })

        # 标记已读
        ts = now()
        await db.execute("UPDATE conv_members SET unread_count=0, last_read_at=? WHERE conv_id=? AND user_id=?", (ts, group_id, user["user_id"]))
        await db.commit()

        return messages
    finally:
        await db.close()


@app.post("/api/messages")
async def send_message(req: SendMessageReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        uid = user["user_id"]

        # 检查是否被禁言
        async with db.execute("SELECT muted FROM group_members WHERE group_id=? AND user_id=?", (req.group_id, uid)) as c:
            m = await c.fetchone()
            if m and m[0]:
                raise HTTPException(403, "你已被禁言")

        async with db.execute("SELECT nickname, avatar FROM users WHERE id=?", (uid,)) as c:
            row = await c.fetchone()
            nickname = row[0] if row else user["username"]
            avatar = row[1] if row else "😀"

        msg_id = gen_id()
        ts = now()

        await db.execute(
            "INSERT INTO messages (id, group_id, sender_id, sender_name, content, msg_type, is_agent, media_url, reply_to, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (msg_id, req.group_id, uid, nickname, req.content, req.msg_type, 0,
             req.media_url or req.voice_url, req.reply_to, ts)
        )

        # 更新未读计数
        await db.execute(
            "UPDATE conv_members SET unread_count=unread_count+1 WHERE conv_id=? AND user_id!=?",
            (req.group_id, uid)
        )
        await db.commit()

        msg_data = {
            "type": "message",
            "data": {
                "id": msg_id, "group_id": req.group_id,
                "sender_id": uid, "sender_name": nickname,
                "sender_avatar": avatar,
                "content": req.content, "msg_type": req.msg_type,
                "is_agent": False, "created_at": ts,
                "media_url": req.media_url or req.voice_url or "",
                "reply_to": req.reply_to,
            }
        }
        await ws_manager.broadcast_to_group(req.group_id, msg_data, exclude_user=uid)

        asyncio.create_task(_trigger_agent_replies(req.group_id, uid, nickname, req.content, req.msg_type))

        return {"id": msg_id, "created_at": ts}
    finally:
        await db.close()


@app.delete("/api/messages/{msg_id}")
async def delete_message(msg_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT sender_id, group_id FROM messages WHERE id=?", (msg_id,)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "消息不存在")
            if row[0] != user["user_id"]:
                raise HTTPException(403, "只能删除自己的消息")

        await db.execute("DELETE FROM messages WHERE id=?", (msg_id,))
        await db.commit()

        await ws_manager.broadcast_to_group(row[1], {
            "type": "message_deleted",
            "data": {"message_id": msg_id, "group_id": row[1]}
        })
        return {"status": "ok"}
    finally:
        await db.close()


@app.post("/api/messages/forward")
async def forward_message(req: ForwardMsgReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT sender_name, content, msg_type, media_url FROM messages WHERE id=?", (req.message_id,)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "消息不存在")

        async with db.execute("SELECT nickname FROM users WHERE id=?", (user["user_id"],)) as c:
            u = await c.fetchone()
            nickname = u[0] if u else "unknown"

        msg_id = gen_id()
        ts = now()
        content = f"[转发] {row[2]}: {row[1]}" if row[2] != "text" else f"[转发] {row[1]}"

        await db.execute(
            "INSERT INTO messages (id, group_id, sender_id, sender_name, content, msg_type, is_agent, media_url, reply_to, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (msg_id, req.target_group_id, user["user_id"], nickname, content, row[2], 0, row[3] or "", "", ts)
        )
        await db.commit()

        await ws_manager.broadcast_to_group(req.target_group_id, {
            "type": "message",
            "data": {"id": msg_id, "group_id": req.target_group_id, "sender_id": user["user_id"],
                     "sender_name": nickname, "content": content, "msg_type": row[2],
                     "is_agent": False, "created_at": ts, "media_url": row[3] or ""}
        })
        return {"id": msg_id}
    finally:
        await db.close()


@app.get("/api/messages/search/{group_id}")
async def search_messages(group_id: str, q: str = Query(...), limit: int = 20, user=Depends(get_current_user)):
    db = await get_db()
    try:
        results = []
        async with db.execute(
            "SELECT id, sender_name, content, msg_type, created_at FROM messages WHERE group_id=? AND content LIKE ? ORDER BY created_at DESC LIMIT ?",
            (group_id, f"%{q}%", limit)
        ) as c:
            async for row in c:
                results.append({
                    "id": row[0], "sender_name": row[1], "content": row[2],
                    "msg_type": row[3], "created_at": row[4],
                })
        return results
    finally:
        await db.close()


async def _trigger_agent_replies(group_id: str, sender_id: str, sender_name: str, content: str, msg_type: str = "text"):
    db = await get_db()
    try:
        replies = await agent_manager.handle_group_message(group_id, sender_id, sender_name, content, msg_type)

        for reply in replies:
            agent_id = reply["agent_id"]
            msg_id = gen_id()
            ts = now()

            # 先发打字提示
            await ws_manager.broadcast_to_group(group_id, {
                "type": "typing",
                "data": {"group_id": group_id, "agent_id": agent_id, "agent_name": reply["agent_name"], "agent_avatar": reply.get("agent_avatar", "🤖")}
            })

            voice_url = None
            if random.random() < 0.3 and len(reply["content"]) > 5:
                voice_url = await _generate_agent_voice(agent_id, reply["content"])

            msg_type_out = "voice" if voice_url else reply["msg_type"]

            await db.execute(
                "INSERT INTO messages (id, group_id, sender_id, sender_name, content, msg_type, is_agent, media_url, reply_to, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (msg_id, group_id, agent_id, reply["agent_name"], reply["content"], msg_type_out, 1, voice_url or "", "", ts)
            )
            await db.commit()

            msg_data = {
                "type": "message",
                "data": {
                    "id": msg_id, "group_id": group_id,
                    "sender_id": agent_id, "sender_name": reply["agent_name"],
                    "content": reply["content"], "msg_type": msg_type_out,
                    "is_agent": True, "created_at": ts,
                    "agent_avatar": reply.get("agent_avatar", "🤖"),
                    "media_url": voice_url or "",
                }
            }
            await ws_manager.broadcast_to_group(group_id, msg_data)

    except Exception as e:
        logger.error(f"Agent 回复异常: {e}")
    finally:
        await db.close()


# ==================== Agent ====================

@app.get("/api/agents")
async def list_agents(user=Depends(get_current_user)):
    return agent_manager.get_all()


@app.post("/api/agents")
async def create_agent(req: CreateAgentReq, user=Depends(get_current_user)):
    agent_id = await agent_manager.create_agent(req.dict())
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
                memories.append({"id": row[0], "content": row[1], "importance": row[2], "type": row[3], "created_at": row[4]})
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

    db = await get_db()
    try:
        # 加入所有群
        async with db.execute("SELECT group_id FROM group_members WHERE user_id=?", (user_id,)) as c:
            async for row in c:
                await ws_manager.join_group(user_id, row[0])
        # 加入所有私聊
        async with db.execute("SELECT conv_id FROM conv_members WHERE user_id=?", (user_id,)) as c:
            async for row in c:
                await ws_manager.join_group(user_id, row[0])
    finally:
        await db.close()

    # 通知好友上线
    db = await get_db()
    try:
        async with db.execute("SELECT friend_id FROM friendships WHERE user_id=? AND status='accepted'", (user_id,)) as c:
            async for row in c:
                await ws_manager.send_to_user(row[0], {"type": "friend_online", "data": {"user_id": user_id}})
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
                    # 转发打字提示
                    gid = msg.get("group_id")
                    if gid:
                        await ws_manager.broadcast_to_group(gid, {
                            "type": "user_typing",
                            "data": {"group_id": gid, "user_id": user_id, "user_name": msg.get("user_name", "")}
                        }, exclude_user=user_id)
                elif msg.get("type") == "read":
                    # 标记已读
                    gid = msg.get("group_id")
                    if gid:
                        ts2 = time.time()
                        await db.execute("UPDATE conv_members SET unread_count=0, last_read_at=? WHERE conv_id=? AND user_id=?", (ts2, gid, user_id))
                        await db.commit()
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, websocket)
        # 通知好友下线
        db2 = await get_db()
        try:
            await db2.execute("UPDATE users SET status='offline' WHERE id=?", (user_id,))
            await db2.commit()
            async with db2.execute("SELECT friend_id FROM friendships WHERE user_id=? AND status='accepted'", (user_id,)) as c:
                async for row in c:
                    await ws_manager.send_to_user(row[0], {"type": "friend_offline", "data": {"user_id": user_id}})
        finally:
            await db2.close()


# ==================== 语音 ====================

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


async def _generate_agent_voice(agent_id: str, text: str) -> Optional[str]:
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


# ==================== 图片/文件 ====================

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "只能上传图片文件")
    file_id = gen_id()
    ext = Path(file.filename).suffix or ".jpg"
    filepath = f"data/uploads/{file_id}{ext}"
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "图片大小不能超过 10MB")
    with open(filepath, "wb") as f:
        f.write(content)
    return {"id": file_id, "url": f"/api/uploads/{file_id}{ext}", "filename": file.filename}


@app.get("/api/uploads/{filename}")
async def get_upload(filename: str):
    filepath = f"data/uploads/{filename}"
    if not Path(filepath).exists():
        raise HTTPException(404)
    ext = Path(filename).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".webp": "image/webp", ".mp4": "video/mp4",
    }
    return FileResponse(filepath, media_type=media_types.get(ext, "application/octet-stream"))


# ==================== 炼化 ====================

class RefineTextReq(BaseModel):
    agent_id: str
    text: str
    source: str = "text"

@app.post("/api/agent/refine/text")
async def refine_agent_text(req: RefineTextReq, user=Depends(get_current_user)):
    agent = agent_manager.get_agent(req.agent_id)
    if not agent:
        raise HTTPException(404, "Agent 不存在")

    analysis_prompt = f"""分析以下文本，提取说话人的性格特征、说话风格、兴趣爱好、口头禅。
文本来源: {req.source}
文本内容:
{req.text}

请以 JSON 格式输出：
{{"traits": [], "speaking_style": "", "interests": [], "catchphrases": [], "backstory_update": "", "personality_summary": ""}}"""

    try:
        result = await agent._call_llm("你是一个专业的性格分析专家。", analysis_prompt)
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        traits_data = json.loads(clean)

        p = agent.personality
        if traits_data.get("traits"):
            p.traits = list(set(p.traits + traits_data["traits"]))
        if traits_data.get("speaking_style"):
            p.speaking_style = traits_data["speaking_style"]
        if traits_data.get("interests"):
            p.interests = list(set(p.interests + traits_data["interests"]))
        if traits_data.get("catchphrases"):
            p.catchphrases = list(set(p.catchphrases + traits_data["catchphrases"]))
        if traits_data.get("backstory_update"):
            p.backstory += "\n" + traits_data["backstory_update"]

        await agent.memory.add_long_term(f"[炼化-文本] {req.source}: {req.text[:500]}", importance=0.9)

        db = await get_db()
        await db.execute(
            "UPDATE agents SET traits=?, speaking_style=?, interests=?, catchphrases=?, backstory=? WHERE id=?",
            (json.dumps(p.traits, ensure_ascii=False), p.speaking_style,
             json.dumps(p.interests, ensure_ascii=False), json.dumps(p.catchphrases, ensure_ascii=False),
             p.backstory, req.agent_id)
        )
        await db.commit()
        await db.close()

        return {"status": "ok", "message": f"炼化完成！提取了 {len(traits_data.get('traits', []))} 个性格特征", "traits": traits_data}
    except json.JSONDecodeError:
        return {"status": "ok", "message": "炼化数据已记录", "raw": result[:500]}
    except Exception as e:
        raise HTTPException(500, f"炼化失败: {e}")


# ==================== 炼化 - 语音/视频 ====================

@app.post("/api/agent/refine/voice")
async def refine_agent_voice(file: UploadFile = File(...), agent_id: str = Form(""), user=Depends(get_current_user)):
    """炼化Agent - 通过语音分析音色和说话习惯"""
    agent = agent_manager.get_agent(agent_id) if agent_id else None
    if not agent:
        raise HTTPException(404, "Agent 不存在")

    file_id = gen_id()
    ext = Path(file.filename).suffix or ".wav"
    filepath = f"data/voices/refine_{file_id}{ext}"
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "文件不能超过50MB")
    with open(filepath, "wb") as f:
        f.write(content)

    db = await get_db()
    voice_config = {"sample_path": filepath, "sample_size": len(content), "format": ext}
    await db.execute("UPDATE agents SET voice_config=? WHERE id=?",
                    (json.dumps(voice_config, ensure_ascii=False), agent_id))
    await db.commit()
    await db.close()

    await agent.memory.add_long_term(
        f"[炼化-语音] 语音样本已录入，可用于音色克隆",
        importance=0.9, metadata={"type": "refinement", "source": "voice"}
    )
    return {"status": "ok", "message": "语音样本已录入，数字人将参考此音色", "file_id": file_id}


@app.post("/api/agent/refine/video")
async def refine_agent_video(file: UploadFile = File(...), agent_id: str = Form(""), user=Depends(get_current_user)):
    """炼化Agent - 通过视频分析表达习惯"""
    agent = agent_manager.get_agent(agent_id) if agent_id else None
    if not agent:
        raise HTTPException(404, "Agent 不存在")

    file_id = gen_id()
    ext = Path(file.filename).suffix or ".mp4"
    filepath = f"data/uploads/refine_{file_id}{ext}"
    content = await file.read()
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(400, "视频不能超过200MB")
    with open(filepath, "wb") as f:
        f.write(content)

    audio_path = None
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(filepath)
        audio_path = f"data/voices/video_audio_{file_id}.wav"
        audio.export(audio_path, format="wav")
    except Exception as e:
        logger.warning(f"视频音频提取失败: {e}")

    await agent.memory.add_long_term(
        f"[炼化-视频] 视频资料已录入: {filepath}, 提取音频: {audio_path or '无'}",
        importance=0.9, metadata={"type": "refinement", "source": "video", "video_path": filepath, "audio_path": audio_path}
    )

    if audio_path:
        db = await get_db()
        voice_config = {"sample_path": audio_path, "source": "video"}
        await db.execute("UPDATE agents SET voice_config=? WHERE id=?",
                        (json.dumps(voice_config, ensure_ascii=False), agent_id))
        await db.commit()
        await db.close()

    return {"status": "ok", "message": "视频资料已录入，已提取音频用于音色分析", "file_id": file_id}


@app.get("/api/agents/{agent_id}/relationships")
async def get_agent_relationships(agent_id: str, user=Depends(get_current_user)):
    """获取Agent关系图谱"""
    db = await get_db()
    try:
        async with db.execute("SELECT relationships FROM agents WHERE id=?", (agent_id,)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "Agent不存在")
            rels = json.loads(row[0]) if row[0] else {}
            return {"agent_id": agent_id, "relationships": rels}
    finally:
        await db.close()


@app.post("/api/agents/{agent_id}/relationships")
async def update_agent_relationships(agent_id: str, relationships: dict, user=Depends(get_current_user)):
    """更新Agent关系图谱"""
    db = await get_db()
    try:
        await db.execute("UPDATE agents SET relationships=? WHERE id=?",
                        (json.dumps(relationships, ensure_ascii=False), agent_id))
        await db.commit()
        # 更新内存
        agent = agent_manager.get_agent(agent_id)
        if agent:
            agent.personality.relationships = relationships
        return {"status": "ok"}
    finally:
        await db.close()


# ==================== 记忆 ====================

@app.get("/api/memories/search")
async def search_memories(q: str, agent_id: str = "", user=Depends(get_current_user)):
    db = await get_db()
    try:
        results = []
        if agent_id:
            sql = "SELECT id, agent_id, content, importance, memory_type, created_at FROM agent_memories WHERE agent_id=? AND content LIKE ? ORDER BY importance DESC LIMIT 20"
            params = (agent_id, f"%{q}%")
        else:
            sql = "SELECT id, agent_id, content, importance, memory_type, created_at FROM agent_memories WHERE content LIKE ? ORDER BY importance DESC LIMIT 20"
            params = (f"%{q}%",)
        async with db.execute(sql, params) as cursor:
            async for row in cursor:
                results.append({"id": row[0], "agent_id": row[1], "content": row[2], "importance": row[3], "type": row[4], "created_at": row[5]})
        return results
    finally:
        await db.close()


# ==================== 系统 ====================

@app.get("/api/status")
async def system_status():
    return {
        "status": "running",
        "agents": len(agent_manager.agents) if agent_manager else 0,
        "online": ws_manager.get_online_count(),
        "version": "2.0.0",
    }


@app.get("/api/voices")
async def list_voices():
    return {
        "voices": [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "gender": "female"},
            {"id": "zh-CN-YunxiNeural", "name": "云希", "gender": "male"},
            {"id": "zh-CN-XiaoyiNeural", "name": "晓艺", "gender": "female"},
            {"id": "zh-CN-YunjianNeural", "name": "云健", "gender": "male"},
        ]
    }


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
            {"id": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini"]},
            {"id": "deepseek", "name": "DeepSeek", "models": ["deepseek-chat", "deepseek-reasoner"]},
            {"id": "zhipu", "name": "智谱AI", "models": ["glm-4", "glm-4-flash"]},
            {"id": "qwen", "name": "通义千问", "models": ["qwen-max", "qwen-plus"]},
        ]
    }
