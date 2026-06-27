"""搜索路由 - 全局搜索（增强版）"""
from fastapi import APIRouter, Depends, Query
from ..core.auth import get_current_user
from ..models.database import get_db

router = APIRouter(prefix="/api/search")


@router.get("")
async def global_search(
    q: str,
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(get_current_user),
):
    """全局搜索：消息 + 联系人 + 群组 + 朋友圈，返回分组结果"""
    if not q or not q.strip():
        return {"messages": [], "contacts": [], "groups": [], "moments": []}

    db = await get_db()
    try:
        results = {"messages": [], "contacts": [], "groups": [], "moments": []}
        keyword = f"%{q}%"

        # 搜索联系人
        async with db.execute(
            """SELECT id, nickname, avatar, avatar_url, signature
               FROM users
               WHERE (nickname LIKE ? OR username LIKE ?) AND id!=?
               LIMIT ?""",
            (keyword, keyword, user["user_id"], limit),
        ) as cursor:
            async for row in cursor:
                results["contacts"].append({
                    "id": row[0], "nickname": row[1], "avatar": row[2] or "😀",
                    "avatar_url": row[3] or "", "signature": row[4] or "",
                })

        # 搜索群组
        async with db.execute(
            """SELECT g.id, g.name, g.avatar, g.description,
                      (SELECT COUNT(*) FROM group_members WHERE group_id=g.id) as member_count
               FROM groups g
               JOIN group_members gm ON g.id=gm.group_id
               WHERE gm.user_id=? AND g.name LIKE ?
               LIMIT ?""",
            (user["user_id"], keyword, limit),
        ) as cursor:
            async for row in cursor:
                results["groups"].append({
                    "id": row[0], "name": row[1], "avatar": row[2],
                    "description": row[3] or "", "member_count": row[4],
                })

        # 搜索消息（只搜用户所在的群，排除已隐藏的消息）
        async with db.execute(
            """SELECT m.id, m.group_id, m.sender_id, m.sender_name, m.content,
                      m.msg_type, m.created_at, g.name
               FROM messages m
               JOIN groups g ON m.group_id=g.id
               JOIN group_members gm ON m.group_id=gm.group_id
               LEFT JOIN hidden_messages hm ON m.id=hm.message_id AND hm.user_id=?
               WHERE gm.user_id=? AND m.content LIKE ? AND m.recalled=0 AND hm.message_id IS NULL
               ORDER BY m.created_at DESC
               LIMIT ?""",
            (user["user_id"], user["user_id"], keyword, limit),
        ) as cursor:
            async for row in cursor:
                results["messages"].append({
                    "id": row[0], "group_id": row[1], "sender_id": row[2],
                    "sender_name": row[3], "content": row[4][:200],
                    "msg_type": row[5], "created_at": row[6], "group_name": row[7],
                })

        # 搜索朋友圈（好友可见）
        # 先获取好友列表
        friend_ids = [user["user_id"]]
        async with db.execute(
            "SELECT friend_id FROM friendships WHERE user_id=?",
            (user["user_id"],),
        ) as c:
            async for row in c:
                friend_ids.append(row[0])

        if friend_ids:
            placeholders = ",".join("?" * len(friend_ids))
            async with db.execute(
                f"""SELECT m.id, m.user_id, m.content, m.images, m.created_at,
                           u.nickname, u.avatar, u.avatar_url
                    FROM moments m
                    JOIN users u ON m.user_id=u.id
                    WHERE m.user_id IN ({placeholders}) AND m.content LIKE ?
                    ORDER BY m.created_at DESC
                    LIMIT ?""",
                (*friend_ids, keyword, limit),
            ) as cursor:
                async for row in cursor:
                    import json
                    results["moments"].append({
                        "id": row[0], "user_id": row[1], "content": row[2][:200],
                        "images": json.loads(row[3]) if row[3] else [],
                        "created_at": row[4],
                        "nickname": row[5], "avatar": row[6] or "😀",
                        "avatar_url": row[7] or "",
                    })

        return results
    finally:
        await db.close()
