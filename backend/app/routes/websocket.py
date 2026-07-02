"""WebSocket 路由 - 消息必达 + 已读回执 + 表情回应"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from ..core.auth import get_ws_user
from ..core.websocket import ws_manager
from ..models.database import get_db, now
from ..services.family import get_group_member_role
from ..services.delivery import MessageDelivery, ReactionManager
from ..services.calling import handle_call_signaling

router = APIRouter()


@router.websocket("/ws")
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

    # 加入所有群
    try:
        async with db.execute("SELECT group_id FROM group_members WHERE user_id=?", (user_id,)) as c:
            async for row in c:
                await ws_manager.join_group(user_id, row[0])
    finally:
        await db.close()

    # 消息必达：连接成功后立即推送未送达消息
    try:
        undelivered = await MessageDelivery.get_undelivered_messages(user_id, limit=200)
        if undelivered:
            logger.info(f"用户 {user_id} 上线，推送 {len(undelivered)} 条未送达消息")
            for msg in undelivered:
                await websocket.send_json({
                    "type": "message",
                    "data": msg,
                })
                # 标记为已送达
                await MessageDelivery.mark_delivered(msg["id"], user_id)

            # 通知客户端补发完成
            await websocket.send_json({
                "type": "sync_complete",
                "data": {"count": len(undelivered)},
            })
    except Exception as e:
        logger.error(f"推送未送达消息失败: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                async def can_use_group(group_id: str) -> bool:
                    if not group_id:
                        return False
                    db_check = await get_db()
                    try:
                        return bool(await get_group_member_role(db_check, group_id, user_id))
                    finally:
                        await db_check.close()

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "typing":
                    if not await can_use_group(msg.get("group_id", "")):
                        continue
                    await ws_manager.broadcast_to_group(
                        msg.get("group_id", ""),
                        {"type": "typing", "data": {"user_id": user_id, "user_name": msg.get("name", "")}},
                        exclude_user=user_id
                    )

                elif msg_type == "ack":
                    # 客户端确认收到消息
                    message_ids = msg.get("message_ids", [])
                    for mid in message_ids:
                        await MessageDelivery.mark_delivered(mid, user_id)

                elif msg_type == "read":
                    # 客户端标记消息已读
                    group_id = msg.get("group_id", "")
                    before = msg.get("before", 0)
                    if group_id and await can_use_group(group_id):
                        await MessageDelivery.mark_batch_read(group_id, user_id, before)
                        # 广播已读状态
                        await ws_manager.broadcast_to_group(group_id, {
                            "type": "read",
                            "data": {
                                "user_id": user_id,
                                "group_id": group_id,
                                "before": before,
                            }
                        }, exclude_user=user_id)

                elif msg_type == "read_single":
                    # 标记单条消息已读
                    message_id = msg.get("message_id", "")
                    if message_id:
                        await MessageDelivery.mark_read(message_id, user_id)

                elif msg_type == "reaction":
                    # 表情回应
                    message_id = msg.get("message_id", "")
                    emoji = msg.get("emoji", "")
                    action = msg.get("action", "add")  # add / remove
                    group_id = msg.get("group_id", "")

                    if message_id and emoji and await can_use_group(group_id):
                        db_msg = await get_db()
                        try:
                            async with db_msg.execute("SELECT group_id FROM messages WHERE id=?", (message_id,)) as mc:
                                msg_row = await mc.fetchone()
                            if not msg_row or msg_row[0] != group_id:
                                continue
                        finally:
                            await db_msg.close()
                        async with (await get_db()) as db2:
                            async with db2.execute("SELECT nickname FROM users WHERE id=?", (user_id,)) as c:
                                row = await c.fetchone()
                                user_name = row[0] if row else "unknown"

                        if action == "add":
                            reactions = await ReactionManager.add_reaction(
                                message_id, user_id, user_name, emoji
                            )
                        else:
                            reactions = await ReactionManager.remove_reaction(
                                message_id, user_id, emoji
                            )

                        if group_id:
                            await ws_manager.broadcast_to_group(group_id, {
                                "type": "reaction",
                                "data": {
                                    "message_id": message_id,
                                    "user_id": user_id,
                                    "user_name": user_name,
                                    "emoji": emoji,
                                    "action": action,
                                    "reactions": reactions,
                                }
                            })

                elif msg_type == "call":
                    # WebRTC 通话信令
                    await handle_call_signaling(user_id, msg)

            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.error(f"WebSocket 消息处理错误: {e}")

    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, websocket)
        db = await get_db()
        await db.execute("UPDATE users SET online_status='offline', last_seen=? WHERE id=?", (now(), user_id))
        await db.commit()
        await db.close()
