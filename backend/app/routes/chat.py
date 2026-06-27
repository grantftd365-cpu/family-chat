"""聊天路由 - 消息/群组/私聊"""
import asyncio
import os
import random
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger

from ..core.auth import get_current_user
from ..core.websocket import ws_manager
from ..models.database import get_db, gen_id, now
from ..services.delivery import MessageDelivery, ReactionManager

router = APIRouter(prefix="/api")


# ==================== Models ====================

class CreateGroupReq(BaseModel):
    name: str
    description: str = ""
    avatar: str = "👥"


class SendMessageReq(BaseModel):
    group_id: str
    content: str
    msg_type: str = "text"
    voice_url: str = ""
    media_url: str = ""
    file_name: str = ""
    file_size: int = 0
    reply_to: str = ""
    extra: str = "{}"


class RecallReq(BaseModel):
    message_id: str


class ForwardReq(BaseModel):
    message_id: str
    target_group_id: str


class AddReactionReq(BaseModel):
    emoji: str


class AddGroupMemberReq(BaseModel):
    user_id: str
    role: str = "member"


class UpdateGroupReq(BaseModel):
    name: str = ""
    description: str = ""
    announcement: str = ""
    avatar: str = ""


class PatReq(BaseModel):
    to_user_id: str
    action: str = "拍了拍"


class UpdateAnnouncementReq(BaseModel):
    content: str
    pinned_message_ids: list = []  # 可选：同时置顶的消息ID列表


class RedEnvelopeReq(BaseModel):
    group_id: str = ""
    receiver_id: str = ""
    amount: float
    count: int = 1
    greeting: str = "恭喜发财"


class ClaimRedEnvelopeReq(BaseModel):
    envelope_id: str


# ==================== 群组 ====================

@router.get("/groups")
async def list_groups(user=Depends(get_current_user)):
    db = await get_db()
    try:
        groups = []
        async with db.execute("""
            SELECT g.id, g.name, g.avatar, g.description, g.announcement, g.owner_id,
                   (SELECT COUNT(*) FROM group_members WHERE group_id=g.id) as member_count,
                   (SELECT content FROM messages WHERE group_id=g.id AND recalled=0 ORDER BY created_at DESC LIMIT 1) as last_msg,
                   (SELECT sender_name FROM messages WHERE group_id=g.id AND recalled=0 ORDER BY created_at DESC LIMIT 1) as last_sender,
                   (SELECT msg_type FROM messages WHERE group_id=g.id AND recalled=0 ORDER BY created_at DESC LIMIT 1) as last_type,
                   (SELECT created_at FROM messages WHERE group_id=g.id AND recalled=0 ORDER BY created_at DESC LIMIT 1) as last_time
            FROM groups g
            JOIN group_members gm ON g.id=gm.group_id
            WHERE gm.user_id=?
            ORDER BY last_time DESC
        """, (user["user_id"],)) as cursor:
            async for row in cursor:
                last_msg = row[7] or ""
                last_type = row[9] or "text"
                if last_type == "image":
                    last_msg = "[图片]"
                elif last_type == "voice":
                    last_msg = "[语音]"
                elif last_type == "file":
                    last_msg = "[文件]"
                elif last_type == "red_envelope":
                    last_msg = "[红包]"
                if row[8] and last_msg:
                    last_msg = f"{row[8]}: {last_msg}"
                groups.append({
                    "id": row[0], "name": row[1], "avatar": row[2] or "👥",
                    "description": row[3], "announcement": row[4], "owner_id": row[5],
                    "member_count": row[6], "last_message": last_msg, "last_time": row[10] or 0,
                })

        # 批量获取未读数
        unread_counts = await MessageDelivery.get_all_unread_counts(user["user_id"])
        for g in groups:
            g["unread_count"] = unread_counts.get(g["id"], 0)

        return groups
    finally:
        await db.close()


