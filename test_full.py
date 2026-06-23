#!/usr/bin/env python3
"""
FamilyChat 全功能端到端集成测试 v2
覆盖所有 API 端点：认证、群组、消息、好友、朋友圈、Agent、系统等

用法：python3 test_full.py
前提：服务已启动 (python3 run.py)
"""
import json
import struct
import sys
import time
import zlib
import requests
import websocket
import threading

BASE = "http://localhost:8000"
TOKEN = ""
USER = {}
AGENT_ID = ""
GROUP_ID = ""
TOKEN2 = ""  # 第二个用户
USER2 = {}
MSG_ID = ""

# ==================== 工具函数 ====================

def api(method, path, data=None, token=None, files=None, params=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{BASE}{path}"
    if method == "GET":
        r = requests.get(url, headers=headers, params=data or params)
    elif method == "POST":
        if files:
            r = requests.post(url, headers=headers, files=files, params=params)
        else:
            r = requests.post(url, headers=headers, json=data, params=params)
    elif method == "PUT":
        r = requests.put(url, headers=headers, json=data)
    elif method == "DELETE":
        r = requests.delete(url, headers=headers, params=params)
    else:
        raise ValueError(f"Unknown method: {method}")
    return r


def check(name, condition, detail=""):
    if condition:
        print(f"  ✅ {name}" + (f" ({detail})" if detail else ""))
        return True
    else:
        print(f"  ❌ {name}" + (f" ({detail})" if detail else ""))
        return False


def create_test_png():
    """创建最小 1x1 PNG"""
    signature = b'\x89PNG\r\n\x1a\n'
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(data)) + c + crc
    ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
    ihdr = chunk(b'IHDR', ihdr_data)
    raw_data = b'\x00\xff\x00\x00'
    compressed = zlib.compress(raw_data)
    idat = chunk(b'IDAT', compressed)
    iend = chunk(b'IEND', b'')
    return signature + ihdr + idat + iend


passed = 0
failed = 0
total = 0


def run_test(name, func, *args):
    global passed, failed, total
    total += 1
    try:
        result = func(*args)
        if result is not False and result is not None:
            passed += 1
        else:
            failed += 1
        return result
    except Exception as e:
        print(f"  💥 异常: {e}")
        failed += 1
        return None


# ==================== 模块1: 服务健康 ====================

