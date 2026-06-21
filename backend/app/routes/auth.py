"""认证路由 - 登录/注册/个人信息"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
from loguru import logger

from ..core.auth import hash_password, verify_password, create_token, get_current_user
from ..models.database import get_db, gen_id, now

router = APIRouter(prefix="/api")


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


class UpdateProfileReq(BaseModel):
    nickname: str = ""
    avatar: str = ""
    signature: str = ""
    gender: str = ""
    region: str = ""


@router.post("/register")
async def register(req: RegisterReq):
    from ..main import agent_manager
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
            """INSERT INTO users (id,email,username,nickname,password_hash,avatar,role,agent_id,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, req.email, req.username, req.nickname,
             hash_password(req.password), req.avatar, "member", "", ts, ts)
        )

        # 创建数字人分身
        agent_id = f"agent_{user_id}"
        agent_config = {
            "id": agent_id, "user_id": user_id, "name": req.nickname,
            "avatar": req.avatar, "role_in_family": req.role_in_family,
            "backstory": f"{req.nickname}的数字分身",
            "speaking_style": "待炼化 - 通过聊天记录或语音训练",
        }
        await agent_manager.create_agent(agent_config, _db=db)
        await db.execute("UPDATE users SET agent_id=? WHERE id=?", (agent_id, user_id))

        # 加入默认群
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
            ("family_default", user_id, "member", ts)
        )
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
            ("family_default", agent_id, "agent", ts)
        )
        await db.commit()

        token = create_token(user_id, req.email)
        return {
            "token": token,
            "user": {"id": user_id, "email": req.email, "username": req.username,
                     "nickname": req.nickname, "avatar": req.avatar, "agent_id": agent_id},
        }
    finally:
        await db.close()


@router.post("/login")
async def login(req: LoginReq):
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id,username,nickname,avatar,agent_id,password_hash,signature FROM users WHERE email=?",
            (req.email,)
        ) as c:
            row = await c.fetchone()
            if not row or not verify_password(req.password, row[5]):
                raise HTTPException(401, "邮箱或密码错误")

        # 更新在线状态
        await db.execute("UPDATE users SET online_status='online', last_seen=? WHERE id=?", (now(), row[0]))
        await db.commit()

        token = create_token(row[0], req.email)
        return {
            "token": token,
            "user": {"id": row[0], "email": req.email, "username": row[1],
                     "nickname": row[2], "avatar": row[3] or "😀",
                     "agent_id": row[4] or "", "signature": row[6] or ""},
        }
    finally:
        await db.close()


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id,username,nickname,avatar,agent_id,signature,gender,region,email FROM users WHERE id=?",
            (user["user_id"],)
        ) as c:
            row = await c.fetchone()
            if not row:
                raise HTTPException(404, "用户不存在")
            return {
                "id": row[0], "username": row[1], "nickname": row[2],
                "avatar": row[3] or "😀", "agent_id": row[4] or "",
                "signature": row[5] or "", "gender": row[6] or "",
                "region": row[7] or "", "email": row[8],
            }
    finally:
        await db.close()


@router.put("/me")
async def update_me(req: UpdateProfileReq, user=Depends(get_current_user)):
    db = await get_db()
    try:
        updates, params = [], []
        if req.nickname:
            updates.append("nickname=?"); params.append(req.nickname)
        if req.avatar:
            updates.append("avatar=?"); params.append(req.avatar)
        if req.signature is not None:
            updates.append("signature=?"); params.append(req.signature)
        if req.gender:
            updates.append("gender=?"); params.append(req.gender)
        if req.region:
            updates.append("region=?"); params.append(req.region)
        if not updates:
            return {"status": "ok"}
        updates.append("updated_at=?"); params.append(now())
        params.append(user["user_id"])
        await db.execute(f"UPDATE users SET {','.join(updates)} WHERE id=?", params)
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "只能上传图片")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "图片不能超过5MB")
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"avatar_{user['user_id']}{ext}"
    filepath = f"data/avatars/{filename}"
    with open(filepath, "wb") as f:
        f.write(content)
    url = f"/api/avatars/{filename}"
    db = await get_db()
    await db.execute("UPDATE users SET avatar_url=?, updated_at=? WHERE id=?", (url, now(), user["user_id"]))
    await db.commit()
    await db.close()
    return {"url": url}


@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    from fastapi.responses import FileResponse
    filepath = f"data/avatars/{filename}"
    if not Path(filepath).exists():
        raise HTTPException(404)
    return FileResponse(filepath)
