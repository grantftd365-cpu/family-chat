"""家庭群隔离与成员同步工具。"""

from ..models.database import now


def user_family_group_id(user_id: str) -> str:
    """每个真实用户都有独立的默认家庭群，避免不同家庭串群。"""
    return f"family_{user_id}"


async def ensure_user_family_group(db, user_id: str, agent_id: str = "") -> str:
    """创建/修复当前用户自己的“我们的家庭”，并加入自己的数字分身。"""
    group_id = user_family_group_id(user_id)
    ts = now()
    await db.execute(
        """INSERT OR IGNORE INTO groups
           (id,name,avatar,owner_id,description,group_type,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (group_id, "我们的家庭", "👥", user_id, "我的家庭聊天群", "family", ts, ts),
    )
    await db.execute(
        "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
        (group_id, user_id, "owner", ts),
    )
    if agent_id:
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
            (group_id, agent_id, "agent", ts),
        )
    return group_id


async def detach_legacy_global_family(db, user_id: str, agent_id: str = ""):
    """旧版本的 family_default 是全局群；多家庭上线后用户不再自动留在该群。"""
    async with db.execute("SELECT owner_id FROM groups WHERE id='family_default'") as cursor:
        row = await cursor.fetchone()
    if not row or row[0] != "system":
        return
    await db.execute(
        "DELETE FROM group_members WHERE group_id='family_default' AND user_id=?",
        (user_id,),
    )
    if agent_id:
        await db.execute(
            "DELETE FROM group_members WHERE group_id='family_default' AND user_id=?",
            (agent_id,),
        )


async def get_user_agent_id(db, user_id: str) -> str:
    async with db.execute("SELECT agent_id FROM users WHERE id=?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    return row[0] if row and row[0] else ""


async def get_group_member_role(db, group_id: str, user_id: str) -> str:
    async with db.execute(
        "SELECT role FROM group_members WHERE group_id=? AND user_id=?",
        (group_id, user_id),
    ) as cursor:
        row = await cursor.fetchone()
    return row[0] if row else ""


async def require_group_member(db, group_id: str, user_id: str) -> str:
    role = await get_group_member_role(db, group_id, user_id)
    if not role:
        from fastapi import HTTPException

        raise HTTPException(403, "你不是该群成员")
    return role


async def require_group_admin(db, group_id: str, user_id: str) -> str:
    role = await require_group_member(db, group_id, user_id)
    if role not in ("owner", "admin"):
        from fastapi import HTTPException

        raise HTTPException(403, "只有群主或管理员可以操作")
    return role


async def user_can_access_agent(db, user_id: str, agent_id: str) -> bool:
    """用户能管理自己的数字人，或能在同群中看到该数字人。"""
    async with db.execute("SELECT user_id FROM agents WHERE id=?", (agent_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return False
    owner_id = row[0] or ""
    if owner_id == user_id:
        return True
    async with db.execute(
        """SELECT 1
           FROM group_members user_member
           JOIN group_members agent_member ON user_member.group_id=agent_member.group_id
           WHERE user_member.user_id=? AND agent_member.user_id=?
           LIMIT 1""",
        (user_id, agent_id),
    ) as cursor:
        return await cursor.fetchone() is not None


async def user_owns_agent(db, user_id: str, agent_id: str) -> bool:
    async with db.execute(
        "SELECT 1 FROM agents WHERE id=? AND user_id=?",
        (agent_id, user_id),
    ) as cursor:
        return await cursor.fetchone() is not None
