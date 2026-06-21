"""搜索路由 - 全局搜索"""
from fastapi import APIRouter, Depends
from ..core.auth import get_current_user
from ..models.database import get_db

router = APIRouter(prefix="/api/search")


@router.get("")
async def global_search(q: str, user=Depends(get_current_user)):
    """全局搜索：消息 + 联系人 + 群组"""
    db = await get_db()
    try:
        results = {"messages": [], "contacts": [], "groups": []}

        # 搜索联系人
        async with db.execute(
            "SELECT id,nickname,avatar,avatar_url,signature FROM users WHERE (nickname LIKE ? OR username LIKE ?) AND id!=? LIMIT 10",
            (f"%{q}%", f"%{q}%", user["user_id"])
        ) as cursor:
            async for row in cursor:
                results["contacts"].append({
                    "id": row[0], "nickname": row[1], "avatar": row[2] or "😀",
                    "avatar_url": row[3] or "", "signature": row[4] or "",
                })

        # 搜索群组
        async with db.execute("""
            SELECT g.id, g.name, g.avatar FROM groups g
            JOIN group_members gm ON g.id=gm.group_id
            WHERE gm.user_id=? AND g.name LIKE ? LIMIT 10
        """, (user["user_id"], f"%{q}%")) as cursor:
            async for row in cursor:
                results["groups"].append({"id": row[0], "name": row[1], "avatar": row[2]})

        # 搜索消息（只搜用户所在的群）
        async with db.execute("""
            SELECT m.id, m.group_id, m.sender_name, m.content, m.created_at, g.name
            FROM messages m
            JOIN groups g ON m.group_id=g.id
            JOIN group_members gm ON m.group_id=gm.group_id
            WHERE gm.user_id=? AND m.content LIKE ? AND m.recalled=0
            ORDER BY m.created_at DESC LIMIT 20
        """, (user["user_id"], f"%{q}%")) as cursor:
            async for row in cursor:
                results["messages"].append({
                    "id": row[0], "group_id": row[1], "sender_name": row[2],
                    "content": row[3][:100], "created_at": row[4], "group_name": row[5],
                })

        return results
    finally:
        await db.close()
