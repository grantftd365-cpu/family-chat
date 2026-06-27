"""系统功能路由 - 备份/恢复/定时任务"""
import asyncio
import json
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger

from ..core.auth import get_current_user
from ..models.database import get_db, gen_id, now

router = APIRouter(prefix="/api/system")


# ==================== 数据备份 ====================

@router.post("/backup")
async def create_backup(user=Depends(get_current_user)):
    """创建数据备份"""
    backup_dir = Path("data/backups")
    backup_dir.mkdir(exist_ok=True)

    ts = int(time.time())
    backup_name = f"familychat_backup_{ts}.db"
    backup_path = backup_dir / backup_name

    # 复制数据库
    shutil.copy2("data/familychat.db", str(backup_path))

    # 备份上传文件
    uploads_backup = backup_dir / f"uploads_{ts}"
    if Path("data/uploads").exists():
        shutil.copytree("data/uploads", str(uploads_backup), dirs_exist_ok=True)

    return {
        "status": "ok",
        "filename": backup_name,
        "size": backup_path.stat().st_size,
        "created_at": ts,
    }


@router.get("/backups")
async def list_backups(user=Depends(get_current_user)):
    """列出备份"""
    backup_dir = Path("data/backups")
    if not backup_dir.exists():
        return []

    backups = []
    for f in sorted(backup_dir.glob("familychat_backup_*.db"), reverse=True):
        backups.append({
            "filename": f.name,
            "size": f.stat().st_size,
            "created_at": f.stat().st_mtime,
        })
    return backups


@router.get("/backups/{filename}/download")
async def download_backup(filename: str, user=Depends(get_current_user)):
    """下载备份文件"""
    filepath = Path("data/backups") / filename
    if not filepath.exists():
        raise HTTPException(404, "备份不存在")
    return FileResponse(str(filepath), filename=filename)


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...), user=Depends(get_current_user)):
    """从备份恢复 - 仅限管理员"""
    # 权限校验：只有 admin 角色可以恢复备份
    db_check = await get_db()
    try:
        async with db_check.execute("SELECT role FROM users WHERE id=?", (user["user_id"],)) as c:
            row = await c.fetchone()
            if not row or row[0] != "admin":
                raise HTTPException(403, "仅管理员可以恢复备份")
    finally:
        await db_check.close()

    content = await file.read()
    if len(content) < 100:
        raise HTTPException(400, "无效的备份文件")

    # 先备份当前数据
    backup_dir = Path("data/backups")
    backup_dir.mkdir(exist_ok=True)
    ts = int(time.time())
    shutil.copy2("data/familychat.db", str(backup_dir / f"pre_restore_{ts}.db"))

    # 写入恢复文件
    with open("data/familychat.db", "wb") as f:
        f.write(content)

    return {"status": "ok", "message": "恢复成功，请重启服务"}


# ==================== 定时任务 - Agent 主动发言 ====================

class ProactiveConfig(BaseModel):
    agent_id: str
    enabled: bool = True
    frequency_hours: int = 6
    topics: list = []


@router.post("/agent/proactive")
async def set_proactive_config(req: ProactiveConfig, user=Depends(get_current_user)):
    """设置 Agent 主动发言配置"""
    db = await get_db()
    try:
        config = json.dumps({
            "enabled": req.enabled,
            "frequency_hours": req.frequency_hours,
            "topics": req.topics,
            "last_proactive": 0,
        }, ensure_ascii=False)
        await db.execute(
            "UPDATE agents SET proactive_config=? WHERE id=?",
            (config, req.agent_id)
        )
        await db.commit()
        return {"status": "ok"}
    finally:
        await db.close()


@router.get("/agent/proactive")
async def get_proactive_configs(user=Depends(get_current_user)):
    """获取所有 Agent 的主动发言配置"""
    db = await get_db()
    try:
        configs = []
        async with db.execute(
            "SELECT id, name, proactive_config FROM agents WHERE enabled=1"
        ) as cursor:
            async for row in cursor:
                cfg = json.loads(row[2]) if row[2] else {}
                configs.append({
                    "agent_id": row[0], "agent_name": row[1],
                    "enabled": cfg.get("enabled", False),
                    "frequency_hours": cfg.get("frequency_hours", 6),
                    "topics": cfg.get("topics", []),
                })
        return configs
    finally:
        await db.close()


# ==================== 系统统计 ====================

@router.get("/stats")
async def get_stats(user=Depends(get_current_user)):
    """获取系统统计"""
    db = await get_db()
    try:
        stats = {}

        async with db.execute("SELECT COUNT(*) FROM users") as c:
            r = await c.fetchone()
            stats["total_users"] = r[0]

        async with db.execute("SELECT COUNT(*) FROM agents WHERE enabled=1") as c:
            r = await c.fetchone()
            stats["total_agents"] = r[0]

        async with db.execute("SELECT COUNT(*) FROM messages") as c:
            r = await c.fetchone()
            stats["total_messages"] = r[0]

        async with db.execute("SELECT COUNT(*) FROM groups") as c:
            r = await c.fetchone()
            stats["total_groups"] = r[0]

        async with db.execute("SELECT COUNT(*) FROM moments") as c:
            r = await c.fetchone()
            stats["total_moments"] = r[0]

        async with db.execute("SELECT COUNT(*) FROM agent_memories") as c:
            r = await c.fetchone()
            stats["total_memories"] = r[0]

        # 数据库大小
        db_path = Path("data/familychat.db")
        stats["db_size_mb"] = round(db_path.stat().st_size / 1048576, 2) if db_path.exists() else 0

        return stats
    finally:
        await db.close()
