"""数据库模型和初始化 - 完整版"""
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
        -- ==================== 用户表 ====================
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,          -- 邮箱（登录凭证）
            username TEXT UNIQUE NOT NULL,        -- 用户名
            nickname TEXT NOT NULL,               -- 显示昵称
            password_hash TEXT NOT NULL,
            avatar TEXT DEFAULT '😀',
            phone TEXT DEFAULT '',
            role TEXT DEFAULT 'member',           -- member / admin
            agent_id TEXT DEFAULT '',             -- 关联的 Agent ID
            status TEXT DEFAULT 'active',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        
        -- ==================== 群组表 ====================
        CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '👥',
            owner_id TEXT NOT NULL,
            description TEXT DEFAULT '',
            group_type TEXT DEFAULT 'family',     -- family / custom
            created_at REAL NOT NULL
        );
        
        -- ==================== 群成员表 ====================
        CREATE TABLE IF NOT EXISTS group_members (
            group_id TEXT NOT NULL,
            user_id TEXT NOT NULL,                -- 用户ID 或 AgentID
            role TEXT DEFAULT 'member',           -- owner / member / agent
            nickname TEXT DEFAULT '',              -- 群内昵称
            joined_at REAL NOT NULL,
            PRIMARY KEY (group_id, user_id)
        );
        
        -- ==================== 消息表 ====================
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',         -- text / voice / image / system / emoji
            media_url TEXT DEFAULT '',             -- 媒体文件URL
            is_agent INTEGER DEFAULT 0,
            reply_to TEXT DEFAULT '',              -- 回复的消息ID
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
        
        -- ==================== Agent 表 (数字人) ====================
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            user_id TEXT DEFAULT '',              -- 关联的用户ID（真人绑定）
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '🤖',
            
            -- 灵魂系统 (Soul)
            soul TEXT DEFAULT '{}',               -- JSON: 核心价值观、人生信条、情感模式
            identity TEXT DEFAULT '{}',           -- JSON: 身份认同、角色定位、自我认知
            
            -- 性格系统
            backstory TEXT DEFAULT '',             -- 背景故事
            speaking_style TEXT DEFAULT '',        -- 说话风格
            traits TEXT DEFAULT '[]',              -- 性格特征列表
            interests TEXT DEFAULT '[]',           -- 兴趣爱好
            catchphrases TEXT DEFAULT '[]',        -- 口头禅
            humor_style TEXT DEFAULT '',           -- 幽默风格
            emotional_pattern TEXT DEFAULT '',     -- 情感模式
            
            -- 关系网络
            relationships TEXT DEFAULT '{}',       -- 与其他人的关系
            
            -- 语音配置
            voice_config TEXT DEFAULT '{}',        -- JSON: 语音模型、音色等
            
            -- 行为配置
            behavior TEXT DEFAULT '{}',            -- JSON: 活跃时间、回复概率等
            
            -- 状态
            enabled INTEGER DEFAULT 1,
            refinement_count INTEGER DEFAULT 0,    -- 炼化次数
            last_refined_at REAL DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_agents_user ON agents(user_id);
        
        -- ==================== Agent 记忆表 ====================
        CREATE TABLE IF NOT EXISTS agent_memories (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            
            -- 记忆内容
            content TEXT NOT NULL,                 -- 记忆内容
            summary TEXT DEFAULT '',               -- 摘要（用于快速检索）
            
            -- 记忆分类
            memory_type TEXT DEFAULT 'short',      -- short / long / core / episodic
            category TEXT DEFAULT 'general',       -- general / event / emotion / fact / person / preference
            
            -- 重要性与检索
            importance REAL DEFAULT 0.5,           -- 重要性 0-1
            emotional_valence REAL DEFAULT 0,      -- 情感倾向 -1(负面) 到 1(正面)
            access_count INTEGER DEFAULT 0,        -- 被访问次数
            last_accessed REAL DEFAULT 0,          -- 最后访问时间
            
            -- 元数据
            source TEXT DEFAULT '',                -- 来源 (chat / refinement / manual / system)
            related_people TEXT DEFAULT '[]',      -- 相关人物
            tags TEXT DEFAULT '[]',                -- 标签
            metadata TEXT DEFAULT '{}',            -- 其他元数据
            
            -- 时间
            occurred_at REAL DEFAULT 0,            -- 事件发生时间（可能是过去的事）
            created_at REAL NOT NULL,
            consolidated INTEGER DEFAULT 0         -- 是否已整理
        );
        CREATE INDEX IF NOT EXISTS idx_memories_agent ON agent_memories(agent_id);
        CREATE INDEX IF NOT EXISTS idx_memories_type ON agent_memories(agent_id, memory_type);
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON agent_memories(agent_id, importance DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_category ON agent_memories(agent_id, category);
        
        -- ==================== 炼化记录表 ====================
        CREATE TABLE IF NOT EXISTS refinement_logs (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            source_type TEXT NOT NULL,             -- text / voice / video / chat_history
            source_url TEXT DEFAULT '',
            extracted_data TEXT DEFAULT '{}',      -- 提取的数据
            status TEXT DEFAULT 'success',
            created_at REAL NOT NULL
        );
        
        -- ==================== 好友关系表 ====================
        CREATE TABLE IF NOT EXISTS friendships (
            user_id TEXT NOT NULL,
            friend_id TEXT NOT NULL,
            status TEXT DEFAULT 'accepted',
            created_at REAL NOT NULL,
            PRIMARY KEY (user_id, friend_id)
        );
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
