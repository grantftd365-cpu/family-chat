"""通知路由"""
from fastapi import APIRouter, Depends
from ..core.auth import get_current_user
from ..models.database import get_db, gen_id, now

router = APIRouter(prefix="/api/notifications")


@router.get("")
async def list_notifications(unread_only: bool = False, user=Depends(get_current_user)):
    db = await get_db()
    try:
        items = []
        sql = "SELECT id,type,title,content,ref_id,is_read,created_at FROM notifications WHERE user_id=?"
        params = [user["user_id"]]
        if unread_only:
            sql += " AND is_read=0"
        sql += " ORDER BY created_at DESC LIMIT 50"

        async with db.execute(sql, params) as cursor:
            async for row in cursor:
                items.append({
                    "id": row[0], "type": row[1], "title": row[2],
                    "content": row[3], "ref_id": row[4],
                    "is_read": bool(row[5]), "created_at": row[6],
                })
        return items
    finally:
        await db.close()


@router.get("/unread-count")
async def unread_count(user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
            (user["user_id"],)
        ) as c:
            row = await c.fetchone()
            return {"count": row[0] if row else 0}
    finally:
        await db.close()


@router.post("/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user["user_id"],))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.post("/{notif_id}/read")
async def mark_read(notif_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (notif_id, user["user_id"]))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


async def create_notification(user_id: str, ntype: str, title: str, content: str, ref_id: str = ""):
    """创建通知（内部函数）"""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO notifications (id,user_id,type,title,content,ref_id,is_read,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (gen_id(), user_id, ntype, title, content, ref_id, 0, now())
        )
        await db.commit()
    finally:
        await db.close()
