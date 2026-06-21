"""好友/通讯录路由"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..core.auth import get_current_user
from ..models.database import get_db, gen_id, now

router = APIRouter(prefix="/api")


class FriendRequestReq(BaseModel):
    to_user_id: str
    message: str = ""


class HandleRequestReq(BaseModel):
    request_id: str
    action: str  # accept / reject


class UpdateRemarkReq(BaseModel):
    friend_id: str
    remark: str


@router.get("/friends")
async def list_friends(user=Depends(get_current_user)):
    db = await get_db()
    try:
        friends = []
        async with db.execute("""
            SELECT u.id, u.nickname, u.avatar, u.avatar_url, u.signature,
                   u.online_status, u.last_seen, f.remark
            FROM friendships f
            JOIN users u ON f.friend_id=u.id
            WHERE f.user_id=? AND f.status='accepted'
            ORDER BY u.online_status DESC, u.last_seen DESC
        """, (user["user_id"],)) as cursor:
            async for row in cursor:
                friends.append({
                    "id": row[0], "nickname": row[1], "avatar": row[2] or "😀",
                    "avatar_url": row[3] or "", "signature": row[4] or "",
                    "online_status": row[5] or "offline", "last_seen": row[6],
                    "remark": row[7] or "",
                })
        return friends
    finally:
        await db.close()


@router.post("/friends/request")
async def send_friend_request(req: FriendRequestReq, user=Depends(get_current_user)):
    if req.to_user_id == user["user_id"]:
        raise HTTPException(400, "不能添加自己")
    db = await get_db()
    try:
        # 检查是否已是好友
        async with db.execute(
            "SELECT status FROM friendships WHERE user_id=? AND friend_id=?",
            (user["user_id"], req.to_user_id)
        ) as c:
            if await c.fetchone():
                raise HTTPException(400, "已经是好友了")

        # 检查是否有待处理请求
        async with db.execute(
            "SELECT id FROM friend_requests WHERE from_user_id=? AND to_user_id=? AND status='pending'",
            (user["user_id"], req.to_user_id)
        ) as c:
            if await c.fetchone():
                raise HTTPException(400, "已发送过请求")

        rid = gen_id()
        await db.execute(
            "INSERT INTO friend_requests (id,from_user_id,to_user_id,message,status,created_at) VALUES (?,?,?,?,?,?)",
            (rid, user["user_id"], req.to_user_id, req.message, "pending", now())
        )
        await db.commit()
        return {"id": rid}
    finally:
        await db.close()


@router.get("/friends/requests")
async def list_friend_requests(user=Depends(get_current_user)):
    db = await get_db()
    try:
        reqs = []
        async with db.execute("""
            SELECT fr.id, fr.from_user_id, fr.message, fr.status, fr.created_at,
                   u.nickname, u.avatar, u.avatar_url
            FROM friend_requests fr
            JOIN users u ON fr.from_user_id=u.id
            WHERE fr.to_user_id=? AND fr.status='pending'
            ORDER BY fr.created_at DESC
        """, (user["user_id"],)) as cursor:
            async for row in cursor:
                reqs.append({
                    "id": row[0], "from_user_id": row[1], "message": row[2],
                    "status": row[3], "created_at": row[4],
                    "nickname": row[5], "avatar": row[6] or "😀", "avatar_url": row[7] or "",
                })
        return reqs
    finally:
        await db.close()


@router.post("/friends/requests/handle")
async def handle_friend_request(req: HandleRequestReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute(
            "SELECT from_user_id,to_user_id FROM friend_requests WHERE id=? AND to_user_id=? AND status='pending'",
            (req.request_id, user["user_id"])
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "请求不存在")

        from_id, to_id = row[0], row[1]
        status = "accepted" if req.action == "accept" else "rejected"
        await db.execute("UPDATE friend_requests SET status=? WHERE id=?", (status, req.request_id))

        if req.action == "accept":
            ts = now()
            await db.execute(
                "INSERT OR IGNORE INTO friendships (user_id,friend_id,status,created_at) VALUES (?,?,?,?)",
                (from_id, to_id, "accepted", ts)
            )
            await db.execute(
                "INSERT OR IGNORE INTO friendships (user_id,friend_id,status,created_at) VALUES (?,?,?,?)",
                (to_id, from_id, "accepted", ts)
            )
        await db.commit()
        return {"status": status}
    finally:
        await db.close()


@router.delete("/friends/{friend_id}")
async def delete_friend(friend_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("DELETE FROM friendships WHERE user_id=? AND friend_id=?", (user["user_id"], friend_id))
        await db.execute("DELETE FROM friendships WHERE user_id=? AND friend_id=?", (friend_id, user["user_id"]))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.put("/friends/remark")
async def update_remark(req: UpdateRemarkReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE friendships SET remark=? WHERE user_id=? AND friend_id=?",
            (req.remark, user["user_id"], req.friend_id)
        )
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.get("/contacts/search")
async def search_contacts(q: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        users = []
        async with db.execute(
            "SELECT id,nickname,avatar,avatar_url,signature FROM users WHERE (nickname LIKE ? OR username LIKE ? OR email LIKE ?) AND id!=? LIMIT 20",
            (f"%{q}%", f"%{q}%", f"%{q}%", user["user_id"])
        ) as cursor:
            async for row in cursor:
                users.append({
                    "id": row[0], "nickname": row[1], "avatar": row[2] or "😀",
                    "avatar_url": row[3] or "", "signature": row[4] or "",
                })
        return users
    finally:
        await db.close()
