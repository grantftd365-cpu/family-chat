"""认证路由 - 登录/注册/个人信息"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
from loguru import logger

from ..core.auth import hash_password, verify_password, create_token, get_current_user
from ..models.database import get_db, gen_id, now
from ..services.family import detach_legacy_global_family, ensure_user_family_group

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

        await ensure_user_family_group(db, user_id, agent_id)
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
            "SELECT id,username,nickname,avatar,agent_id,password_hash,signature,avatar_url FROM users WHERE email=?",
            (req.email,)
        ) as c:
            row = await c.fetchone()
            if not row or not verify_password(req.password, row[5]):
                raise HTTPException(401, "邮箱或密码错误")

        # 更新在线状态
        await ensure_user_family_group(db, row[0], row[4] or "")
        await detach_legacy_global_family(db, row[0], row[4] or "")
        await db.execute("UPDATE users SET online_status='online', last_seen=? WHERE id=?", (now(), row[0]))
        await db.commit()

        token = create_token(row[0], req.email)
        return {
            "token": token,
            "user": {"id": row[0], "email": req.email, "username": row[1],
                     "nickname": row[2], "avatar": row[3] or "😀",
                     "agent_id": row[4] or "", "signature": row[6] or "",
                     "avatar_url": row[7] or ""},
        }
    finally:
        await db.close()


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id,username,nickname,avatar,agent_id,signature,gender,region,email,avatar_url FROM users WHERE id=?",
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
                "avatar_url": row[9] or "",
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


# ==================== 微信登录 ====================

import os
import httpx

WX_APPID = os.getenv("WX_APPID", "")
WX_SECRET = os.getenv("WX_SECRET", "")
# 网页授权 OAuth scope: snsapi_userinfo 可获取用户信息
WX_OAUTH_SCOPE = os.getenv("WX_OAUTH_SCOPE", "snsapi_userinfo")


class WxLoginReq(BaseModel):
    code: str
    nickname: str = ""
    avatar: str = ""
    gender: int = 0
    province: str = ""
    city: str = ""
    country: str = ""
    language: str = "zh_CN"
    encrypted_data: str = ""
    iv: str = ""
    raw_data: str = ""
    signature: str = ""


def _gender_text(value: int) -> str:
    return "男" if value == 1 else "女" if value == 2 else ""


def _region_text(profile: dict) -> str:
    return f"{profile.get('province', '')} {profile.get('city', '')}".strip()


def _wx_profile_from_req(req: WxLoginReq) -> dict:
    return {
        "nickname": req.nickname.strip(),
        "avatar": req.avatar.strip(),
        "gender": req.gender,
        "province": req.province.strip(),
        "city": req.city.strip(),
        "country": req.country.strip(),
        "language": req.language or "zh_CN",
    }


async def _refine_wechat_profile(agent_id: str, profile: dict):
    meaningful = [profile.get("nickname"), profile.get("avatar"), profile.get("province"), profile.get("city")]
    if not agent_id or not any(meaningful):
        return
    try:
        from ..main import refinement_service
        if refinement_service:
            await refinement_service.refine_from_wechat_profile(agent_id, profile)
    except Exception as e:
        logger.debug(f"微信资料炼化跳过: {e}")


@router.post("/wx-login")
async def wx_login(req: WxLoginReq):
    """微信小程序登录: code -> openid -> JWT token"""
    if not req.code or not req.code.strip():
        raise HTTPException(400, "code 不能为空")
    if not WX_APPID or not WX_SECRET:
        raise HTTPException(500, "微信登录未配置（缺少 WX_APPID / WX_SECRET）")

    # 1. 用 code 换 openid
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": WX_APPID,
                    "secret": WX_SECRET,
                    "js_code": req.code,
                    "grant_type": "authorization_code",
                },
            )
            data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "微信服务器超时，请重试")
    except httpx.RequestError as e:
        logger.error(f"微信 API 请求失败: {e}")
        raise HTTPException(502, "无法连接微信服务器")

    openid = data.get("openid")
    if not openid:
        logger.error(f"微信登录失败: {data}")
        errcode = data.get("errcode", 0)
        # 常见错误码: 40029=code无效, 40163=code已使用, 45011=频率限制
        errmsg = data.get("errmsg", '未知错误')
        raise HTTPException(400, f"微信登录失败({errcode}): {errmsg}")

    unionid = data.get("unionid", "")

    wx_profile = _wx_profile_from_req(req)

    # 2. 查找或创建用户
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id, username, nickname, avatar, agent_id, avatar_url FROM users WHERE wx_openid=?",
            (openid,)
        ) as c:
            row = await c.fetchone()

        if row:
            # 已有用户，直接登录
            user_id = row[0]
            nickname = wx_profile.get("nickname") or row[2]
            avatar_url = wx_profile.get("avatar") or row[5] or ""
            gender = _gender_text(wx_profile.get("gender", 0))
            region = _region_text(wx_profile)
            update_fields = ["online_status='online'", "last_seen=?"]
            update_params = [now()]
            if wx_profile.get("nickname"):
                update_fields.append("nickname=?")
                update_params.append(nickname)
            if avatar_url:
                update_fields.append("avatar_url=?")
                update_params.append(avatar_url)
            if gender:
                update_fields.append("gender=?")
                update_params.append(gender)
            if region:
                update_fields.append("region=?")
                update_params.append(region)
            update_fields.append("updated_at=?")
            update_params.append(now())
            update_params.append(user_id)
            await db.execute(
                f"UPDATE users SET {','.join(update_fields)} WHERE id=?",
                update_params
            )
            await db.commit()
            await _refine_wechat_profile(row[4], wx_profile)
            token = create_token(user_id, row[1])
            return {
                "token": token,
                "user": {
                    "id": user_id, "username": row[1], "nickname": nickname,
                    "avatar": row[3] or "😀", "avatar_url": avatar_url,
                    "agent_id": row[4] or "", "is_new": False,
                    "wx_profile": wx_profile,
                },
            }

        # 新用户，自动注册
        user_id = gen_id()
        ts = now()
        nickname = wx_profile.get("nickname") or f"微信用户{user_id[:6]}"
        avatar = "💬"
        avatar_url = wx_profile.get("avatar") or ""
        username = f"wx_{openid[:8]}"
        gender = _gender_text(wx_profile.get("gender", 0))
        region = _region_text(wx_profile)

        await db.execute(
            """INSERT INTO users (id,email,username,nickname,password_hash,avatar,avatar_url,wx_openid,wx_unionid,gender,region,role,agent_id,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, f"{openid}@wx.local", username, nickname,
             "", avatar, avatar_url, openid, unionid, gender, region, "member", "", ts, ts)
        )

        # 创建数字人分身
        from ..main import agent_manager
        agent_id = f"agent_{user_id}"
        agent_config = {
            "id": agent_id, "user_id": user_id, "name": nickname,
            "avatar": avatar, "backstory": f"{nickname}的数字分身",
            "speaking_style": "待炼化",
        }
        await agent_manager.create_agent(agent_config, _db=db)
        await db.execute("UPDATE users SET agent_id=? WHERE id=?", (agent_id, user_id))

        await ensure_user_family_group(db, user_id, agent_id)
        await db.commit()
        await _refine_wechat_profile(agent_id, wx_profile)

        token = create_token(user_id, username)
        return {
            "token": token,
            "user": {
                "id": user_id, "username": username, "nickname": nickname,
                "avatar": avatar, "avatar_url": avatar_url,
                "agent_id": agent_id, "is_new": True,
                "wx_profile": wx_profile,
            },
        }
    finally:
        await db.close()


