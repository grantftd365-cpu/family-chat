"""数据库模型和初始化"""
import aiosqlite
import time
import uuid
from pathlib import Path
from typing import Optional

DB_PATH = "data/familychat.db"


async def init_db():
    """初始化数据库"""
    Path("data").mkdir(exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    
    await db.executescript("""
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            nickname TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            avatar TEXT DEFAULT '',
            status TEXT DEFAULT 'online',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        
        -- 群组表
        CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '',
            owner_id TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at REAL NOT NULL
        );
        
        -- 群成员表
        CREATE TABLE IF NOT EXISTS group_members (
            group_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at REAL NOT NULL,
            PRIMARY KEY (group_id, user_id)
        );
        
        -- 消息表
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            is_agent INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );
        
        -- Agent 表
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '',
            personality TEXT DEFAULT '{}',
            voice_config TEXT DEFAULT '{}',
            behavior TEXT DEFAULT '{}',
            backstory TEXT DEFAULT '',
            speaking_style TEXT DEFAULT '',
            traits TEXT DEFAULT '[]',
            interests TEXT DEFAULT '[]',
            catchphrases TEXT DEFAULT '[]',
            relationships TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            created_at REAL NOT NULL
        );
        
        -- Agent 记忆表
        CREATE TABLE IF NOT EXISTS agent_memories (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            memory_type TEXT DEFAULT 'short',
            metadata TEXT DEFAULT '{}',
            created_at REAL NOT NULL
        );
        
        -- 好友关系表
        CREATE TABLE IF NOT EXISTS friendships (
            user_id TEXT NOT NULL,
            friend_id TEXT NOT NULL,
            status TEXT DEFAULT 'accepted',
            created_at REAL NOT NULL,
            PRIMARY KEY (user_id, friend_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
        CREATE INDEX IF NOT EXISTS idx_memories_agent ON agent_memories(agent_id);
    """)
    
    await db.commit()
    await db.close()


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


def gen_id() -> str:
    """生成短ID"""
    return str(uuid.uuid4())[:12]


def now() -> float:
    """当前时间戳"""
    return time.time()
