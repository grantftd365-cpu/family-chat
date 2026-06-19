"""WebSocket 管理器 - 实时消息"""
import asyncio
import json
import time
from typing import Optional
from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """WebSocket 连接管理"""

    def __init__(self):
        # user_id -> list[WebSocket]
        self._connections: dict[str, list[WebSocket]] = {}
        # group_id -> set[user_id]
        self._group_members: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket):
        """用户连接"""
        await websocket.accept()
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = []
            self._connections[user_id].append(websocket)
        logger.info(f"WebSocket 连接: {user_id} (共 {len(self._connections[user_id])} 个)")

    async def disconnect(self, user_id: str, websocket: WebSocket):
        """用户断开"""
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id] = [
                    ws for ws in self._connections[user_id] if ws != websocket
                ]
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info(f"WebSocket 断开: {user_id}")

    async def join_group(self, user_id: str, group_id: str):
        """加入群聊（订阅消息）"""
        async with self._lock:
            if group_id not in self._group_members:
                self._group_members[group_id] = set()
            self._group_members[group_id].add(user_id)

    async def leave_group(self, user_id: str, group_id: str):
        """离开群聊"""
        async with self._lock:
            if group_id in self._group_members:
                self._group_members[group_id].discard(user_id)

    async def send_to_user(self, user_id: str, message: dict):
        """发送消息给指定用户"""
        connections = self._connections.get(user_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)
        
        # 清理断开的连接
        if dead:
            async with self._lock:
                if user_id in self._connections:
                    self._connections[user_id] = [
                        ws for ws in self._connections[user_id] if ws not in dead
                    ]

    async def broadcast_to_group(self, group_id: str, message: dict, exclude_user: str = ""):
        """群发消息"""
        members = self._group_members.get(group_id, set())
        tasks = []
        for user_id in members:
            if user_id != exclude_user:
                tasks.append(self.send_to_user(user_id, message))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def is_online(self, user_id: str) -> bool:
        """用户是否在线"""
        return user_id in self._connections and len(self._connections[user_id]) > 0

    def get_online_count(self) -> int:
        """在线用户数"""
        return len(self._connections)


# 全局实例
ws_manager = ConnectionManager()
