#!/usr/bin/env python3
"""
FamilyChat 小程序相关功能测试
测试 wx-login、数据库字段、WebSocket、小程序 API 兼容性

用法：python3 test_miniprogram.py
前提：服务已启动 (python3 run.py)
"""
import json
import sys
import time
import requests

BASE = "http://localhost:8000"
TOKEN = ""
USER = {}

passed = 0
failed = 0
total = 0


def api(method, path, data=None, tok=None, files=None, params=None):
    headers = {}
    t = tok or TOKEN
    if t:
        headers["Authorization"] = f"Bearer {t}"
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
    global passed, failed, total
    total += 1
    if condition:
        print(f"  ✅ {name}" + (f" ({detail})" if detail else ""))
        passed += 1
        return True
    else:
        print(f"  ❌ {name}" + (f" ({detail})" if detail else ""))
        failed += 1
        return False


# ==================== 模块1: 服务健康 ====================

def test_health():
    print("\n🏥 模块1: 服务健康检查")
    r = api("GET", "/api/status")
    check("服务运行中", r.status_code == 200)
    return r.status_code == 200


# ==================== 模块2: wx-login 接口测试 ====================

def test_wx_login_no_config():
    """测试 wx-login 在没有配置时的行为"""
    print("\n📱 模块2a: wx-login 无配置测试")
    r = api("POST", "/api/wx-login", {"code": "test_code"})
    check("wx-login 端点存在", r.status_code in [400, 500], f"status={r.status_code}")
    if r.status_code == 400:
        check("返回微信错误信息", "微信登录失败" in r.text or "invalid" in r.text.lower())
    elif r.status_code == 500:
        check("返回未配置提示", "WX_APPID" in r.text or "WX_SECRET" in r.text)
    return True


def test_wx_login_empty_code():
    """测试 wx-login 空 code"""
    print("\n📱 模块2b: wx-login 空 code")
    r = api("POST", "/api/wx-login", {"code": ""})
    check("空 code 被拒绝", r.status_code in [400, 422, 500], f"status={r.status_code}")
    return True


def test_wx_login_invalid_code():
    """测试 wx-login 无效 code"""
    print("\n📱 模块2c: wx-login 无效 code")
    r = api("POST", "/api/wx-login", {"code": "invalid_code_12345"})
    check("无效 code 被拒绝", r.status_code == 400, f"status={r.status_code}")
    if r.status_code == 400:
        check("返回错误信息", "微信登录失败" in r.text)
    return True


# ==================== 模块3: 数据库 wx_openid 字段 ====================

def test_db_schema():
    """测试数据库 schema 包含 wx_openid"""
    print("\n🗄️ 模块3: 数据库 schema 测试")
    import sqlite3
    db_path = "data/familychat.db"
    try:
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        check("users 表存在", "users" in tables)

        cursor = conn.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        check("wx_openid 字段存在", "wx_openid" in columns, f"type={columns.get('wx_openid', 'N/A')}")
        check("wx_unionid 字段存在", "wx_unionid" in columns, f"type={columns.get('wx_unionid', 'N/A')}")

        # 检查索引
        indexes = [r[1] for r in conn.execute("PRAGMA index_list(users)").fetchall()]
        check("wx_openid 索引存在", any("wx_openid" in i for i in indexes), f"indexes={indexes}")

        conn.close()
        return True
    except Exception as e:
        check("数据库访问", False, str(e))
        return False


# ==================== 模块4: 注册用户 ====================

def test_register():
    """注册测试用户"""
    print("\n📧 模块4: 注册测试用户")
    global TOKEN, USER
    r = api("POST", "/api/register", {
        "email": "mp_test@wx.local", "username": "mp_test",
        "password": "***", "nickname": "小程序测试用户", "avatar": "😎",
    })
    if r.status_code == 200:
        data = r.json()
        TOKEN = data.get("token", "")
        USER = data.get("user", {})
        check("注册成功", True, f"id={USER.get('id','')[:12]}")
        return True
    if "已注册" in r.text or "已存在" in r.text:
        r2 = api("POST", "/api/login", {"email": "mp_test@wx.local", "password": "***"})
        if r2.status_code == 200:
            data = r2.json()
            TOKEN = data.get("token", "")
            USER = data.get("user", {})
            check("登录成功", True)
            return True
    check("注册", False, r.text[:100])
    return False


