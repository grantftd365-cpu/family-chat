"""WebRTC 信令服务 — 语音/视频通话

架构:
1. 呼叫方通过 WebSocket 发送 offer
2. 服务端转发 offer 给被叫方
3. 被叫方通过 WebSocket 发送 answer
4. 双方交换 ICE candidate
5. P2P 连接建立后直接通话（音频/视频流不经过服务器）

限制:
- 需要 STUN/TURN 服务器处理 NAT 穿透
- 仅支持 1v1 通话（群通话需要 SFU，复杂度高）
- 移动端需要原生 WebRTC 支持（uni-app 需要 native 插件或 WebView）
"""
import json
import time
from loguru import logger

from ..core.websocket import ws_manager
from ..models.database import get_db, gen_id, now


# 通话状态管理
_active_calls: dict[str, dict] = {}  # call_id -> call_info


async def handle_call_signaling(user_id: str, data: dict):
    """处理通话信令消息"""
    action = data.get("action", "")
    call_id = data.get("call_id", "")
    target_id = data.get("target_id", "")

    if action == "call_invite":
        # 发起通话邀请
        call_type = data.get("call_type", "voice")  # voice / video
        call_id = call_id or gen_id()

        # 检查目标用户是否在线
        if not ws_manager.is_online(target_id):
            await ws_manager.send_to_user(user_id, {
                "type": "call_event",
                "data": {
                    "action": "call_failed",
                    "call_id": call_id,
                    "reason": "对方不在线",
                }
            })
            return

        # 检查目标用户是否正在通话中
        for cid, cinfo in _active_calls.items():
            if target_id in (cinfo.get("caller_id"), cinfo.get("callee_id")):
                await ws_manager.send_to_user(user_id, {
                    "type": "call_event",
                    "data": {
                        "action": "call_failed",
                        "call_id": call_id,
                        "reason": "对方正在通话中",
                    }
                })
                return

        # 创建通话记录
        _active_calls[call_id] = {
            "caller_id": user_id,
            "callee_id": target_id,
            "call_type": call_type,
            "status": "ringing",
            "started_at": time.time(),
        }

        # 获取呼叫方信息
        db = await get_db()
        try:
            async with db.execute("SELECT nickname, avatar FROM users WHERE id=?", (user_id,)) as c:
                row = await c.fetchone()
                caller_name = row[0] if row else "unknown"
                caller_avatar = row[1] if row else "😀"
        finally:
            await db.close()

        # 转发通话邀请给被叫方
        await ws_manager.send_to_user(target_id, {
            "type": "call_event",
            "data": {
                "action": "call_invite",
                "call_id": call_id,
                "call_type": call_type,
                "caller_id": user_id,
                "caller_name": caller_name,
                "caller_avatar": caller_avatar,
            }
        })

        logger.info(f"通话邀请: {user_id} -> {target_id} ({call_type}) call_id={call_id}")

    elif action == "call_accept":
        # 被叫方接听
        if call_id in _active_calls:
            _active_calls[call_id]["status"] = "connected"
            _active_calls[call_id]["connected_at"] = time.time()

            # 通知呼叫方
            await ws_manager.send_to_user(_active_calls[call_id]["caller_id"], {
                "type": "call_event",
                "data": {
                    "action": "call_accept",
                    "call_id": call_id,
                }
            })
            logger.info(f"通话接通: {call_id}")

    elif action == "call_reject":
        # 被叫方拒接
        if call_id in _active_calls:
            _active_calls[call_id]["status"] = "rejected"
            await ws_manager.send_to_user(_active_calls[call_id]["caller_id"], {
                "type": "call_event",
                "data": {
                    "action": "call_reject",
                    "call_id": call_id,
                }
            })
            del _active_calls[call_id]
            logger.info(f"通话拒接: {call_id}")

    elif action == "call_end":
        # 任一方挂断
        if call_id in _active_calls:
            call = _active_calls[call_id]
            other_id = call["callee_id"] if user_id == call["caller_id"] else call["caller_id"]
            await ws_manager.send_to_user(other_id, {
                "type": "call_event",
                "data": {
                    "action": "call_end",
                    "call_id": call_id,
                }
            })
            # 记录通话时长
            duration = 0
            if call.get("connected_at"):
                duration = int(time.time() - call["connected_at"])
            del _active_calls[call_id]
            logger.info(f"通话结束: {call_id} 时长={duration}s")

    elif action == "call_offer":
        # 转发 SDP offer
        if call_id in _active_calls:
            call = _active_calls[call_id]
            target = call["callee_id"] if user_id == call["caller_id"] else call["caller_id"]
            await ws_manager.send_to_user(target, {
                "type": "call_event",
                "data": {
                    "action": "call_offer",
                    "call_id": call_id,
                    "sdp": data.get("sdp", ""),
                }
            })

    elif action == "call_answer":
        # 转发 SDP answer
        if call_id in _active_calls:
            call = _active_calls[call_id]
            target = call["caller_id"] if user_id == call["callee_id"] else call["callee_id"]
            await ws_manager.send_to_user(target, {
                "type": "call_event",
                "data": {
                    "action": "call_answer",
                    "call_id": call_id,
                    "sdp": data.get("sdp", ""),
                }
            })

    elif action == "call_candidate":
        # 转发 ICE candidate
        if call_id in _active_calls:
            call = _active_calls[call_id]
            target = call["callee_id"] if user_id == call["caller_id"] else call["caller_id"]
            await ws_manager.send_to_user(target, {
                "type": "call_event",
                "data": {
                    "action": "call_candidate",
                    "call_id": call_id,
                    "candidate": data.get("candidate", ""),
                }
            })
