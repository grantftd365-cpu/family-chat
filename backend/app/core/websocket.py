"""WebSocket 管理器 - 增强版（支持已读回执、打字提示、在线状态）"""
import asyncio
import json
import time
from typing import Optional
from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}
        self._group_members: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = []
            self._connections[user_id].append(websocket)
        logger.info(f"WS + {user_id} ({len(self._connections[user_id])}个连接)")

    async def disconnect(self, user_id: str, websocket: WebSocket):
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id] = [ws for ws in self._connections[user_id] if ws != websocket]
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info(f"WS - {user_id}")

    async def join_group(self, user_id: str, group_id: str):
        async with self._lock:
            if group_id not in self._group_members:
                self._group_members[group_id] = set()
            self._group_members[group_id].add(user_id)

    async def leave_group(self, user_id: str, group_id: str):
        async with self._lock:
            if group_id in self._group_members:
                self._group_members[group_id].discard(user_id)

    async def send_to_user(self, user_id: str, message: dict):
        connections = self._connections.get(user_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)
        if dead:
            async with self._lock:
                if user_id in self._connections:
                    self._connections[user_id] = [ws for ws in self._connections[user_id] if ws not in dead]

    async def broadcast_to_group(self, group_id: str, message: dict, exclude_user: str = ""):
        members = self._group_members.get(group_id, set())
        tasks = []
        for user_id in members:
            if user_id != exclude_user:
                tasks.append(self.send_to_user(user_id, message))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def is_online(self, user_id: str) -> bool:
        return user_id in self._connections and len(self._connections[user_id]) > 0

    def get_online_count(self) -> int:
        return len(self._connections)

    def get_group_online(self, group_id: str) -> list[str]:
        members = self._group_members.get(group_id, set())
        return [uid for uid in members if self.is_online(uid)]


ws_manager = ConnectionManager()
