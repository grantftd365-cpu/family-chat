"""消息投递服务 — 消息必达 + 已读回执 + 离线队列

核心保证：
1. 消息写入 DB 后才算"已发送"
2. 用户离线期间的消息进入离线队列
3. 用户上线/重连后自动推送离线消息
4. 每条消息对每个群成员有独立的投递状态
5. 已读状态精确到人
"""
import json
import time
from loguru import logger

from ..models.database import get_db, gen_id, now


class MessageDelivery:
    """消息投递管理器"""

    @staticmethod
    async def on_message_sent(message_id: str, group_id: str, sender_id: str):
        """消息发送后：为群内其他成员创建投递记录 + 离线队列"""
        db = await get_db()
        try:
            ts = now()
            # 获取群内所有成员（排除发送者）
            async with db.execute(
                "SELECT user_id FROM group_members WHERE group_id=? AND user_id!=?",
                (group_id, sender_id)
            ) as cursor:
                members = [row[0] async for row in cursor]

            for user_id in members:
                # 创建投递记录
                await db.execute(
                    """INSERT OR IGNORE INTO message_delivery
                       (message_id, user_id, status, delivered_at, read_at)
                       VALUES (?, ?, 'pending', 0, 0)""",
                    (message_id, user_id)
                )

            await db.commit()

            # 检查哪些用户在线，在线的立即标记 delivered
            from ..core.websocket import ws_manager
            for user_id in members:
                if ws_manager.is_online(user_id):
                    await MessageDelivery.mark_delivered(message_id, user_id)

        except Exception as e:
            logger.error(f"消息投递记录创建失败: {e}")
        finally:
            await db.close()

    @staticmethod
    async def mark_delivered(message_id: str, user_id: str):
        """标记消息已送达（客户端确认收到）"""
        db = await get_db()
        try:
            await db.execute(
                """UPDATE message_delivery SET status='delivered', delivered_at=?
                   WHERE message_id=? AND user_id=? AND status='pending'""",
                (now(), message_id, user_id)
            )
            await db.commit()
        finally:
            await db.close()

    @staticmethod
    async def mark_read(message_id: str, user_id: str):
        """标记消息已读"""
        db = await get_db()
        try:
            await db.execute(
                """UPDATE message_delivery SET status='read', read_at=?
                   WHERE message_id=? AND user_id=? AND status IN ('pending', 'delivered')""",
                (now(), message_id, user_id)
            )
            await db.commit()
        finally:
            await db.close()

    @staticmethod
    async def mark_batch_read(group_id: str, user_id: str, before_timestamp: float = 0):
        """批量标记已读 — 用户打开群聊时，将该群所有未读消息标记为已读"""
        db = await get_db()
        try:
            if before_timestamp > 0:
                await db.execute(
                    """UPDATE message_delivery SET status='read', read_at=?
                       WHERE user_id=? AND status IN ('pending', 'delivered')
                       AND message_id IN (
                           SELECT id FROM messages WHERE group_id=? AND created_at<=?
                       )""",
                    (now(), user_id, group_id, before_timestamp)
                )
            else:
                await db.execute(
                    """UPDATE message_delivery SET status='read', read_at=?
                       WHERE user_id=? AND status IN ('pending', 'delivered')
                       AND message_id IN (
                           SELECT id FROM messages WHERE group_id=?
                       )""",
                    (now(), user_id, group_id)
                )
            await db.commit()
        finally:
            await db.close()

    @staticmethod
    async def get_message_status(message_id: str) -> dict:
        """获取消息的投递状态汇总"""
        db = await get_db()
        try:
            result = {"total": 0, "delivered": 0, "read": 0, "pending": 0}
            async with db.execute(
                "SELECT status, COUNT(*) FROM message_delivery WHERE message_id=? GROUP BY status",
                (message_id,)
            ) as cursor:
                async for row in cursor:
                    result[row[0]] = row[1]
                    result["total"] += row[1]
            return result
        finally:
            await db.close()

    @staticmethod
    async def get_unread_count(user_id: str, group_id: str) -> int:
        """获取用户在某群的未读消息数"""
        db = await get_db()
        try:
            async with db.execute(
                """SELECT COUNT(*) FROM message_delivery
                   WHERE user_id=? AND status IN ('pending', 'delivered')
                   AND message_id IN (SELECT id FROM messages WHERE group_id=?)""",
                (user_id, group_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        finally:
            await db.close()

    @staticmethod
    async def get_all_unread_counts(user_id: str) -> dict:
        """获取用户在所有群的未读消息数"""
        db = await get_db()
        try:
            counts = {}
            async with db.execute(
                """SELECT m.group_id, COUNT(*) FROM message_delivery md
                   JOIN messages m ON md.message_id=m.id
                   WHERE md.user_id=? AND md.status IN ('pending', 'delivered')
                   GROUP BY m.group_id""",
                (user_id,)
            ) as cursor:
                async for row in cursor:
                    counts[row[0]] = row[1]
            return counts
        finally:
            await db.close()

    @staticmethod
    async def get_undelivered_messages(user_id: str, limit: int = 200) -> list:
        """获取用户未收到的消息（离线消息补发）"""
        db = await get_db()
        try:
            messages = []
            async with db.execute(
                """SELECT m.* FROM messages m
                   JOIN message_delivery md ON m.id=md.message_id
                   WHERE md.user_id=? AND md.status='pending'
                   ORDER BY m.created_at ASC LIMIT ?""",
                (user_id, limit)
            ) as cursor:
                async for row in cursor:
                    messages.append({
                        "id": row[0], "group_id": row[1], "sender_id": row[2],
                        "sender_name": row[3], "sender_avatar": row[4] or "",
                        "content": row[5], "msg_type": row[6],
                        "media_url": row[7] or "", "file_name": row[8] or "",
                        "file_size": row[9] or 0,
                        "is_agent": bool(row[10]), "reply_to": row[11] or "",
                        "reply_content": row[12] or "",
                        "forwarded_from": row[13] or "",
                        "recalled": bool(row[14]), "pinned": bool(row[15]),
                        "extra": row[16] or "{}",
                        "created_at": row[17],
                    })
            return messages
        finally:
            await db.close()

    @staticmethod
    async def get_read_users(message_id: str) -> list:
        """获取已读某消息的用户列表"""
        db = await get_db()
        try:
            users = []
            async with db.execute(
                """SELECT md.user_id, COALESCE(u.nickname, u.username) as name
                   FROM message_delivery md
                   LEFT JOIN users u ON md.user_id=u.id
                   WHERE md.message_id=? AND md.status='read'""",
                (message_id,)
            ) as cursor:
                async for row in cursor:
                    users.append({"user_id": row[0], "name": row[1]})
            return users
        finally:
            await db.close()


class ReactionManager:
    """飞书风格表情回应管理"""

    EMOJI_SET = ["👍", "❤️", "😂", "😮", "😢", "🎉", "🤔", "👏", "🔥", "💯"]

    @staticmethod
    async def add_reaction(message_id: str, user_id: str, user_name: str, emoji: str) -> dict:
        """添加表情回应"""
        db = await get_db()
        try:
            rid = gen_id()
            await db.execute(
                """INSERT OR IGNORE INTO message_reactions_v2
                   (id, message_id, user_id, user_name, emoji, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (rid, message_id, user_id, user_name, emoji, now())
            )
            await db.commit()
            # 返回该消息的所有回应
            return await ReactionManager.get_reactions(message_id)
        finally:
            await db.close()

    @staticmethod
    async def remove_reaction(message_id: str, user_id: str, emoji: str) -> dict:
        """移除表情回应"""
        db = await get_db()
        try:
            await db.execute(
                "DELETE FROM message_reactions_v2 WHERE message_id=? AND user_id=? AND emoji=?",
                (message_id, user_id, emoji)
            )
            await db.commit()
            return await ReactionManager.get_reactions(message_id)
        finally:
            await db.close()

    @staticmethod
    async def get_reactions(message_id: str) -> list:
        """获取消息的所有表情回应"""
        db = await get_db()
        try:
            reactions = []
            async with db.execute(
                """SELECT emoji, user_id, user_name FROM message_reactions_v2
                   WHERE message_id=? ORDER BY created_at""",
                (message_id,)
            ) as cursor:
                async for row in cursor:
                    reactions.append({
                        "emoji": row[0],
                        "user_id": row[1],
                        "user_name": row[2],
                    })
            return reactions
        finally:
            await db.close()

    @staticmethod
    async def get_batch_reactions(message_ids: list) -> dict:
        """批量获取多条消息的表情回应"""
        if not message_ids:
            return {}
        db = await get_db()
        try:
            reactions = {}
            placeholders = ",".join("?" * len(message_ids))
            async with db.execute(
                f"""SELECT message_id, emoji, user_id, user_name
                    FROM message_reactions_v2
                    WHERE message_id IN ({placeholders})
                    ORDER BY created_at""",
                message_ids
            ) as cursor:
                async for row in cursor:
                    if row[0] not in reactions:
                        reactions[row[0]] = []
                    reactions[row[0]].append({
                        "emoji": row[1],
                        "user_id": row[2],
                        "user_name": row[3],
                    })
            return reactions
        finally:
            await db.close()