# ==================== 模块5: 小程序 API 兼容性 ====================

def test_api_groups():
    """测试群组 API（小程序会调用）"""
    print("\n💬 模块5a: 群组 API")
    r = api("GET", "/api/groups")
    check("获取群组", r.status_code == 200)
    if r.status_code == 200:
        groups = r.json()
        check("返回列表", isinstance(groups, list))
        check("有默认群", len(groups) > 0)
        if groups:
            g = groups[0]
            check("有 id", bool(g.get("id")))
            check("有 name", bool(g.get("name")))
            check("有 avatar", "avatar" in g)
            check("有 last_message", "last_message" in g)
            check("有 last_time", "last_time" in g)
            check("有 member_count", "member_count" in g)
    return True


def test_api_messages():
    """测试消息 API（小程序会调用）"""
    print("\n💬 模块5b: 消息 API")
    r = api("POST", "/api/messages", {
        "group_id": "family_default", "content": "小程序测试消息 📱",
    })
    check("发送消息", r.status_code == 200)

    r2 = api("GET", "/api/messages/family_default", data={"limit": 10})
    check("获取消息", r2.status_code == 200)
    if r2.status_code == 200:
        msgs = r2.json()
        check("返回列表", isinstance(msgs, list))
        if msgs:
            m = msgs[-1]
            check("消息有 id", bool(m.get("id")))
            check("消息有 content", "content" in m)
            check("消息有 sender_name", bool(m.get("sender_name")))
            check("消息有 sender_avatar", "sender_avatar" in m)
            check("消息有 msg_type", bool(m.get("msg_type")))
            check("消息有 created_at", "created_at" in m)
            check("消息有 reactions", "reactions" in m)
    return True


def test_api_image_upload():
    """测试图片上传（小程序会调用）"""
    print("\n📷 模块5c: 图片上传")
    import struct, zlib
    sig = b'\x89PNG\r\n\x1a\n'
    def chunk(ct, d):
        c = ct + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    png = sig + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + chunk(b'IEND', b'')

    r = api("POST", "/api/upload/image", files={"file": ("test.png", png, "image/png")})
    check("图片上传", r.status_code == 200)
    if r.status_code == 200:
        check("返回 url", bool(r.json().get("url")))
    return True


def test_api_friends():
    """测试好友 API（小程序会调用）"""
    print("\n🤝 模块5d: 好友 API")
    r = api("GET", "/api/friends")
    check("获取好友列表", r.status_code == 200)
    r2 = api("GET", "/api/friends/requests")
    check("获取好友请求", r2.status_code == 200)
    r3 = api("GET", "/api/contacts/search", data={"q": "测试"})
    check("搜索联系人", r3.status_code == 200)
    return True


def test_api_agents():
    """测试 Agent API（小程序会调用）"""
    print("\n🤖 模块5e: Agent API")
    r = api("GET", "/api/agents")
    check("获取 Agent 列表", r.status_code == 200)
    if r.status_code == 200:
        agents = r.json()
        check("返回列表", isinstance(agents, list))
        check("有 Agent", len(agents) > 0, f"count={len(agents)}")
    return True