@router.post("/groups")
async def create_group(req: CreateGroupReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        group_id = gen_id()
        ts = now()
        await db.execute(
            "INSERT INTO groups (id,name,owner_id,description,avatar,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (group_id, req.name, user["user_id"], req.description, req.avatar, ts, ts)
        )
        await db.execute(
            "INSERT INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
            (group_id, user["user_id"], "owner", ts)
        )
        # 加入所有 Agent
        async with db.execute("SELECT id FROM agents WHERE enabled=1") as c:
            async for row in c:
                await db.execute(
                    "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
                    (group_id, row[0], "agent", ts)
                )
        await db.commit()
        return {"id": group_id, "name": req.name}
    finally:
        await db.close()


@router.get("/groups/{group_id}")
async def get_group(group_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        # 使用具名列名，避免 SELECT * 导致索引错位
        async with db.execute(
            "SELECT id, name, avatar, owner_id, description, announcement, mute_all FROM groups WHERE id=?",
            (group_id,)
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "群不存在")
            return {
                "id": row[0], "name": row[1], "avatar": row[2],
                "owner_id": row[3], "description": row[4],
                "announcement": row[5] or "", "mute_all": bool(row[6]),
            }
    finally:
        await db.close()


@router.put("/groups/{group_id}")
async def update_group(group_id: str, req: UpdateGroupReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        # 权限校验：只有群主/管理员可以修改群信息
        async with db.execute(
            "SELECT role FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(403, "你不是群成员")
            if row[0] not in ("owner", "admin"):
                raise HTTPException(403, "只有群主或管理员可以修改群信息")
        updates, params = [], []
        if req.name:
            updates.append("name=?"); params.append(req.name)
        if req.description is not None:
            updates.append("description=?"); params.append(req.description)
        if req.announcement is not None:
            updates.append("announcement=?"); params.append(req.announcement)
        if req.avatar:
            updates.append("avatar=?"); params.append(req.avatar)
        if not updates:
            return {"status": "ok"}
        updates.append("updated_at=?"); params.append(now())
        params.append(group_id)
        await db.execute(f"UPDATE groups SET {','.join(updates)} WHERE id=?", params)
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.get("/groups/{group_id}/members")
async def group_members(group_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        members = []
        async with db.execute("""
            SELECT gm.user_id, gm.role, gm.nickname, gm.muted_until,
                   COALESCE(u.nickname, a.name) as name,
                   COALESCE(u.avatar, a.avatar) as avatar,
                   COALESCE(u.avatar_url, '') as avatar_url,
                   COALESCE(u.online_status, 'offline') as online_status,
                   COALESCE(u.signature, '') as signature
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id=u.id
            LEFT JOIN agents a ON gm.user_id=a.id
            WHERE gm.group_id=?
        """, (group_id,)) as cursor:
            async for row in cursor:
                members.append({
                    "id": row[0], "role": row[1], "group_nickname": row[2] or "",
                    "muted_until": row[3], "name": row[4] or row[0],
                    "avatar": row[5] or "😀", "avatar_url": row[6] or "",
                    "is_agent": row[1] == "agent",
                    "online_status": row[7], "signature": row[8] or "",
                })
        return members
    finally:
        await db.close()


@router.post("/groups/{group_id}/members")
async def add_group_member(group_id: str, req: AddGroupMemberReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        # 权限校验：只有群主/管理员可以邀请成员
        async with db.execute(
            "SELECT role FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            caller_row = await c.fetchone()
            if not caller_row:
                raise HTTPException(403, "你不是群成员")
            if caller_row[0] not in ("owner", "admin"):
                raise HTTPException(403, "只有群主或管理员可以邀请成员")
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
            (group_id, req.user_id, req.role, now())
        )
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.delete("/groups/{group_id}/members/{user_id}")
async def remove_group_member(group_id: str, user_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        # 权限校验：只有群主可以踢人
        async with db.execute(
            "SELECT role FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            caller_row = await c.fetchone()
            if not caller_row:
                raise HTTPException(403, "你不是群成员")
            if caller_row[0] not in ("owner", "admin"):
                raise HTTPException(403, "只有群主或管理员可以移除成员")
        # 不能踢自己
        if user_id == user["user_id"]:
            raise HTTPException(400, "不能移除自己，请使用退出群聊")
        # 不能踢群主
        async with db.execute(
            "SELECT role FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user_id)
        ) as c:
            target_row = await c.fetchone()
            if target_row and target_row[0] == "owner":
                raise HTTPException(403, "不能移除群主")
        await db.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


# ==================== 消息 ====================

@router.get("/messages/{group_id}")
async def get_messages(group_id: str, limit: int = 50, before: float = 0, user=Depends(get_current_user)):
    db = await get_db()
    try:
        messages = []
        # 获取用户隐藏的消息ID集合
        hidden_ids = set()
        async with db.execute(
            "SELECT message_id FROM hidden_messages WHERE user_id=?",
            (user["user_id"],)
        ) as hc:
            async for hr in hc:
                hidden_ids.add(hr[0])

        if before > 0:
            sql = "SELECT * FROM messages WHERE group_id=? AND created_at<? ORDER BY created_at DESC LIMIT ?"
            params = (group_id, before, limit)
        else:
            sql = "SELECT * FROM messages WHERE group_id=? ORDER BY created_at DESC LIMIT ?"
            params = (group_id, limit)

        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        for row in reversed(rows):
            msg = {
                "id": row[0], "group_id": row[1], "sender_id": row[2],
                "sender_name": row[3], "sender_avatar": row[4] or "",
                "content": row[5], "msg_type": row[6],
                "media_url": row[7] or "", "file_name": row[8] or "",
                "file_size": row[9] or 0,
                "is_agent": bool(row[10]), "reply_to": row[11] or "",
                "reply_content": row[12] or "", "forwarded_from": row[13] or "",
                "recalled": bool(row[14]), "pinned": bool(row[15]),
                "extra": row[16] or "{}",
                "created_at": row[17],
            }
            if msg["recalled"]:
                msg["content"] = "你撤回了一条消息" if msg["sender_id"] == user["user_id"] else f"{msg['sender_name']}撤回了一条消息"
                msg["msg_type"] = "system"
            # 跳过用户已隐藏的消息
            if msg["id"] in hidden_ids:
                continue
            messages.append(msg)

        # 获取 reactions v2 (飞书风格表情回应)
        msg_ids = [m["id"] for m in messages]
        reactions_v2 = await ReactionManager.get_batch_reactions(msg_ids)
        for m in messages:
            m["reactions"] = reactions_v2.get(m["id"], [])

        # 获取自己发送的消息的投递状态
        my_msg_ids = [m["id"] for m in messages if m["sender_id"] == user["user_id"]]
        if my_msg_ids:
            for mid in my_msg_ids:
                status = await MessageDelivery.get_message_status(mid)
                for m in messages:
                    if m["id"] == mid:
                        if status["pending"] > 0:
                            m["_status"] = "sent"
                        elif status["delivered"] > 0:
                            m["_status"] = "delivered"
                        elif status["read"] > 0:
                            m["_status"] = "read"
                        else:
                            m["_status"] = "sent"

        return messages
    finally:
        await db.close()


@router.post("/messages")
async def send_message(req: SendMessageReq, user=Depends(get_current_user)):
    from ..main import agent_manager
    db = await get_db()
    try:
        async with db.execute("SELECT nickname,avatar FROM users WHERE id=?", (user["user_id"],)) as c:
            row = await c.fetchone()
            nickname = row[0] if row else user["username"]
            avatar = row[1] if row else "😀"

        # 检查是否被禁言
        async with db.execute(
            "SELECT muted_until FROM group_members WHERE group_id=? AND user_id=?",
            (req.group_id, user["user_id"])
        ) as c:
            mute_row = await c.fetchone()
            if mute_row and mute_row[0] > now():
                raise HTTPException(403, "你已被禁言")

        msg_id = gen_id()
        ts = now()

        # 获取回复内容
        reply_content = ""
        if req.reply_to:
            async with db.execute("SELECT content,sender_name FROM messages WHERE id=?", (req.reply_to,)) as c:
                r = await c.fetchone()
                if r:
                    reply_content = f"{r[1]}: {r[0][:50]}"

        await db.execute(
            """INSERT INTO messages (id,group_id,sender_id,sender_name,sender_avatar,content,msg_type,
               media_url,file_name,file_size,is_agent,reply_to,reply_content,extra,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (msg_id, req.group_id, user["user_id"], nickname, avatar,
             req.content, req.msg_type, req.media_url, req.file_name, req.file_size,
             0, req.reply_to, reply_content, req.extra, ts)
        )
        await db.commit()

        msg_data = {
            "type": "message",
            "data": {
                "id": msg_id, "group_id": req.group_id,
                "sender_id": user["user_id"], "sender_name": nickname,
                "sender_avatar": avatar, "content": req.content,
                "msg_type": req.msg_type, "media_url": req.media_url,
                "file_name": req.file_name, "file_size": req.file_size,
                "is_agent": False, "reply_to": req.reply_to,
                "reply_content": reply_content, "extra": req.extra,
                "created_at": ts, "reactions": [],
            }
        }
        await ws_manager.broadcast_to_group(req.group_id, msg_data, exclude_user=user["user_id"])

        # 消息必达：为群成员创建投递记录
        asyncio.create_task(MessageDelivery.on_message_sent(msg_id, req.group_id, user["user_id"]))

        # 触发 Agent 回复（支持语音）
        asyncio.create_task(
            _handle_agent_replies(req.group_id, user["user_id"], nickname, req.content, req.msg_type)
        )

        return {"id": msg_id, "created_at": ts}
    finally:
        await db.close()


async def _handle_agent_replies(group_id: str, sender_id: str, sender_name: str,
                                content: str, msg_type: str):
    """处理 Agent 回复，支持语音合成"""
    from ..main import agent_manager, voice_profile_manager
    try:
        replies = await agent_manager.handle_group_message(
            group_id, sender_id, sender_name, content, msg_type
        )
        for reply in replies:
            db = await get_db()
            try:
                msg_id = gen_id()
                ts = now()

                # 尝试生成语音
                voice_url = ""
                if voice_profile_manager:
                    try:
                        voice = await voice_profile_manager.get_agent_voice(reply["agent_id"])
                        if voice:
                            tts_path = await voice_profile_manager.synthesize(
                                reply["content"], profile_id=voice["id"]
                            )
                            if tts_path:
                                voice_url = f"/api/voice/{os.path.basename(tts_path)}"
                    except Exception as ve:
                        logger.debug(f"语音合成跳过: {ve}")

                reply_msg_type = "voice" if voice_url else "text"
                await db.execute(
                    """INSERT INTO messages (id,group_id,sender_id,sender_name,sender_avatar,content,msg_type,
                       media_url,is_agent,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (msg_id, group_id, reply["agent_id"], reply["agent_name"],
                     reply.get("agent_avatar", "🤖"), reply["content"],
                     reply_msg_type, voice_url, 1, ts)
                )
                await db.commit()

                ws_data = {
                    "type": "message",
                    "data": {
                        "id": msg_id, "group_id": group_id,
                        "sender_id": reply["agent_id"], "sender_name": reply["agent_name"],
                        "sender_avatar": reply.get("agent_avatar", "🤖"),
                        "content": reply["content"], "msg_type": reply_msg_type,
                        "media_url": voice_url, "is_agent": True,
                        "created_at": ts, "reactions": [],
                    }
                }
                await ws_manager.broadcast_to_group(group_id, ws_data)
            finally:
                await db.close()
    except Exception as e:
        logger.error(f"Agent 回复处理失败: {e}")


@router.post("/messages/recall")
async def recall_message(req: RecallReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT sender_id,created_at FROM messages WHERE id=?", (req.message_id,)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "消息不存在")
            if row[0] != user["user_id"]:
                raise HTTPException(403, "只能撤回自己的消息")
            if now() - row[1] > 120:
                raise HTTPException(400, "超过2分钟无法撤回")

        await db.execute("UPDATE messages SET recalled=1 WHERE id=?", (req.message_id,))
        await db.commit()

        # 广播撤回通知
        async with db.execute("SELECT group_id FROM messages WHERE id=?", (req.message_id,)) as c:
            r = await c.fetchone()
            if r:
                await ws_manager.broadcast_to_group(r[0], {
                    "type": "recall", "data": {"message_id": req.message_id, "user_id": user["user_id"]}
                })

        return {"status": "ok"}
    finally:
        await db.close()


@router.post("/messages/forward")
async def forward_message(req: ForwardReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT content,msg_type,media_url,sender_name FROM messages WHERE id=?", (req.message_id,)) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404)

        async with db.execute("SELECT nickname FROM users WHERE id=?", (user["user_id"],)) as c:
            u = await c.fetchone()
            nickname = u[0] if u else "unknown"

        msg_id = gen_id()
        ts = now()
        await db.execute(
            """INSERT INTO messages (id,group_id,sender_id,sender_name,content,msg_type,media_url,forwarded_from,created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (msg_id, req.target_group_id, user["user_id"], nickname,
             row[0], row[1], row[2] or "", f"{row[3]}: {row[0][:30]}", ts)
        )
        await db.commit()

        await ws_manager.broadcast_to_group(req.target_group_id, {
            "type": "message",
            "data": {
                "id": msg_id, "group_id": req.target_group_id,
                "sender_id": user["user_id"], "sender_name": nickname,
                "content": row[0], "msg_type": row[1], "media_url": row[2] or "",
                "is_agent": False, "forwarded_from": f"{row[3]}: {row[0][:30]}",
                "created_at": ts, "reactions": [],
            }
        })
        return {"id": msg_id}
    finally:
        await db.close()


@router.post("/messages/{message_id}/pin")
async def pin_message(message_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        # 权限校验：必须是群成员才能置顶
        async with db.execute("SELECT group_id FROM messages WHERE id=?", (message_id,)) as c:
            msg_row = await c.fetchone()
            if not msg_row:
                raise HTTPException(404, "消息不存在")
        async with db.execute(
            "SELECT 1 FROM group_members WHERE group_id=? AND user_id=?",
            (msg_row[0], user["user_id"])
        ) as c:
            if not await c.fetchone():
                raise HTTPException(403, "你不是该群成员")
        await db.execute("UPDATE messages SET pinned=1 WHERE id=?", (message_id,))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.delete("/messages/{message_id}/pin")
async def unpin_message(message_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("UPDATE messages SET pinned=0 WHERE id=?", (message_id,))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.get("/messages/{group_id}/pinned")
async def get_pinned_messages(group_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        msgs = []
        async with db.execute(
            "SELECT id,sender_name,content,created_at FROM messages WHERE group_id=? AND pinned=1 ORDER BY created_at DESC",
            (group_id,)
        ) as cursor:
            async for row in cursor:
                msgs.append({"id": row[0], "sender_name": row[1], "content": row[2], "created_at": row[3]})
        return msgs
    finally:
        await db.close()


# ==================== 表情回复 ====================

@router.post("/messages/{message_id}/reactions")
async def add_reaction(message_id: str, req: AddReactionReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        rid = gen_id()
        await db.execute(
            "INSERT OR IGNORE INTO message_reactions (id,message_id,user_id,emoji,created_at) VALUES (?,?,?,?,?)",
            (rid, message_id, user["user_id"], req.emoji, now())
        )
        await db.commit()

        async with db.execute("SELECT group_id FROM messages WHERE id=?", (message_id,)) as c:
            row = await c.fetchone()
            if row:
                await ws_manager.broadcast_to_group(row[0], {
                    "type": "reaction",
                    "data": {"message_id": message_id, "user_id": user["user_id"], "emoji": req.emoji, "action": "add"}
                })
        return {"status": "ok"}
    finally:
        await db.close()


@router.delete("/messages/{message_id}/reactions/{emoji}")
async def remove_reaction(message_id: str, emoji: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM message_reactions WHERE message_id=? AND user_id=? AND emoji=?",
            (message_id, user["user_id"], emoji)
        )
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


# ==================== 消息必达 + 已读回执 ====================

class AckReq(BaseModel):
    message_ids: list  # 批量确认收到


class ReadReq(BaseModel):
    group_id: str
    before_timestamp: float = 0  # 标记该时间之前的消息全部已读


class ReactionV2Req(BaseModel):
    emoji: str


@router.post("/messages/ack")
async def ack_messages(req: AckReq, user=Depends(get_current_user)):
    """客户端确认收到消息（标记为 delivered）"""
    for mid in req.message_ids:
        await MessageDelivery.mark_delivered(mid, user["user_id"])
    return {"status": "ok", "acked": len(req.message_ids)}


@router.post("/messages/read")
async def mark_read(req: ReadReq, user=Depends(get_current_user)):
    """批量标记已读 — 打开群聊时调用"""
    await MessageDelivery.mark_batch_read(
        req.group_id, user["user_id"], req.before_timestamp
    )
    # 广播已读状态给群内其他人
    await ws_manager.broadcast_to_group(req.group_id, {
        "type": "read",
        "data": {
            "user_id": user["user_id"],
            "group_id": req.group_id,
            "before": req.before_timestamp,
        }
    }, exclude_user=user["user_id"])
    return {"status": "ok"}


@router.post("/messages/{message_id}/read")
async def mark_single_read(message_id: str, user=Depends(get_current_user)):
    """标记单条消息已读"""
    await MessageDelivery.mark_read(message_id, user["user_id"])
    return {"status": "ok"}


@router.get("/messages/{message_id}/read-users")
async def get_read_users(message_id: str, user=Depends(get_current_user)):
    """获取已读某消息的用户列表"""
    users = await MessageDelivery.get_read_users(message_id)
    return users


@router.get("/unread")
async def get_all_unread(user=Depends(get_current_user)):
    """获取所有群的未读消息数"""
    counts = await MessageDelivery.get_all_unread_counts(user["user_id"])
    return counts


@router.get("/messages/{group_id}/undelivered")
async def get_undelivered(group_id: str, user=Depends(get_current_user)):
    """获取用户在某群的未送达消息（重连补发）"""
    messages = await MessageDelivery.get_undelivered_messages(user["user_id"])
    # 过滤出当前群的消息
    group_msgs = [m for m in messages if m["group_id"] == group_id]
    return group_msgs


@router.get("/undelivered")
async def get_all_undelivered(user=Depends(get_current_user)):
    """获取用户所有未送达消息（断线重连时调用）"""
    messages = await MessageDelivery.get_undelivered_messages(user["user_id"])
    return messages


# ==================== 飞书风格表情回应 ====================

@router.post("/messages/{message_id}/reactions/v2")
async def add_reaction_v2(message_id: str, req: ReactionV2Req, user=Depends(get_current_user)):
    """添加表情回应"""
    # 获取用户昵称
    db = await get_db()
    try:
        async with db.execute("SELECT nickname FROM users WHERE id=?", (user["user_id"],)) as c:
            row = await c.fetchone()
            name = row[0] if row else "unknown"
    finally:
        await db.close()

    reactions = await ReactionManager.add_reaction(message_id, user["user_id"], name, req.emoji)

    # 广播表情回应
    async with db.execute("SELECT group_id FROM messages WHERE id=?", (message_id,)) as c:
        msg_row = await c.fetchone()
    if msg_row:
        await ws_manager.broadcast_to_group(msg_row[0], {
            "type": "reaction_v2",
            "data": {
                "message_id": message_id,
                "user_id": user["user_id"],
                "user_name": name,
                "emoji": req.emoji,
                "action": "add",
                "reactions": reactions,
            }
        })

    return {"reactions": reactions}


@router.delete("/messages/{message_id}/reactions/v2/{emoji}")
async def remove_reaction_v2(message_id: str, emoji: str, user=Depends(get_current_user)):
    """移除表情回应"""
    reactions = await ReactionManager.remove_reaction(message_id, user["user_id"], emoji)

    db = await get_db()
    try:
        async with db.execute("SELECT group_id FROM messages WHERE id=?", (message_id,)) as c:
            msg_row = await c.fetchone()
        if msg_row:
            await ws_manager.broadcast_to_group(msg_row[0], {
                "type": "reaction_v2",
                "data": {
                    "message_id": message_id,
                    "user_id": user["user_id"],
                    "emoji": emoji,
                    "action": "remove",
                    "reactions": reactions,
                }
            })
    finally:
        await db.close()

    return {"reactions": reactions}


@router.get("/messages/{message_id}/reactions/v2")
async def get_reactions_v2(message_id: str, user=Depends(get_current_user)):
    """获取消息的表情回应"""
    reactions = await ReactionManager.get_reactions(message_id)
    return {"reactions": reactions}


# ==================== 拍一拍 ====================

@router.post("/groups/{group_id}/pat")
async def pat_user(group_id: str, req: PatReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT nickname FROM users WHERE id=?", (user["user_id"],)) as c:
            r = await c.fetchone()
            from_name = r[0] if r else "someone"
        async with db.execute("SELECT nickname FROM users WHERE id=?", (req.to_user_id,)) as c:
            r = await c.fetchone()
            to_name = r[0] if r else "someone"

        pat_id = gen_id()
        ts = now()
        await db.execute(
            "INSERT INTO pats (id,group_id,from_user_id,from_user_name,to_user_id,to_user_name,action,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (pat_id, group_id, user["user_id"], from_name, req.to_user_id, to_name, req.action, ts)
        )
        await db.commit()

        system_msg = f"{from_name} {req.action} {to_name}"
        await ws_manager.broadcast_to_group(group_id, {
            "type": "pat",
            "data": {"from": from_name, "to": to_name, "action": req.action, "group_id": group_id}
        })
        return {"message": system_msg}
    finally:
        await db.close()


# ==================== 收藏 ====================

@router.post("/favorites")
async def add_favorite(message_id: str = "", content: str = "", msg_type: str = "text",
                       media_url: str = "", source_name: str = "", user=Depends(get_current_user)):
    db = await get_db()
    try:
        fid = gen_id()
        await db.execute(
            "INSERT INTO favorites (id,user_id,message_id,content,msg_type,media_url,source_name,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (fid, user["user_id"], message_id, content, msg_type, media_url, source_name, now())
        )
        await db.commit()
        return {"id": fid}
    finally:
        await db.close()


@router.get("/favorites")
async def list_favorites(user=Depends(get_current_user)):
    db = await get_db()
    try:
        items = []
        async with db.execute(
            "SELECT id,content,msg_type,media_url,source_name,created_at FROM favorites WHERE user_id=? ORDER BY created_at DESC",
            (user["user_id"],)
        ) as cursor:
            async for row in cursor:
                items.append({
                    "id": row[0], "content": row[1], "msg_type": row[2],
                    "media_url": row[3], "source_name": row[4], "created_at": row[5],
                })
        return items
    finally:
        await db.close()


@router.delete("/favorites/{fav_id}")
async def delete_favorite(fav_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("DELETE FROM favorites WHERE id=? AND user_id=?", (fav_id, user["user_id"]))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


# ==================== 文件上传 ====================

@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "只能上传图片")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "图片不能超过10MB")
    if len(content) < 100:
        raise HTTPException(400, "文件内容过小")
    # Magic bytes 校验：验证文件确实是图片
    image_signatures = {
        b"\xff\xd8\xff": ".jpg",
        b"\x89PNG": ".png",
        b"GIF8": ".gif",
        b"RIFF": ".webp",  # WebP starts with RIFF
    }
    detected_ext = None
    for sig, ext in image_signatures.items():
        if content[:len(sig)] == sig:
            detected_ext = ext
            break
    if not detected_ext:
        raise HTTPException(400, "文件内容不是有效的图片格式")
    ext = Path(file.filename).suffix if file.filename else detected_ext
    if ext.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        ext = detected_ext
    filepath = f"data/uploads/{gen_id()}{ext}"
    with open(filepath, "wb") as f:
        f.write(content)
    return {"url": f"/api/uploads/{Path(filepath).name}", "filename": file.filename}


@router.post("/upload/file")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "文件不能超过50MB")
    ext = Path(file.filename).suffix
    filepath = f"data/uploads/{gen_id()}{ext}"
    with open(filepath, "wb") as f:
        f.write(content)
    return {
        "url": f"/api/uploads/{Path(filepath).name}",
        "filename": file.filename,
        "size": len(content),
    }


@router.get("/uploads/{filename}")
async def get_upload(filename: str):
    # 防止路径遍历攻击
    safe_name = Path(filename).name
    if not safe_name or safe_name.startswith("."):
        raise HTTPException(400, "无效的文件名")
    filepath = Path("data/uploads") / safe_name
    if not filepath.exists():
        raise HTTPException(404)
    ext = Path(filename).suffix.lower()
    types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".webp": "image/webp", ".mp4": "video/mp4",
        ".webm": "audio/webm", ".mp3": "audio/mpeg", ".pdf": "application/pdf",
        ".doc": "application/msword", ".docx": "application/vnd.openxmlformats",
        ".zip": "application/zip",
    }
    return FileResponse(filepath, media_type=types.get(ext, "application/octet-stream"))


# ==================== 红包 ====================

@router.post("/red-envelopes")
async def create_red_envelope(req: RedEnvelopeReq, user=Depends(get_current_user)):
    if req.amount <= 0 or req.amount > 200:
        raise HTTPException(400, "红包金额 0.01-200 元")
    if req.count < 1 or req.count > 100:
        raise HTTPException(400, "红包个数 1-100")
    db = await get_db()
    try:
        eid = gen_id()
        await db.execute(
            """INSERT INTO red_envelopes (id,sender_id,group_id,receiver_id,amount,count,greeting,status,remaining,remaining_count,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, user["user_id"], req.group_id, req.receiver_id,
             req.amount, req.count, req.greeting, "pending", req.amount, req.count, now())
        )
        await db.commit()

        # 广播红包消息
        if req.group_id:
            async with db.execute("SELECT nickname FROM users WHERE id=?", (user["user_id"],)) as c:
                r = await c.fetchone()
                name = r[0] if r else "someone"
            msg_id = gen_id()
            ts = now()
            await db.execute(
                "INSERT INTO messages (id,group_id,sender_id,sender_name,content,msg_type,created_at) VALUES (?,?,?,?,?,?,?)",
                (msg_id, req.group_id, user["user_id"], name, req.greeting, "red_envelope", ts)
            )
            await db.commit()
            await ws_manager.broadcast_to_group(req.group_id, {
                "type": "red_envelope",
                "data": {"id": eid, "sender": name, "greeting": req.greeting, "group_id": req.group_id}
            })

        return {"id": eid}
    finally:
        await db.close()


@router.post("/red-envelopes/{eid}/claim")
async def claim_red_envelope(eid: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT * FROM red_envelopes WHERE id=?", (eid,)) as c:
            env = await c.fetchone()
            if not env:
                raise HTTPException(404, "红包不存在")
            if env[7] != "pending":
                raise HTTPException(400, "红包已领完")
            if env[1] == user["user_id"]:
                raise HTTPException(400, "不能领自己的红包")

        # 检查是否已领
        async with db.execute(
            "SELECT id FROM red_envelope_claims WHERE envelope_id=? AND user_id=?",
            (eid, user["user_id"])
        ) as c:
            if await c.fetchone():
                raise HTTPException(400, "你已经领过了")

        # 随机金额
        remaining = env[8]
        count_left = env[9]
        if count_left <= 1:
            amount = round(remaining, 2)
        else:
            amount = round(random.uniform(0.01, remaining / count_left * 2), 2)
            amount = max(0.01, min(amount, remaining - 0.01 * (count_left - 1)))

        claim_id = gen_id()
        await db.execute(
            "INSERT INTO red_envelope_claims (id,envelope_id,user_id,amount,claimed_at) VALUES (?,?,?,?,?)",
            (claim_id, eid, user["user_id"], amount, now())
        )

        new_remaining = round(remaining - amount, 2)
        new_count = count_left - 1
        status = "completed" if new_count <= 0 else "pending"
        await db.execute(
            "UPDATE red_envelopes SET remaining=?,remaining_count=?,status=? WHERE id=?",
            (new_remaining, new_count, status, eid)
        )
        await db.commit()

        return {"amount": amount, "greeting": env[6], "sender_id": env[1]}
    finally:
        await db.close()


@router.get("/red-envelopes/{eid}")
async def get_red_envelope(eid: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT * FROM red_envelopes WHERE id=?", (eid,)) as c:
            env = await c.fetchone()
            if not env:
                raise HTTPException(404)

        claims = []
        async with db.execute("""
            SELECT rc.user_id, rc.amount, rc.claimed_at, COALESCE(u.nickname, 'unknown')
            FROM red_envelope_claims rc LEFT JOIN users u ON rc.user_id=u.id
            WHERE rc.envelope_id=? ORDER BY rc.claimed_at
        """, (eid,)) as cursor:
            async for row in cursor:
                claims.append({"user_id": row[0], "amount": row[1], "claimed_at": row[2], "nickname": row[3]})

        my_claim = [c for c in claims if c["user_id"] == user["user_id"]]
        return {
            "id": eid, "sender_id": env[1], "amount": env[4], "count": env[5],
            "greeting": env[6], "status": env[7], "remaining": env[8],
            "claims": claims, "my_claim": my_claim[0] if my_claim else None,
        }
    finally:
        await db.close()


# ==================== 家庭邀请码 ====================

import random
import string


def _gen_family_code() -> str:
    """生成6位家庭邀请码"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@router.get("/messages/{group_id}/search")
async def search_messages(group_id: str, q: str, limit: int = 20, user=Depends(get_current_user)):
    """在指定群聊中搜索消息内容，返回匹配的消息及上下文（前后各1条）"""
    if not q or not q.strip():
        raise HTTPException(400, "搜索关键词不能为空")
    db = await get_db()
    try:
        # 权限校验：必须是群成员
        async with db.execute(
            "SELECT 1 FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            if not await c.fetchone():
                raise HTTPException(403, "你不是该群成员")

        messages = []
        # 搜索匹配的消息
        async with db.execute(
            """SELECT id, group_id, sender_id, sender_name, sender_avatar, content, msg_type,
                     media_url, reply_to, reply_content, recalled, pinned, created_at
               FROM messages WHERE group_id=? AND content LIKE ? AND recalled=0
               ORDER BY created_at DESC LIMIT ?""",
            (group_id, f"%{q}%", limit)
        ) as cursor:
            async for row in cursor:
                messages.append({
                    "id": row[0], "group_id": row[1], "sender_id": row[2],
                    "sender_name": row[3], "sender_avatar": row[4] or "",
                    "content": row[5], "msg_type": row[6], "media_url": row[7] or "",
                    "reply_to": row[8] or "", "reply_content": row[9] or "",
                    "recalled": bool(row[10]), "pinned": bool(row[11]),
                    "created_at": row[12],
                })

        # 为每条匹配消息获取上下文（前后各1条）
        results = []
        for msg in messages:
            context = {"before": None, "target": msg, "after": None}
            # 前一条
            async with db.execute(
                """SELECT id, sender_name, content, msg_type, created_at
                   FROM messages WHERE group_id=? AND created_at<?
                   ORDER BY created_at DESC LIMIT 1""",
                (group_id, msg["created_at"])
            ) as c:
                prev = await c.fetchone()
                if prev:
                    context["before"] = {
                        "id": prev[0], "sender_name": prev[1], "content": prev[2],
                        "msg_type": prev[3], "created_at": prev[4],
                    }
            # 后一条
            async with db.execute(
                """SELECT id, sender_name, content, msg_type, created_at
                   FROM messages WHERE group_id=? AND created_at>?
                   ORDER BY created_at ASC LIMIT 1""",
                (group_id, msg["created_at"])
            ) as c:
                nxt = await c.fetchone()
                if nxt:
                    context["after"] = {
                        "id": nxt[0], "sender_name": nxt[1], "content": nxt[2],
                        "msg_type": nxt[3], "created_at": nxt[4],
                    }
            results.append(context)

        return {"results": results, "total": len(results)}
    finally:
        await db.close()


# ==================== 群公告管理 ====================

@router.get("/groups/{group_id}/announcement")
async def get_announcement(group_id: str, user=Depends(get_current_user)):
    """获取群公告"""
    db = await get_db()
    try:
        # 权限校验：必须是群成员
        async with db.execute(
            "SELECT 1 FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            if not await c.fetchone():
                raise HTTPException(403, "你不是该群成员")

        async with db.execute(
            "SELECT announcement FROM groups WHERE id=?",
            (group_id,)
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "群不存在")
            return {"group_id": group_id, "announcement": row[0] or ""}
    finally:
        await db.close()


@router.put("/groups/{group_id}/announcement")
async def update_announcement(group_id: str, req: UpdateAnnouncementReq, user=Depends(get_current_user)):
    """更新群公告（仅群主/管理员）"""
    db = await get_db()
    try:
        # 权限校验
        async with db.execute(
            "SELECT role FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(403, "你不是群成员")
            if row[0] not in ("owner", "admin"):
                raise HTTPException(403, "只有群主或管理员可以更新公告")

        # 更新公告文本
        await db.execute(
            "UPDATE groups SET announcement=?, updated_at=? WHERE id=?",
            (req.content, now(), group_id)
        )

        # 处理置顶消息：将指定消息标记为 pinned
        if req.pinned_message_ids:
            for mid in req.pinned_message_ids:
                async with db.execute(
                    "SELECT group_id FROM messages WHERE id=?",
                    (mid,)
                ) as mc:
                    msg_row = await mc.fetchone()
                    if msg_row and msg_row[0] == group_id:
                        await db.execute(
                            "UPDATE messages SET pinned=1 WHERE id=?",
                            (mid,)
                        )

        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


# ==================== 群置顶消息 ====================

@router.post("/groups/{group_id}/pin/{message_id}")
async def pin_to_group(group_id: str, message_id: str, user=Depends(get_current_user)):
    """将消息置顶到群公告（仅群主/管理员）"""
    db = await get_db()
    try:
        # 权限校验
        async with db.execute(
            "SELECT role FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(403, "你不是群成员")
            if row[0] not in ("owner", "admin"):
                raise HTTPException(403, "只有群主或管理员可以置顶消息")

        # 验证消息属于该群
        async with db.execute(
            "SELECT group_id FROM messages WHERE id=?",
            (message_id,)
        ) as c:
            msg_row = await c.fetchone()
            if not msg_row:
                raise HTTPException(404, "消息不存在")
            if msg_row[0] != group_id:
                raise HTTPException(400, "消息不属于该群")

        await db.execute("UPDATE messages SET pinned=1 WHERE id=?", (message_id,))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.get("/groups/{group_id}/pinned")
async def get_group_pinned(group_id: str, user=Depends(get_current_user)):
    """获取群置顶消息"""
    db = await get_db()
    try:
        # 权限校验：必须是群成员
        async with db.execute(
            "SELECT 1 FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            if not await c.fetchone():
                raise HTTPException(403, "你不是该群成员")

        msgs = []
        async with db.execute(
            """SELECT id, sender_id, sender_name, content, msg_type, created_at
               FROM messages WHERE group_id=? AND pinned=1
               ORDER BY created_at DESC""",
            (group_id,)
        ) as cursor:
            async for row in cursor:
                msgs.append({
                    "id": row[0], "sender_id": row[1], "sender_name": row[2],
                    "content": row[3], "msg_type": row[4], "created_at": row[5],
                })
        return msgs
    finally:
        await db.close()


# ==================== 消息删除（仅对自己隐藏） ====================

@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, user=Depends(get_current_user)):
    """删除消息（仅对自己隐藏，其他人仍可见）"""
    db = await get_db()
    try:
        # 验证消息存在
        async with db.execute(
            "SELECT id FROM messages WHERE id=?",
            (message_id,)
        ) as c:
            if not await c.fetchone():
                raise HTTPException(404, "消息不存在")

        # 记录隐藏关系（幂等，忽略重复）
        await db.execute(
            "INSERT OR IGNORE INTO hidden_messages (message_id, user_id, hidden_at) VALUES (?,?,?)",
            (message_id, user["user_id"], now())
        )
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


# ==================== 用户在线状态 ====================

@router.get("/users/{user_id}/online")
async def get_user_online(user_id: str, user=Depends(get_current_user)):
    """查询用户在线状态"""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT online_status, last_seen FROM users WHERE id=?",
            (user_id,)
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "用户不存在")
            return {
                "user_id": user_id,
                "online_status": row[0] or "offline",
                "last_seen": row[1] or 0,
            }
    finally:
        await db.close()


@router.post("/groups/{group_id}/invite-code")
async def generate_invite_code(group_id: str, user=Depends(get_current_user)):
    """生成或刷新家庭邀请码"""
    db = await get_db()
    try:
        # 检查是否是群主或管理员
        async with db.execute(
            "SELECT role FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(403, "你不是群成员")

        # 检查是否已有有效邀请码
        async with db.execute(
            "SELECT family_code FROM groups WHERE id=?",
            (group_id,)
        ) as c:
            row = await c.fetchone()
            if row and row[0]:
                return {"code": row[0]}

        # 生成新邀请码
        code = _gen_family_code()
        await db.execute(
            "UPDATE groups SET family_code=? WHERE id=?",
            (code, group_id)
        )
        await db.commit()
        return {"code": code}
    finally:
        await db.close()


@router.post("/family/join")
async def join_by_code(code: str, user=Depends(get_current_user)):
    """通过邀请码加入家庭群"""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id, name FROM groups WHERE family_code=?",
            (code.upper(),)
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "邀请码无效")

        group_id, group_name = row[0], row[1]

        # 检查是否已在群中
        async with db.execute(
            "SELECT 1 FROM group_members WHERE group_id=? AND user_id=?",
            (group_id, user["user_id"])
        ) as c:
            if await c.fetchone():
                return {"group_id": group_id, "group_name": group_name, "already_joined": True}

        # 加入群
        ts = now()
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
            (group_id, user["user_id"], "member", ts)
        )
        # 同时加入用户的 Agent
        async with db.execute(
            "SELECT agent_id FROM users WHERE id=?",
            (user["user_id"],)
        ) as c:
            agent_row = await c.fetchone()
            if agent_row and agent_row[0]:
                await db.execute(
                    "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
                    (group_id, agent_row[0], "agent", ts)
                )
        await db.commit()

        # 广播加入消息
        async with db.execute(
            "SELECT nickname FROM users WHERE id=?",
            (user["user_id"],)
        ) as c:
            u = await c.fetchone()
            nickname = u[0] if u else "新成员"

        msg_id = gen_id()
        await db.execute(
            "INSERT INTO messages (id,group_id,sender_id,sender_name,content,msg_type,created_at) VALUES (?,?,?,?,?,?,?)",
            (msg_id, group_id, "system", "系统", f"{nickname} 加入了群聊", "system", ts)
        )
        await db.commit()

        await ws_manager.broadcast_to_group(group_id, {
            "type": "system",
            "data": {"message": f"{nickname} 加入了群聊", "group_id": group_id}
        })

        return {"group_id": group_id, "group_name": group_name, "already_joined": False}
    finally:
        await db.close()


@router.get("/family/check-code")
async def check_invite_code(code: str):
    """检查邀请码是否有效（无需登录）"""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id, name, avatar FROM groups WHERE family_code=?",
            (code.upper(),)
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "邀请码无效")
            # 获取成员数
            async with db.execute(
                "SELECT COUNT(*) FROM group_members WHERE group_id=?",
                (row[0],)
            ) as mc:
                count = (await mc.fetchone())[0]
            return {"group_id": row[0], "name": row[1], "avatar": row[2], "member_count": count}
    finally:
        await db.close()
