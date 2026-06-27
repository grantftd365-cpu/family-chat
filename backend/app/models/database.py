"""数据库模型和初始化 - v2.0 全功能版

优化：连接池、WAL 模式、索引优化
"""
import aiosqlite
import asyncio
import time
import uuid
from pathlib import Path
from loguru import logger

DB_PATH = "data/familychat.db"

# 连接池
_pool: aiosqlite.Connection | None = None
_pool_lock = asyncio.Lock()


async def init_db():
    """初始化数据库 - 完整 schema"""
    Path("data").mkdir(exist_ok=True)
    Path("data/uploads").mkdir(exist_ok=True)
    Path("data/voices").mkdir(exist_ok=True)
    Path("data/avatars").mkdir(exist_ok=True)
    Path("data/backups").mkdir(exist_ok=True)

    db = await aiosqlite.connect(DB_PATH)
    await db.executescript("""
        -- ==================== 用户表 ====================
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            nickname TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            avatar TEXT DEFAULT '😀',
            avatar_url TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            wx_openid TEXT DEFAULT '',
            wx_unionid TEXT DEFAULT '',
            signature TEXT DEFAULT '',
            gender TEXT DEFAULT '',
            region TEXT DEFAULT '',
            role TEXT DEFAULT 'member',
            agent_id TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            online_status TEXT DEFAULT 'offline',
            last_seen REAL DEFAULT 0,
            settings TEXT DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_wx_openid ON users(wx_openid);

        -- ==================== 群组表 ====================
        CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '👥',
            owner_id TEXT NOT NULL,
            description TEXT DEFAULT '',
            group_type TEXT DEFAULT 'family',
            announcement TEXT DEFAULT '',
            family_code TEXT DEFAULT '',
            mute_all INTEGER DEFAULT 0,
            max_members INTEGER DEFAULT 500,
            created_at REAL NOT NULL,
            updated_at REAL DEFAULT 0
        );

        -- ==================== 群成员表 ====================
        CREATE TABLE IF NOT EXISTS group_members (
            group_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            nickname TEXT DEFAULT '',
            muted_until REAL DEFAULT 0,
            joined_at REAL NOT NULL,
            PRIMARY KEY (group_id, user_id)
        );

        -- ==================== 消息表 ====================
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            sender_avatar TEXT DEFAULT '',
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            media_url TEXT DEFAULT '',
            file_name TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            is_agent INTEGER DEFAULT 0,
            reply_to TEXT DEFAULT '',
            reply_content TEXT DEFAULT '',
            forwarded_from TEXT DEFAULT '',
            recalled INTEGER DEFAULT 0,
            pinned INTEGER DEFAULT 0,
            extra TEXT DEFAULT '{}',
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);

        -- ==================== 消息表情回复 ====================
        CREATE TABLE IF NOT EXISTS message_reactions (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            emoji TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(message_id, user_id, emoji)
        );

        -- ==================== 收藏消息 ====================
        CREATE TABLE IF NOT EXISTS favorites (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            message_id TEXT DEFAULT '',
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            media_url TEXT DEFAULT '',
            source_name TEXT DEFAULT '',
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);

        -- ==================== Agent 表 ====================
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            user_id TEXT DEFAULT '',
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '🤖',
            soul TEXT DEFAULT '{}',
            identity TEXT DEFAULT '{}',
            backstory TEXT DEFAULT '',
            speaking_style TEXT DEFAULT '',
            traits TEXT DEFAULT '[]',
            interests TEXT DEFAULT '[]',
            catchphrases TEXT DEFAULT '[]',
            humor_style TEXT DEFAULT '',
            emotional_pattern TEXT DEFAULT '',
            relationships TEXT DEFAULT '{}',
            voice_config TEXT DEFAULT '{}',
            behavior TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            refinement_count INTEGER DEFAULT 0,
            last_refined_at REAL DEFAULT 0,
            proactive_config TEXT DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        -- ==================== Agent 记忆表 ====================
        CREATE TABLE IF NOT EXISTS agent_memories (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT DEFAULT '',
            memory_type TEXT DEFAULT 'short',
            category TEXT DEFAULT 'general',
            importance REAL DEFAULT 0.5,
            emotional_valence REAL DEFAULT 0,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL DEFAULT 0,
            source TEXT DEFAULT '',
            related_people TEXT DEFAULT '[]',
            tags TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            occurred_at REAL DEFAULT 0,
            created_at REAL NOT NULL,
            consolidated INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_memories_agent ON agent_memories(agent_id);
        CREATE INDEX IF NOT EXISTS idx_memories_type ON agent_memories(agent_id, memory_type);

        -- ==================== 炼化记录表 ====================
        CREATE TABLE IF NOT EXISTS refinement_logs (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_url TEXT DEFAULT '',
            extracted_data TEXT DEFAULT '{}',
            status TEXT DEFAULT 'success',
            created_at REAL NOT NULL
        );

        -- ==================== 好友关系表 ====================
        CREATE TABLE IF NOT EXISTS friendships (
            user_id TEXT NOT NULL,
            friend_id TEXT NOT NULL,
            status TEXT DEFAULT 'accepted',
            remark TEXT DEFAULT '',
            created_at REAL NOT NULL,
            PRIMARY KEY (user_id, friend_id)
        );

        -- ==================== 好友请求表 ====================
        CREATE TABLE IF NOT EXISTS friend_requests (
            id TEXT PRIMARY KEY,
            from_user_id TEXT NOT NULL,
            to_user_id TEXT NOT NULL,
            message TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_fr_req_to ON friend_requests(to_user_id, status);

        -- ==================== 朋友圈表 ====================
        CREATE TABLE IF NOT EXISTS moments (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            content TEXT DEFAULT '',
            images TEXT DEFAULT '[]',
            location TEXT DEFAULT '',
            visibility TEXT DEFAULT 'all',
            like_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_moments_user ON moments(user_id, created_at);

        -- ==================== 朋友圈点赞/评论 ====================
        CREATE TABLE IF NOT EXISTS moment_interactions (
            id TEXT PRIMARY KEY,
            moment_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT DEFAULT '',
            interaction_type TEXT NOT NULL,
            content TEXT DEFAULT '',
            created_at REAL NOT NULL
        );

        -- ==================== 红包表 ====================
        CREATE TABLE IF NOT EXISTS red_envelopes (
            id TEXT PRIMARY KEY,
            sender_id TEXT NOT NULL,
            group_id TEXT DEFAULT '',
            receiver_id TEXT DEFAULT '',
            amount REAL NOT NULL,
            count INTEGER DEFAULT 1,
            greeting TEXT DEFAULT '恭喜发财',
            status TEXT DEFAULT 'pending',
            remaining REAL DEFAULT 0,
            remaining_count INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );

        -- ==================== 红包领取记录 ====================
        CREATE TABLE IF NOT EXISTS red_envelope_claims (
            id TEXT PRIMARY KEY,
            envelope_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            claimed_at REAL NOT NULL
        );

        -- ==================== 通知表 ====================
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT DEFAULT '',
            content TEXT DEFAULT '',
            ref_id TEXT DEFAULT '',
            is_read INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read);

        -- ==================== 拍一拍记录 ====================
        CREATE TABLE IF NOT EXISTS pats (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            from_user_id TEXT NOT NULL,
            from_user_name TEXT DEFAULT '',
            to_user_id TEXT NOT NULL,
            to_user_name TEXT DEFAULT '',
            action TEXT DEFAULT '拍了拍',
            created_at REAL NOT NULL
        );

        -- ==================== 消息投递状态表 ====================
        -- 每条消息对每个用户的投递状态: pending/delivered/read
        CREATE TABLE IF NOT EXISTS message_delivery (
            message_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',  -- pending / delivered / read
            delivered_at REAL DEFAULT 0,
            read_at REAL DEFAULT 0,
            PRIMARY KEY (message_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_delivery_user ON message_delivery(user_id, status);

        -- ==================== 离线消息队列表 ====================
        -- 用户离线期间的消息，上线后推送
        CREATE TABLE IF NOT EXISTS offline_queue (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            message_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_offline_user ON offline_queue(user_id, created_at);

        -- ==================== 消息表情回应表 ====================
        -- 飞书风格：每条消息下方的小表情回应
        CREATE TABLE IF NOT EXISTS message_reactions_v2 (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT DEFAULT '',
            emoji TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(message_id, user_id, emoji)
        );
        CREATE INDEX IF NOT EXISTS idx_reaction_msg ON message_reactions_v2(message_id);
    """)

    await db.commit()
    await db.close()


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接（每次新建，避免并发问题）"""
    db = await aiosqlite.connect(DB_PATH, timeout=30)
    db.row_factory = aiosqlite.Row
    return db


class ManagedDB:
    """Context manager for database connections"""
    def __init__(self):
        self.db = None

    async def __aenter__(self):
        self.db = await get_db()
        return self.db

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            await self.db.close()
        return False


async def close_db():
    """关闭数据库连接"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def gen_id() -> str:
    """生成唯一 ID（完整 UUID4，无截断，避免碰撞）"""
    return str(uuid.uuid4())


def now() -> float:
    return time.time()