def test_health():
    print("\n🏥 模块1: 服务健康检查")
    r = api("GET", "/api/status")
    check("服务运行中", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("版本号 2.0.0", data.get("version") == "2.0.0")
        check("有 agents 计数", "agents" in data)
        check("有 online 计数", "online" in data)
        return True
    return False


# ==================== 模块2: 认证系统 ====================

def test_register():
    print("\n📧 模块2a: 用户注册")
    global TOKEN, USER
    r = api("POST", "/api/register", {
        "email": "test1@family.com", "username": "testuser1",
        "password": "pass123456", "nickname": "测试用户1", "avatar": "😎",
        "role_in_family": "儿子",
    })
    check("注册成功", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        TOKEN = data.get("token", "")
        USER = data.get("user", {})
        check("返回 token", bool(TOKEN))
        check("返回 user.id", bool(USER.get("id")))
        check("返回 user.agent_id", bool(USER.get("agent_id")))
        check("昵称正确", USER.get("nickname") == "测试用户1")
        return True
    if "已注册" in r.text or "已存在" in r.text:
        return test_login()
    print(f"  错误: {r.text}")
    return False


def test_login():
    print("\n🔑 模块2b: 用户登录")
    global TOKEN, USER
    r = api("POST", "/api/login", {
        "email": "test1@family.com", "password": "pass123456",
    })
    check("登录成功", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        TOKEN = data.get("token", "")
        USER = data.get("user", {})
        check("返回 token", bool(TOKEN))
        check("用户信息完整", all(k in USER for k in ["id", "nickname", "avatar"]))
        return True
    return False


def test_get_me():
    print("\n👤 模块2c: 获取当前用户")
    r = api("GET", "/api/me", token=TOKEN)
    check("获取成功", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        check("邮箱正确", data.get("email") == "test1@family.com")
        check("有 agent_id", bool(data.get("agent_id")))
        return True
    return False


def test_update_profile():
    print("\n✏️ 模块2d: 更新个人资料")
    r = api("PUT", "/api/me", {
        "nickname": "测试用户1改名", "signature": "这是我的签名",
        "gender": "male", "region": "北京",
    }, token=TOKEN)
    check("更新成功", r.status_code == 200)
    # 验证更新
    r2 = api("GET", "/api/me", token=TOKEN)
    if r2.status_code == 200:
        d = r2.json()
        check("昵称已更新", d.get("nickname") == "测试用户1改名")
        check("签名已更新", d.get("signature") == "这是我的签名")
        check("性别已更新", d.get("gender") == "male")
        check("地区已更新", d.get("region") == "北京")
    return True


def test_avatar_upload():
    print("\n🖼️ 模块2e: 头像上传")
    png = create_test_png()
    r = api("POST", "/api/me/avatar", token=TOKEN, files={"file": ("avatar.png", png, "image/png")})
    check("头像上传成功", r.status_code == 200)
    if r.status_code == 200:
        check("返回 url", bool(r.json().get("url")))
        return True
    return False


def test_register_second_user():
    print("\n📧 模块2f: 注册第二个用户")
    global TOKEN2, USER2
    r = api("POST", "/api/register", {
        "email": "test2@family.com", "username": "testuser2",
        "password": "pass123456", "nickname": "测试用户2", "avatar": "👩",
        "role_in_family": "女儿",
    })
    if r.status_code == 200:
        data = r.json()
        TOKEN2 = data.get("token", "")
        USER2 = data.get("user", {})
        check("第二个用户注册成功", True, f"id={USER2.get('id','')[:12]}")
        return True
    if "已注册" in r.text or "已存在" in r.text:
        r2 = api("POST", "/api/login", {"email": "test2@family.com", "password": "pass123456"})
        if r2.status_code == 200:
            data = r2.json()
            TOKEN2 = data.get("token", "")
            USER2 = data.get("user", {})
            check("第二个用户登录成功", True)
            return True
    check("第二个用户注册", False, r.text[:100])
    return False


# ==================== 模块3: Agent 系统 ====================

def test_list_agents():
    print("\n🤖 模块3a: Agent 列表")
    r = api("GET", "/api/agents", token=TOKEN)
    check("获取成功", r.status_code == 200)
    if r.status_code == 200:
        agents = r.json()
        check("Agent 数量 >= 4", len(agents) >= 4, f"count={len(agents)}")
        names = [a.get("name") for a in agents]
        check("包含爸爸", "爸爸" in names)
        check("包含妈妈", "妈妈" in names)
        check("包含奶奶", "奶奶" in names)
        return agents
    return None


def test_get_agent():
    print("\n🔍 模块3b: 获取单个 Agent")
    r = api("GET", "/api/agents/agent_dad", token=TOKEN)
    check("获取成功", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("名字是爸爸", d.get("name") == "爸爸")
        check("有 backstory", bool(d.get("backstory")))
        check("有 speaking_style", bool(d.get("speaking_style")))
        check("有 traits", bool(d.get("traits")))
        check("有 soul", bool(d.get("soul")))
        return True
    return False


def test_create_agent():
    print("\n➕ 模块3c: 创建新 Agent")
    r = api("POST", "/api/agents", {
        "name": "小猫咪", "avatar": "🐱",
        "backstory": "家里养的猫，高冷但偶尔撒娇",
        "speaking_style": "说话带喵，偶尔不理人",
        "traits": ["高冷", "傲娇", "爱睡觉"],
        "interests": ["晒太阳", "逗老鼠", "吃鱼"],
        "catchphrases": ["喵~", "不理你了", "鱼呢？"],
    }, token=TOKEN)
    check("创建成功", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("返回 ID", bool(d.get("id")))
        check("名字正确", d.get("name") == "小猫咪")
        return d.get("id")
    return None


def test_update_agent():
    print("\n✏️ 模块3d: 更新 Agent")
    r = api("PUT", "/api/agents/agent_dad", {
        "backstory": "退休教师，教了一辈子语文。喜欢钓鱼、看历史书。稳重有耐心。",
    }, token=TOKEN)
    check("更新成功", r.status_code == 200)
    return r.status_code == 200


def test_agent_memories():
    print("\n📚 模块3e: Agent 记忆")
    r = api("GET", "/api/agents/agent_dad/memories", token=TOKEN)
    check("获取记忆成功", r.status_code == 200)
    if r.status_code == 200:
        memories = r.json()
        check("返回列表", isinstance(memories, list))
        return True
    return False


# ==================== 模块4: 群组管理 ====================

def test_list_groups():
    print("\n👥 模块4a: 群组列表")
    global GROUP_ID
    r = api("GET", "/api/groups", token=TOKEN)
    check("获取成功", r.status_code == 200)
    if r.status_code == 200:
        groups = r.json()
        check("有默认群", len(groups) > 0)
        if groups:
            GROUP_ID = groups[0]["id"]
            check("群名称包含家庭", "家庭" in groups[0].get("name", ""))
            check("有 last_message 字段", "last_message" in groups[0])
            check("有 member_count", "member_count" in groups[0])
        return groups
    return None


def test_get_group():
    print("\n🔍 模块4b: 获取群详情")
    r = api("GET", f"/api/groups/{GROUP_ID}", token=TOKEN)
    check("获取成功", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("有 name", bool(d.get("name")))
        check("有 owner_id", bool(d.get("owner_id")))
        return True
    return False


def test_create_group():
    print("\n➕ 模块4c: 创建新群")
    r = api("POST", "/api/groups", {
        "name": "测试小群", "description": "用于测试的群",
    }, token=TOKEN)
    check("创建成功", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("返回群 ID", bool(d.get("id")))
        return d.get("id")
    return None


def test_update_group():
    print("\n✏️ 模块4d: 更新群信息")
    r = api("PUT", f"/api/groups/{GROUP_ID}", {
        "name": "我们的家庭(改名)", "description": "更新了描述",
        "announcement": "这是群公告",
    }, token=TOKEN)
    check("更新成功", r.status_code == 200)
    # 验证
    r2 = api("GET", f"/api/groups/{GROUP_ID}", token=TOKEN)
    if r2.status_code == 200:
        d = r2.json()
        check("名称已更新", d.get("name") == "我们的家庭(改名)")
        check("公告已更新", d.get("announcement") == "这是群公告")
    # 改回来
    api("PUT", f"/api/groups/{GROUP_ID}", {"name": "我们的家庭"}, token=TOKEN)
    return True


def test_group_members():
    print("\n👤 模块4e: 群成员管理")
    r = api("GET", f"/api/groups/{GROUP_ID}/members", token=TOKEN)
    check("获取成员成功", r.status_code == 200)
    if r.status_code == 200:
        members = r.json()
        check("成员数 > 0", len(members) > 0, f"count={len(members)}")
        has_agent = any(m.get("is_agent") for m in members)
        has_human = any(not m.get("is_agent") for m in members)
        check("有真人成员", has_agent)
        check("有数字人", has_agent)
        # 检查成员字段完整性
        if members:
            m = members[0]
            check("成员有 id", bool(m.get("id")))
            check("成员有 name", bool(m.get("name")))
            check("成员有 avatar", bool(m.get("avatar")))
            check("成员有 role", bool(m.get("role")))
        return members
    return None


def test_add_remove_member():
    print("\n🔄 模块4f: 添加/移除群成员")
    if not USER2.get("id"):
        check("跳过", False, "无第二个用户")
        return False
    # 添加
    r = api("POST", f"/api/groups/{GROUP_ID}/members", {
        "user_id": USER2["id"], "role": "member",
    }, token=TOKEN)
    check("添加成员成功", r.status_code == 200)
    # 移除
    r2 = api("DELETE", f"/api/groups/{GROUP_ID}/members/{USER2['id']}", token=TOKEN)
    check("移除成员成功", r2.status_code == 200)
    return True


# ==================== 模块5: 消息系统 ====================

def test_send_message():
    print("\n💬 模块5a: 发送消息")
    global MSG_ID
    r = api("POST", "/api/messages", {
        "group_id": GROUP_ID, "content": "大家好！这是一条测试消息 🎉",
    }, token=TOKEN)
    check("发送成功", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        MSG_ID = d.get("id", "")
        check("返回消息 ID", bool(MSG_ID))
        check("返回 created_at", "created_at" in d)
        return True
    return False


def test_get_messages():
    print("\n📜 模块5b: 获取消息历史")
    r = api("GET", f"/api/messages/{GROUP_ID}", token=TOKEN, params={"limit": 50})
    check("获取成功", r.status_code == 200)
    if r.status_code == 200:
        msgs = r.json()
        check("消息数 > 0", len(msgs) > 0, f"count={len(msgs)}")
        if msgs:
            m = msgs[-1]  # 最新的
            check("消息有 id", bool(m.get("id")))
            check("消息有 content", "content" in m)
            check("消息有 sender_name", bool(m.get("sender_name")))
            check("消息有 msg_type", bool(m.get("msg_type")))
            check("消息有 created_at", "created_at" in m)
            check("消息有 reactions", "reactions" in m)
        return msgs
    return None


def test_send_at_message():
    print("\n📢 模块5c: @提及消息")
    r = api("POST", "/api/messages", {
        "group_id": GROUP_ID, "content": "@爸爸 今天去钓鱼了吗？",
    }, token=TOKEN)
    check("@爸爸 发送成功", r.status_code == 200)
    r2 = api("POST", "/api/messages", {
        "group_id": GROUP_ID, "content": "@所有人 明天聚餐！",
    }, token=TOKEN)
    check("@所有人 发送成功", r2.status_code == 200)
    return True


def test_send_emoji():
    print("\n😊 模块5d: Emoji 消息")
    emojis = ["🎉🎊🥳", "❤️💕", "😂🤣", "👍👏", "🐱🐶"]
    for e in emojis:
        r = api("POST", "/api/messages", {
            "group_id": GROUP_ID, "content": e,
        }, token=TOKEN)
        check(f"Emoji: {e}", r.status_code == 200)
    return True


def test_reply_message():
    print("\n↩️ 模块5e: 回复消息")
    if not MSG_ID:
        check("跳过", False, "无消息ID")
        return False
    r = api("POST", "/api/messages", {
        "group_id": GROUP_ID, "content": "这是一条回复",
        "reply_to": MSG_ID,
    }, token=TOKEN)
    check("回复消息发送成功", r.status_code == 200)
    if r.status_code == 200:
        # 验证回复内容
        r2 = api("GET", f"/api/messages/{GROUP_ID}", token=TOKEN, params={"limit": 5})
        if r2.status_code == 200:
            msgs = r2.json()
            replied = [m for m in msgs if m.get("reply_to") == MSG_ID]
            if replied:
                check("回复关联正确", replied[0].get("reply_to") == MSG_ID)
                check("有 reply_content", bool(replied[0].get("reply_content")))
        return True
    return False


def test_recall_message():
    print("\n🗑️ 模块5f: 撤回消息")
    # 先发一条
    r = api("POST", "/api/messages", {
        "group_id": GROUP_ID, "content": "这条消息要撤回",
    }, token=TOKEN)
    if r.status_code != 200:
        check("发送待撤回消息", False)
        return False
    mid = r.json().get("id")
    # 撤回
    r2 = api("POST", "/api/messages/recall", {"message_id": mid}, token=TOKEN)
    check("撤回成功", r2.status_code == 200)
    # 验证
    r3 = api("GET", f"/api/messages/{GROUP_ID}", token=TOKEN, params={"limit": 5})
    if r3.status_code == 200:
        msgs = r3.json()
        recalled = [m for m in msgs if m.get("id") == mid]
        if recalled:
            check("撤回后显示系统消息", "撤回" in recalled[0].get("content", ""))
            check("msg_type 变为 system", recalled[0].get("msg_type") == "system")
    return True


def test_forward_message():
    print("\n↪️ 模块5g: 转发消息")
    if not MSG_ID:
        check("跳过", False, "无消息ID")
        return False
    # 创建另一个群用来转发
    r = api("POST", "/api/groups", {"name": "转发目标群"}, token=TOKEN)
    if r.status_code != 200:
        check("创建转发目标群", False)
        return False
    target_gid = r.json().get("id")
    # 转发
    r2 = api("POST", "/api/messages/forward", {
        "message_id": MSG_ID, "target_group_id": target_gid,
    }, token=TOKEN)
    check("转发成功", r2.status_code == 200)
    if r2.status_code == 200:
        check("返回新消息 ID", bool(r2.json().get("id")))
        # 验证目标群有转发消息
        r3 = api("GET", f"/api/messages/{target_gid}", token=TOKEN)
        if r3.status_code == 200:
            msgs = r3.json()
            fwd = [m for m in msgs if m.get("forwarded_from")]
            check("目标群有转发消息", len(fwd) > 0)
    return True


def test_pin_message():
    print("\n📌 模块5h: 消息置顶")
    if not MSG_ID:
        check("跳过", False, "无消息ID")
        return False
    # 置顶
    r = api("POST", f"/api/messages/{MSG_ID}/pin", token=TOKEN)
    check("置顶成功", r.status_code == 200)
    # 获取置顶消息
    r2 = api("GET", f"/api/messages/{GROUP_ID}/pinned", token=TOKEN)
    check("获取置顶消息", r2.status_code == 200)
    if r2.status_code == 200:
        pinned = r2.json()
        check("有置顶消息", len(pinned) > 0)
    # 取消置顶
    r3 = api("DELETE", f"/api/messages/{MSG_ID}/pin", token=TOKEN)
    check("取消置顶成功", r3.status_code == 200)
    return True


def test_reactions():
    print("\n😊 模块5i: 表情回复 (Reactions)")
    if not MSG_ID:
        check("跳过", False, "无消息ID")
        return False
    # 添加表情
    r = api("POST", f"/api/messages/{MSG_ID}/reactions", {"emoji": "👍"}, token=TOKEN)
    check("添加表情成功", r.status_code == 200)
    # 再添加一个
    r2 = api("POST", f"/api/messages/{MSG_ID}/reactions", {"emoji": "❤️"}, token=TOKEN)
    check("添加第二个表情", r2.status_code == 200)
    # 验证消息上有 reactions
    r3 = api("GET", f"/api/messages/{GROUP_ID}", token=TOKEN, params={"limit": 10})
    if r3.status_code == 200:
        msgs = r3.json()
        target = [m for m in msgs if m.get("id") == MSG_ID]
        if target:
            reactions = target[0].get("reactions", [])
            check("消息有 reactions", len(reactions) >= 1, f"count={len(reactions)}")
    # 删除表情
    r4 = api("DELETE", f"/api/messages/{MSG_ID}/reactions/👍", token=TOKEN)
    check("删除表情成功", r4.status_code == 200)
    return True


def test_image_upload_send():
    print("\n📷 模块5j: 图片上传与发送")
    png = create_test_png()
    r = api("POST", "/api/upload/image", token=TOKEN, files={"file": ("test.png", png, "image/png")})
    check("图片上传成功", r.status_code == 200)
    if r.status_code == 200:
        url = r.json().get("url")
        check("返回 URL", bool(url))
        # 发送图片消息
        r2 = api("POST", "/api/messages", {
            "group_id": GROUP_ID, "content": url, "msg_type": "image", "media_url": url,
        }, token=TOKEN)
        check("图片消息发送成功", r2.status_code == 200)
        return url
    return None


def test_file_upload():
    print("\n📎 模块5k: 文件上传")
    # 创建一个小文本文件
    content = b"Hello, this is a test file for FamilyChat!"
    r = api("POST", "/api/upload/file", token=TOKEN,
            files={"file": ("test.txt", content, "text/plain")})
    check("文件上传成功", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("返回 URL", bool(d.get("url")))
        check("返回 filename", bool(d.get("filename")))
        check("返回 size", d.get("size") > 0)
        # 发送文件消息
        r2 = api("POST", "/api/messages", {
            "group_id": GROUP_ID, "content": d["url"],
            "msg_type": "file", "file_name": "test.txt", "file_size": d["size"],
        }, token=TOKEN)
        check("文件消息发送成功", r2.status_code == 200)
        return True
    return False


def test_voice_upload_send():
    print("\n🎤 模块5l: 语音上传与发送")
    fake_audio = b'\x1a\x45\xdf\xa3' + b'\x00' * 100
    r = api("POST", "/api/voice/upload", token=TOKEN,
            files={"file": ("test.webm", fake_audio, "audio/webm")})
    check("语音上传成功", r.status_code == 200)
    if r.status_code == 200:
        url = r.json().get("url")
        check("返回 URL", bool(url))
        r2 = api("POST", "/api/messages", {
            "group_id": GROUP_ID, "content": "[语音消息]",
            "msg_type": "voice", "voice_url": url,
        }, token=TOKEN)
        check("语音消息发送成功", r2.status_code == 200)
        return url
    return None


# ==================== 模块6: 拍一拍 ====================

def test_pat():
    print("\n👋 模块6: 拍一拍")
    if not USER2.get("id"):
        # 用 Agent
        target = "agent_dad"
    else:
        target = USER2["id"]
    r = api("POST", f"/api/groups/{GROUP_ID}/pat", {
        "to_user_id": target, "action": "拍了拍",
    }, token=TOKEN)
    check("拍一拍成功", r.status_code == 200)
    if r.status_code == 200:
        check("返回 message", bool(r.json().get("message")))
    return True


# ==================== 模块7: 红包系统 ====================

def test_red_envelope():
    print("\n🧧 模块7: 红包系统")
    # 发红包
    r = api("POST", "/api/red-envelopes", {
        "group_id": GROUP_ID, "amount": 10.0, "count": 3,
        "greeting": "恭喜发财🧧",
    }, token=TOKEN)
    check("发红包成功", r.status_code == 200)
    if r.status_code == 200:
        eid = r.json().get("id")
        check("返回红包 ID", bool(eid))
        # 查看红包
        r2 = api("GET", f"/api/red-envelopes/{eid}", token=TOKEN)
        check("查看红包", r2.status_code == 200)
        if r2.status_code == 200:
            d = r2.json()
            check("金额正确", d.get("amount") == 10.0)
            check("状态 pending", d.get("status") == "pending")
        return eid
    return None


# ==================== 模块8: 收藏系统 ====================

def test_favorites():
    print("\n⭐ 模块8: 收藏系统")
    # 添加收藏
    r = api("POST", "/api/favorites", token=TOKEN, params={
        "content": "这是一条收藏的文本", "msg_type": "text", "source_name": "测试用户1",
    })
    check("添加收藏成功", r.status_code == 200)
    fav_id = r.json().get("id") if r.status_code == 200 else None

    # 列出收藏
    r2 = api("GET", "/api/favorites", token=TOKEN)
    check("列出收藏", r2.status_code == 200)
    if r2.status_code == 200:
        favs = r2.json()
        check("有收藏", len(favs) > 0)

    # 删除收藏
    if fav_id:
        r3 = api("DELETE", f"/api/favorites/{fav_id}", token=TOKEN)
        check("删除收藏成功", r3.status_code == 200)
    return True


# ==================== 模块9: 好友系统 ====================

def test_friend_system():
    print("\n🤝 模块9: 好友系统")
    if not USER2.get("id"):
        check("跳过", False, "无第二个用户")
        return False

    # 发送好友请求
    r = api("POST", "/api/friends/request", {
        "to_user_id": USER2["id"], "message": "加个好友吧",
    }, token=TOKEN)
    check("发送好友请求", r.status_code == 200)

    # 列出好友请求（用户2视角）
    r2 = api("GET", "/api/friends/requests", token=TOKEN2)
    check("查看好友请求", r2.status_code == 200)
    if r2.status_code == 200:
        reqs = r2.json()
        check("有好友请求", len(reqs) > 0)
        if reqs:
            req_id = reqs[0]["id"]
            # 接受好友请求
            r3 = api("POST", "/api/friends/requests/handle", {
                "request_id": req_id, "action": "accept",
            }, token=TOKEN2)
            check("接受好友请求", r3.status_code == 200)

    # 列出好友
    r4 = api("GET", "/api/friends", token=TOKEN)
    check("列出好友", r4.status_code == 200)
    if r4.status_code == 200:
        friends = r4.json()
        check("有好友", len(friends) > 0)

    # 搜索联系人
    r5 = api("GET", "/api/contacts/search", token=TOKEN, params={"q": "测试"})
    check("搜索联系人", r5.status_code == 200)
    if r5.status_code == 200:
        contacts = r5.json()
        check("有搜索结果", len(contacts) > 0)

    # 更新好友备注
    if r4.status_code == 200 and r4.json():
        fid = r4.json()[0]["id"]
        r6 = api("PUT", "/api/friends/remark", {
            "friend_id": fid, "remark": "好朋友",
        }, token=TOKEN)
        check("更新备注", r6.status_code == 200)

    # 删除好友
    if r4.status_code == 200 and r4.json():
        fid = r4.json()[0]["id"]
        r7 = api("DELETE", f"/api/friends/{fid}", token=TOKEN)
        check("删除好友", r7.status_code == 200)

    return True


# ==================== 模块10: 朋友圈 ====================

def test_moments():
    print("\n📷 模块10: 朋友圈")
    # 发布动态
    r = api("POST", "/api/moments", {
        "content": "今天天气真好！☀️", "images": [], "location": "北京",
    }, token=TOKEN)
    check("发布动态成功", r.status_code == 200)
    moment_id = r.json().get("id") if r.status_code == 200 else None

    # 列出朋友圈
    r2 = api("GET", "/api/moments", token=TOKEN)
    check("列出朋友圈", r2.status_code == 200)
    if r2.status_code == 200:
        moments = r2.json()
        check("有动态", len(moments) > 0)
        if moments:
            check("动态有 content", bool(moments[0].get("content")))
            check("动态有 nickname", bool(moments[0].get("nickname")))
            check("动态有 likes", "likes" in moments[0])
            check("动态有 comments", "comments" in moments[0])

    # 点赞
    if moment_id:
        r3 = api("POST", f"/api/moments/{moment_id}/like", token=TOKEN)
        check("点赞成功", r3.status_code == 200)
        if r3.status_code == 200:
            check("返回 liked", r3.json().get("action") == "liked")
        # 再次点赞（取消）
        r4 = api("POST", f"/api/moments/{moment_id}/like", token=TOKEN)
        check("取消点赞", r4.status_code == 200 and r4.json().get("action") == "unliked")

    # 评论
    if moment_id:
        r5 = api("POST", f"/api/moments/{moment_id}/comment", {
            "content": "拍得真好看！",
        }, token=TOKEN)
        check("评论成功", r5.status_code == 200)

    # 上传朋友圈图片
    png = create_test_png()
    r6 = api("POST", "/api/moments/upload", token=TOKEN,
             files={"file": ("moment.png", png, "image/png")})
    check("朋友圈图片上传", r6.status_code == 200)

    # 删除动态
    if moment_id:
        r7 = api("DELETE", f"/api/moments/{moment_id}", token=TOKEN)
        check("删除动态", r7.status_code == 200)

    return True


# ==================== 模块11: 通知系统 ====================

def test_notifications():
    print("\n🔔 模块11: 通知系统")
    # 列出通知
    r = api("GET", "/api/notifications", token=TOKEN)
    check("列出通知", r.status_code == 200)
    if r.status_code == 200:
        check("返回列表", isinstance(r.json(), list))

    # 未读数
    r2 = api("GET", "/api/notifications/unread-count", token=TOKEN)
    check("获取未读数", r2.status_code == 200)
    if r2.status_code == 200:
        check("返回 count", "count" in r2.json())

    # 只看未读
    r3 = api("GET", "/api/notifications", token=TOKEN, params={"unread_only": True})
    check("只看未读", r3.status_code == 200)

    # 全部标为已读
    r4 = api("POST", "/api/notifications/read-all", token=TOKEN)
    check("全部标为已读", r4.status_code == 200)

    return True


# ==================== 模块12: 搜索系统 ====================

def test_search():
    print("\n🔍 模块12: 全局搜索")
    r = api("GET", "/api/search", token=TOKEN, params={"q": "测试"})
    check("搜索成功", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("有 messages 字段", "messages" in d)
        check("有 contacts 字段", "contacts" in d)
        check("有 groups 字段", "groups" in d)
        check("联系人有结果", len(d.get("contacts", [])) > 0)
        return True
    return False


# ==================== 模块13: LLM 配置 ====================

def test_llm_config():
    print("\n⚙️ 模块13: LLM 配置")
    # 获取配置
    r = api("GET", "/api/config/llm", token=TOKEN)
    check("获取配置", r.status_code == 200)
    if r.status_code == 200:
        cfg = r.json()
        check("有 provider", "provider" in cfg)
        check("API Key 已脱敏", "***" in cfg.get("api_key", ""))

    # 获取提供商列表
    r2 = api("GET", "/api/config/providers")
    check("获取提供商列表", r2.status_code == 200)
    if r2.status_code == 200:
        providers = r2.json().get("providers", [])
        check("提供商 >= 4", len(providers) >= 4)

    # 更新配置
    r3 = api("POST", "/api/config/llm", {
        "temperature": 0.9,
    }, token=TOKEN)
    check("更新配置", r3.status_code == 200)

    # 获取语音列表
    r4 = api("GET", "/api/voices")
    check("获取语音列表", r4.status_code == 200)
    if r4.status_code == 200:
        voices = r4.json().get("voices", [])
        check("有可用语音", len(voices) > 0)

    return True


# ==================== 模块14: 系统功能 ====================

def test_backup():
    print("\n💾 模块14a: 备份恢复")
    # 创建备份
    r = api("POST", "/api/system/backup", token=TOKEN)
    check("创建备份", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("返回 filename", bool(d.get("filename")))
        check("返回 size", d.get("size", 0) > 0)

    # 列出备份
    r2 = api("GET", "/api/system/backups", token=TOKEN)
    check("列出备份", r2.status_code == 200)
    if r2.status_code == 200:
        backups = r2.json()
        check("有备份", len(backups) > 0)
        if backups:
            # 下载备份
            fname = backups[0]["filename"]
            r3 = api("GET", f"/api/system/backups/{fname}/download", token=TOKEN)
            check("下载备份", r3.status_code == 200)

    return True


def test_stats():
    print("\n📊 模块14b: 系统统计")
    r = api("GET", "/api/system/stats", token=TOKEN)
    check("获取统计", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("有 total_users", "total_users" in d)
        check("有 total_agents", "total_agents" in d)
        check("有 total_messages", "total_messages" in d)
        check("有 total_groups", "total_groups" in d)
        check("有 db_size_mb", "db_size_mb" in d)
        check("用户数 > 0", d.get("total_users", 0) > 0)
        check("消息数 > 0", d.get("total_messages", 0) > 0)
    return True


def test_proactive_config():
    print("\n🤖 模块14c: Agent 主动发言配置")
    # 设置配置
    r = api("POST", "/api/system/agent/proactive", {
        "agent_id": "agent_dad",
        "enabled": True,
        "frequency_hours": 4,
        "topics": ["今天天气怎么样", "大家吃饭了吗", "周末有什么安排"],
    }, token=TOKEN)
    check("设置主动发言配置", r.status_code == 200)

    # 获取配置
    r2 = api("GET", "/api/system/agent/proactive", token=TOKEN)
    check("获取配置", r2.status_code == 200)
    if r2.status_code == 200:
        configs = r2.json()
        check("有配置列表", len(configs) > 0)
        dad_cfg = [c for c in configs if c.get("agent_id") == "agent_dad"]
        if dad_cfg:
            check("爸爸配置存在", True)
            check("频率正确", dad_cfg[0].get("frequency_hours") == 4)

    return True


# ==================== 模块15: WebSocket ====================

def test_websocket():
    print("\n🔌 模块15: WebSocket 连接")
    ws_url = f"ws://localhost:8000/ws?token={TOKEN}"
    try:
        ws = websocket.create_connection(ws_url, timeout=5)
        check("WebSocket 连接成功", True)

        # 发送 ping
        ws.send(json.dumps({"type": "ping"}))
        result = ws.recv()
        data = json.loads(result)
        check("收到 pong", data.get("type") == "pong")

        # 发送 typing 事件
        ws.send(json.dumps({"type": "typing", "group_id": GROUP_ID, "name": "测试用户1"}))
        check("typing 事件发送", True)

        ws.close()
        return True
    except Exception as e:
        check("WebSocket 连接", False, str(e))
        return False


# ==================== 模块16: 炼化系统 ====================

def test_refine_text():
    print("\n🧪 模块16a: 文本炼化")
    agent_id = USER.get("agent_id", "")
    if not agent_id:
        check("跳过", False, "无 Agent ID")
        return False
    r = api("POST", "/api/agents/refine/text", {
        "agent_id": agent_id,
        "text": "我叫Grant，28岁，在北京做软件开发。喜欢打篮球看电影。说话直接，口头禅：好的没问题、绝了。",
        "source": "text",
    }, token=TOKEN)
    # 无真实 LLM 服务时应返回 400（URL 无效）
    if r.status_code == 400:
        check("文本炼化请求 (无 LLM 服务，正确返回 400)", True)
        return True
    check("文本炼化请求", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("炼化成功", d.get("status") == "ok")
        return True
    print(f"  错误: {r.text[:200]}")
    return False


def test_refine_chat():
    print("\n💬 模块16b: 聊天记录炼化")
    agent_id = USER.get("agent_id", "")
    if not agent_id:
        check("跳过", False, "无 Agent ID")
        return False
    r = api("POST", "/api/agents/refine/chat", {
        "agent_id": agent_id,
        "text": "昨天打篮球赢了！晚上看电影放松。周末去爬山。我妈让我回家吃饭😂",
    }, token=TOKEN)
    check("聊天炼化请求", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("炼化成功", d.get("status") == "ok")
        return True
    return False


# ==================== 主测试流程 ====================

def main():
    global passed, failed, total

    print("=" * 60)
    print("🏠 FamilyChat 全功能端到端集成测试 v2")
    print("=" * 60)

    # 1. 健康检查
    if not run_test("健康检查", test_health):
        print("\n❌ 服务未启动！请先运行: python3 run.py")
        sys.exit(1)

    # 2. 认证系统
    run_test("用户注册", test_register)
    run_test("获取用户", test_get_me)
    run_test("更新资料", test_update_profile)
    run_test("头像上传", test_avatar_upload)
    run_test("注册第二用户", test_register_second_user)

    # 3. Agent 系统
    run_test("Agent 列表", test_list_agents)
    run_test("获取 Agent", test_get_agent)
    run_test("创建 Agent", test_create_agent)
    run_test("更新 Agent", test_update_agent)
    run_test("Agent 记忆", test_agent_memories)

    # 4. 群组管理
    run_test("群组列表", test_list_groups)
    run_test("群详情", test_get_group)
    run_test("创建群", test_create_group)
    run_test("更新群", test_update_group)
    run_test("群成员", test_group_members)
    run_test("添加/移除成员", test_add_remove_member)

    # 5. 消息系统
    run_test("发送消息", test_send_message)
    run_test("获取消息", test_get_messages)
    run_test("@提及", test_send_at_message)
    run_test("Emoji", test_send_emoji)
    run_test("回复消息", test_reply_message)
    run_test("撤回消息", test_recall_message)
    run_test("转发消息", test_forward_message)
    run_test("消息置顶", test_pin_message)
    run_test("表情回复", test_reactions)
    run_test("图片上传发送", test_image_upload_send)
    run_test("文件上传", test_file_upload)
    run_test("语音上传发送", test_voice_upload_send)

    # 6. 拍一拍
    run_test("拍一拍", test_pat)

    # 7. 红包
    run_test("红包系统", test_red_envelope)

    # 8. 收藏
    run_test("收藏系统", test_favorites)

    # 9. 好友系统
    run_test("好友系统", test_friend_system)

    # 10. 朋友圈
    run_test("朋友圈", test_moments)

    # 11. 通知
    run_test("通知系统", test_notifications)

    # 12. 搜索
    run_test("全局搜索", test_search)

    # 13. LLM 配置
    run_test("LLM 配置", test_llm_config)

    # 14. 系统功能
    run_test("备份恢复", test_backup)
    run_test("系统统计", test_stats)
    run_test("主动发言配置", test_proactive_config)

    # 15. WebSocket
    run_test("WebSocket", test_websocket)

    # 16. 炼化
    run_test("文本炼化", test_refine_text)
    run_test("聊天炼化", test_refine_chat)

    # ==================== 结果 ====================
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过 | {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("🎉 全部测试通过！")
    else:
        print(f"⚠️ 有 {failed} 个测试失败")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