def test_api_me():
    """测试用户信息 API（小程序会调用）"""
    print("\n👤 模块5f: 用户信息 API")
    r = api("GET", "/api/me")
    check("获取用户信息", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("有 id", bool(d.get("id")))
        check("有 nickname", bool(d.get("nickname")))
        check("有 avatar", "avatar" in d)
        check("有 agent_id", "agent_id" in d)
    return True


def test_api_update_me():
    """测试更新用户信息（小程序会调用）"""
    print("\n✏️ 模块5g: 更新用户信息")
    r = api("PUT", "/api/me", {
        "nickname": "小程序用户改名", "signature": "来自小程序",
    })
    check("更新成功", r.status_code == 200)
    return True


def test_api_favorites():
    """测试收藏 API（小程序会调用）"""
    print("\n⭐ 模块5h: 收藏 API")
    r = api("POST", "/api/favorites", params={"content": "测试收藏", "msg_type": "text"})
    check("添加收藏", r.status_code == 200)
    r2 = api("GET", "/api/favorites")
    check("列出收藏", r2.status_code == 200)
    if r2.status_code == 200:
        check("有收藏", len(r2.json()) > 0)
    return True


def test_api_moments():
    """测试朋友圈 API（小程序会调用）"""
    print("\n📷 模块5i: 朋友圈 API")
    r = api("POST", "/api/moments", {"content": "小程序发布的动态 📱"})
    check("发布动态", r.status_code == 200)
    r2 = api("GET", "/api/moments")
    check("列出朋友圈", r2.status_code == 200)
    return True


def test_api_notifications():
    """测试通知 API（小程序会调用）"""
    print("\n🔔 模块5j: 通知 API")
    r = api("GET", "/api/notifications")
    check("获取通知", r.status_code == 200)
    r2 = api("GET", "/api/notifications/unread-count")
    check("获取未读数", r2.status_code == 200)
    return True


# ==================== 模块6: WebSocket 测试 ====================

def test_websocket():
    """测试 WebSocket 连接"""
    print("\n🔌 模块6: WebSocket 连接")
    import websocket
    import threading
    ws_url = f"ws://localhost:8000/ws?token={TOKEN}"
    try:
        ws = websocket.create_connection(ws_url, timeout=5)
        check("WebSocket 连接成功", True)

        ws.send(json.dumps({"type": "ping"}))
        result = ws.recv()
        data = json.loads(result)
        check("ping/pong 正常", data.get("type") == "pong")

        ws.send(json.dumps({"type": "typing", "group_id": "family_default", "name": "小程序用户"}))
        check("typing 事件发送", True)

        # 测试消息推送（需要另一个用户发送，因为发送者自己被排除）
        # 注册第二个用户
        r_reg = api("POST", "/api/register", {
            "email": "ws_sender@wx.local", "username": "ws_sender",
            "password": "test123", "nickname": "WS发送者",
        })
        sender_token = ""
        if r_reg.status_code == 200:
            sender_token = r_reg.json().get("token", "")
        elif "已" in r_reg.text:
            r_login = api("POST", "/api/login", {"email": "ws_sender@wx.local", "password": "test123"})
            sender_token = r_login.json().get("token", "") if r_login.status_code == 200 else ""

        received_msg = []
        def recv_msg():
            try:
                d = ws.recv()
                received_msg.append(json.loads(d))
            except:
                pass
        t = threading.Thread(target=recv_msg)
        t.start()
        time.sleep(0.5)
        if sender_token:
            api("POST", "/api/messages", {"group_id": "family_default", "content": "WS 推送测试"}, tok=sender_token)
        t.join(timeout=3)
        if received_msg:
            check("WS 收到消息推送", received_msg[0].get("type") == "message")
        else:
            check("WS 收到消息推送", False, "超时")

        ws.close()
        return True
    except Exception as e:
        check("WebSocket 连接", False, str(e))
        return False


# ==================== 模块7: 小程序文件检查 ====================

def test_miniprogram_files():
    """检查小程序文件完整性"""
    print("\n📁 模块7: 小程序文件完整性")
    import os

    required = [
        "miniprogram/app.js", "miniprogram/app.json", "miniprogram/app.wxss",
        "miniprogram/project.config.json", "miniprogram/sitemap.json",
        "miniprogram/utils/util.js", "miniprogram/utils/ws.js",
    ]
    pages = ["index", "chat", "contacts", "profile"]
    for p in pages:
        for ext in [".js", ".wxml", ".wxss", ".json"]:
            required.append(f"miniprogram/pages/{p}/{p}{ext}")

    for f in required:
        check(f"文件: {f}", os.path.exists(f))

    with open("miniprogram/app.json") as f:
        config = json.load(f)
    check("app.json pages >= 4", len(config.get("pages", [])) >= 4)
    check("app.json 有 tabBar", "tabBar" in config)
    check("tabBar 3 个项", len(config.get("tabBar", {}).get("list", [])) == 3)

    with open("miniprogram/project.config.json") as f:
        pc = json.load(f)
    check("appid = wx65823623a0e36d16", pc.get("appid") == "wx65823623a0e36d16")
    return True


# ==================== 模块8: 代码质量 ====================

def test_code_quality():
    """检查小程序代码质量"""
    print("\n🔍 模块8: 代码质量检查")

    with open("miniprogram/app.js") as f:
        c = f.read()
    check("app.js: baseUrl 配置", "baseUrl" in c)
    check("app.js: wxLogin 方法", "wxLogin" in c)
    check("app.js: request 封装", "request" in c)
    check("app.js: uploadFile 封装", "uploadFile" in c)
    check("app.js: token 管理", "token" in c)
    check("app.js: 401 处理", "401" in c)
    check("app.js: 本地缓存", "StorageSync" in c or "storage" in c.lower())

    with open("miniprogram/utils/ws.js") as f:
        ws = f.read()
    check("ws.js: connect", "connect" in ws)
    check("ws.js: reconnect", "reconnect" in ws)
    check("ws.js: heartbeat", "heartbeat" in ws or "Heartbeat" in ws)
    check("ws.js: on/off 事件", "on(" in ws and "off(" in ws)
    check("ws.js: send", "send" in ws)

    with open("miniprogram/pages/chat/chat.js") as f:
        ch = f.read()
    check("chat.js: sendMessage", "sendMessage" in ch)
    check("chat.js: loadMessages", "loadMessages" in ch)
    check("chat.js: WebSocket 监听", "ws.on" in ch)
    check("chat.js: 图片上传", "chooseMedia" in ch or "chooseImage" in ch)
    check("chat.js: 撤回功能", "recall" in ch.lower())
    check("chat.js: 消息渲染", "isMine" in ch)
    check("chat.js: 滚动到底部", "scrollToBottom" in ch or "scrollTo" in ch)

    with open("miniprogram/pages/index/index.js") as f:
        idx = f.read()
    check("index.js: 群组列表", "groups" in idx)
    check("index.js: 下拉刷新", "onPullDownRefresh" in idx)
    check("index.js: 登录检查", "isLoggedIn" in idx or "wxLogin" in idx)

    return True


# ==================== 主流程 ====================

def main():
    global passed, failed, total
    print("=" * 60)
    print("📱 FamilyChat 小程序功能测试")
    print("=" * 60)

    def run(name, func, *args):
        try:
            func(*args)
        except Exception as e:
            print(f"  💥 异常: {e}")
            global total, failed
            total += 1
            failed += 1

    if not test_health():
        print("\n❌ 服务未启动！")
        sys.exit(1)

    run("wx-login 无配置", test_wx_login_no_config)
    run("wx-login 空 code", test_wx_login_empty_code)
    run("wx-login 无效 code", test_wx_login_invalid_code)
    run("数据库 schema", test_db_schema)
    run("注册用户", test_register)
    run("群组 API", test_api_groups)
    run("消息 API", test_api_messages)
    run("图片上传", test_api_image_upload)
    run("好友 API", test_api_friends)
    run("Agent API", test_api_agents)
    run("用户信息", test_api_me)
    run("更新用户", test_api_update_me)
    run("收藏 API", test_api_favorites)
    run("朋友圈 API", test_api_moments)
    run("通知 API", test_api_notifications)
    run("WebSocket", test_websocket)
    run("文件完整性", test_miniprogram_files)
    run("代码质量", test_code_quality)

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
