"""朋友圈路由"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from ..core.auth import get_current_user
from ..models.database import get_db, gen_id, now
import json

router = APIRouter(prefix="/api/moments")


class CreateMomentReq(BaseModel):
    content: str = ""
    images: list = []
    location: str = ""
    visibility: str = "all"


class CommentReq(BaseModel):
    content: str


@router.get("")
async def list_moments(before: float = 0, limit: int = 20, user=Depends(get_current_user)):
    db = await get_db()
    try:
        # 获取好友列表
        friend_ids = [user["user_id"]]
        async with db.execute("SELECT friend_id FROM friendships WHERE user_id=?", (user["user_id"],)) as c:
            async for row in c:
                friend_ids.append(row[0])

        placeholders = ",".join("?" * len(friend_ids))
        if before > 0:
            sql = f"""SELECT m.*, u.nickname, u.avatar, u.avatar_url
                      FROM moments m JOIN users u ON m.user_id=u.id
                      WHERE m.user_id IN ({placeholders}) AND m.created_at<?
                      ORDER BY m.created_at DESC LIMIT ?"""
            params = (*friend_ids, before, limit)
        else:
            sql = f"""SELECT m.*, u.nickname, u.avatar, u.avatar_url
                      FROM moments m JOIN users u ON m.user_id=u.id
                      WHERE m.user_id IN ({placeholders})
                      ORDER BY m.created_at DESC LIMIT ?"""
            params = (*friend_ids, limit)

        moments = []
        async with db.execute(sql, params) as cursor:
            async for row in cursor:
                mid = row[0]
                # 获取点赞
                likes = []
                async with db.execute(
                    "SELECT user_id,user_name FROM moment_interactions WHERE moment_id=? AND interaction_type='like'",
                    (mid,)
                ) as lc:
                    async for lr in lc:
                        likes.append({"user_id": lr[0], "user_name": lr[1]})

                # 获取评论
                comments = []
                async with db.execute(
                    "SELECT user_id,user_name,content,created_at FROM moment_interactions WHERE moment_id=? AND interaction_type='comment' ORDER BY created_at",
                    (mid,)
                ) as cc:
                    async for cr in cc:
                        comments.append({"user_id": cr[0], "user_name": cr[1], "content": cr[2], "created_at": cr[3]})

                my_like = any(l["user_id"] == user["user_id"] for l in likes)

                moments.append({
                    "id": mid, "user_id": row[1], "content": row[2],
                    "images": json.loads(row[3]) if row[3] else [],
                    "location": row[4], "like_count": row[6], "comment_count": row[7],
                    "created_at": row[8],
                    "nickname": row[9], "avatar": row[10] or "😀", "avatar_url": row[11] or "",
                    "likes": likes, "comments": comments, "my_like": my_like,
                })
        return moments
    finally:
        await db.close()


@router.post("")
async def create_moment(req: CreateMomentReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        mid = gen_id()
        await db.execute(
            "INSERT INTO moments (id,user_id,content,images,location,visibility,created_at) VALUES (?,?,?,?,?,?,?)",
            (mid, user["user_id"], req.content, json.dumps(req.images, ensure_ascii=False),
             req.location, req.visibility, now())
        )
        await db.commit()
        return {"id": mid}
    finally:
        await db.close()


@router.delete("/{moment_id}")
async def delete_moment(moment_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        await db.execute("DELETE FROM moments WHERE id=? AND user_id=?", (moment_id, user["user_id"]))
        await db.execute("DELETE FROM moment_interactions WHERE moment_id=?", (moment_id,))
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.post("/{moment_id}/like")
async def like_moment(moment_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT nickname FROM users WHERE id=?", (user["user_id"],)) as c:
            r = await c.fetchone()
            name = r[0] if r else "unknown"

        # 检查是否已点赞
        async with db.execute(
            "SELECT id FROM moment_interactions WHERE moment_id=? AND user_id=? AND interaction_type='like'",
            (moment_id, user["user_id"])
        ) as c:
            existing = await c.fetchone()
            if existing:
                # 取消点赞
                await db.execute("DELETE FROM moment_interactions WHERE id=?", (existing[0],))
                await db.execute("UPDATE moments SET like_count=like_count-1 WHERE id=?", (moment_id,))
                await db.commit()
                return {"action": "unliked"}

        iid = gen_id()
        await db.execute(
            "INSERT INTO moment_interactions (id,moment_id,user_id,user_name,interaction_type,created_at) VALUES (?,?,?,?,?,?)",
            (iid, moment_id, user["user_id"], name, "like", now())
        )
        await db.execute("UPDATE moments SET like_count=like_count+1 WHERE id=?", (moment_id,))
        await db.commit()
        return {"action": "liked"}
    finally:
        await db.close()


@router.post("/{moment_id}/comment")
async def comment_moment(moment_id: str, req: CommentReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute("SELECT nickname FROM users WHERE id=?", (user["user_id"],)) as c:
            r = await c.fetchone()
            name = r[0] if r else "unknown"

        iid = gen_id()
        await db.execute(
            "INSERT INTO moment_interactions (id,moment_id,user_id,user_name,interaction_type,content,created_at) VALUES (?,?,?,?,?,?,?)",
            (iid, moment_id, user["user_id"], name, "comment", req.content, now())
        )
        await db.execute("UPDATE moments SET comment_count=comment_count+1 WHERE id=?", (moment_id,))
        await db.commit()
        return {"id": iid}
    finally:
        await db.close()


@router.post("/upload")
async def upload_moment_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "只能上传图片")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "图片不能超过10MB")
    from pathlib import Path
    ext = Path(file.filename).suffix or ".jpg"
    filepath = f"data/uploads/moment_{gen_id()}{ext}"
    with open(filepath, "wb") as f:
        f.write(content)
    return {"url": f"/api/uploads/{Path(filepath).name}"}
