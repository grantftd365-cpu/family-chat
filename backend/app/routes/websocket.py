"""WebSocket 路由 - 独立注册避免 reload 模式下路由丢失"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from ..core.auth import get_ws_user
from ..core.websocket import ws_manager
from ..models.database import get_db, now

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