# ==================== 微信网页 OAuth 登录 ====================

class WxOAuthLoginReq(BaseModel):
    """微信网页 OAuth 登录（公众号/开放平台）"""
    code: str


class WxOAuthCallbackResp(BaseModel):
    """OAuth 回调数据"""
    openid: str
    nickname: str = ""
    avatar: str = ""
    gender: int = 0
    province: str = ""
    city: str = ""
    country: str = ""
    unionid: str = ""
    language: str = "zh_CN"


@router.get("/wx/oauth/url")
async def wx_oauth_url(redirect_uri: str):
    """生成微信 OAuth 授权 URL（用户点击后跳转微信授权）"""
    if not WX_APPID:
        raise HTTPException(500, "微信登录未配置（缺少 WX_APPID）")
    import urllib.parse
    encoded_uri = urllib.parse.quote(redirect_uri, safe="")
    url = (
        f"https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={WX_APPID}"
        f"&redirect_uri={encoded_uri}"
        f"&response_type=code"
        f"&scope={WX_OAUTH_SCOPE}"
        f"&state=familychat"
        f"#wechat_redirect"
    )
    return {"url": url}


@router.post("/wx/oauth/login")
async def wx_oauth_login(req: WxOAuthLoginReq):
    """微信网页 OAuth 登录完整流程:
    1. 用 code 换 access_token + openid
    2. 用 access_token 获取用户信息（昵称、头像、性别、地区等）
    3. 查找或创建用户
    4. 自动炼化数字人基础信息
    """
    if not req.code or not req.code.strip():
        raise HTTPException(400, "code 不能为空")
    if not WX_APPID or not WX_SECRET:
        raise HTTPException(500, "微信登录未配置（缺少 WX_APPID / WX_SECRET）")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: code -> access_token + openid
            token_resp = await client.get(
                "https://api.weixin.qq.com/sns/oauth2/access_token",
                params={
                    "appid": WX_APPID,
                    "secret": WX_SECRET,
                    "code": req.code,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_resp.json()

    except httpx.TimeoutException:
        raise HTTPException(504, "微信服务器超时")
    except httpx.RequestError as e:
        logger.error(f"微信 OAuth 请求失败: {e}")
        raise HTTPException(502, "无法连接微信服务器")

    access_token = token_data.get("access_token")
    openid = token_data.get("openid")
    if not access_token or not openid:
        errcode = token_data.get("errcode", 0)
        errmsg = token_data.get("errmsg", "未知错误")
        logger.error(f"微信 OAuth 失败: {token_data}")
        raise HTTPException(400, f"微信授权失败({errcode}): {errmsg}")

    unionid = token_data.get("unionid", "")

    # Step 2: 获取用户信息
    wx_profile = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            user_resp = await client.get(
                "https://api.weixin.qq.com/sns/userinfo",
                params={
                    "access_token": access_token,
                    "openid": openid,
                    "lang": "zh_CN",
                },
            )
            user_data = user_resp.json()
            if "errcode" not in user_data or user_data.get("errcode") == 0:
                wx_profile = {
                    "nickname": user_data.get("nickname", ""),
                    "avatar": user_data.get("headimgurl", ""),
                    "gender": user_data.get("sex", 0),
                    "province": user_data.get("province", ""),
                    "city": user_data.get("city", ""),
                    "country": user_data.get("country", ""),
                    "language": user_data.get("language", "zh_CN"),
                }
            else:
                logger.warning(f"获取微信用户信息失败（可能是 scope 不足）: {user_data}")
    except Exception as e:
        logger.warning(f"获取微信用户信息异常: {e}")

    # Step 3: 查找或创建用户
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id, username, nickname, avatar, agent_id, avatar_url FROM users WHERE wx_openid=?",
            (openid,)
        ) as c:
            row = await c.fetchone()

        if row:
            user_id = row[0]
            # 更新微信资料（如果有新数据）
            if wx_profile:
                update_fields = []
                update_params = []
                if wx_profile.get("nickname") and not row[2]:
                    update_fields.append("nickname=?")
                    update_params.append(wx_profile["nickname"])
                if wx_profile.get("avatar"):
                    update_fields.append("avatar_url=?")
                    update_params.append(wx_profile["avatar"])
                if wx_profile.get("gender"):
                    update_fields.append("gender=?")
                    update_params.append("男" if wx_profile["gender"] == 1 else "女" if wx_profile["gender"] == 2 else "")
                if wx_profile.get("province") or wx_profile.get("city"):
                    region = f"{wx_profile.get('province', '')} {wx_profile.get('city', '')}".strip()
                    if region:
                        update_fields.append("region=?")
                        update_params.append(region)
                if update_fields:
                    update_fields.append("updated_at=?")
                    update_params.append(now())
                    update_params.append(user_id)
                    await db.execute(
                        f"UPDATE users SET {','.join(update_fields)} WHERE id=?",
                        update_params
                    )

            await db.execute(
                "UPDATE users SET online_status='online', last_seen=? WHERE id=?",
                (now(), user_id)
            )
            await ensure_user_family_group(db, user_id, row[4] or "")
            await detach_legacy_global_family(db, user_id, row[4] or "")
            await db.commit()

            # 异步炼化微信资料到数字人
            if wx_profile:
                try:
                    from ..main import refinement_service
                    agent_row = await (await db.execute("SELECT agent_id FROM users WHERE id=?", (user_id,))).fetchone()
                    if agent_row and agent_row[0] and refinement_service:
                        await refinement_service.refine_from_wechat_profile(agent_row[0], wx_profile)
                except Exception as e:
                    logger.debug(f"微信资料炼化跳过: {e}")

            token = create_token(user_id, row[1])
            return {
                "token": token,
                "user": {
                    "id": user_id, "username": row[1], "nickname": row[2],
                    "avatar": row[3] or "😀", "avatar_url": wx_profile.get("avatar") or row[5] or "",
                    "agent_id": row[4] or "",
                    "is_new": False, "wx_profile": wx_profile,
                },
            }

        # 新用户
        user_id = gen_id()
        ts = now()
        nickname = wx_profile.get("nickname", "") or f"微信用户{user_id[:6]}"
        avatar = "💬"
        avatar_url = wx_profile.get("avatar", "")
        username = f"wx_{openid[:8]}"
        gender = "男" if wx_profile.get("gender") == 1 else "女" if wx_profile.get("gender") == 2 else ""
        region = f"{wx_profile.get('province', '')} {wx_profile.get('city', '')}".strip()

        await db.execute(
            """INSERT INTO users (id,email,username,nickname,password_hash,avatar,avatar_url,wx_openid,wx_unionid,gender,region,role,agent_id,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, f"{openid}@wx.local", username, nickname,
             "", avatar, avatar_url, openid, unionid, gender, region, "member", "", ts, ts)
        )

        # 创建数字人分身
        from ..main import agent_manager, refinement_service
        agent_id = f"agent_{user_id}"
        agent_config = {
            "id": agent_id, "user_id": user_id, "name": nickname,
            "avatar": avatar, "backstory": f"{nickname}的数字分身",
            "speaking_style": "待炼化",
        }
        await agent_manager.create_agent(agent_config, _db=db)
        await db.execute("UPDATE users SET agent_id=? WHERE id=?", (agent_id, user_id))

        await ensure_user_family_group(db, user_id, agent_id)
        await db.commit()

        # 异步炼化微信资料到数字人
        if wx_profile and refinement_service:
            try:
                await refinement_service.refine_from_wechat_profile(agent_id, wx_profile)
            except Exception as e:
                logger.debug(f"微信资料炼化跳过: {e}")

        token = create_token(user_id, username)
        return {
            "token": token,
            "user": {
                "id": user_id, "username": username, "nickname": nickname,
                "avatar": avatar, "avatar_url": avatar_url,
                "agent_id": agent_id, "is_new": True,
                "wx_profile": wx_profile,
            },
        }
    finally:
        await db.close()
