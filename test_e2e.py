#!/usr/bin/env python3
"""
FamilyChat 端到端集成测试
测试全流程：注册 → 登录 → 创建Agent → 发消息 → 炼化 → 群聊 → Agent回复

用法：
    python test_e2e.py

前提：服务已启动 (python run.py)
"""
import json
import sys
import time
import requests

BASE = "http://localhost:8000"
TOKEN = ""
USER = {}
AGENT = {}

# ==================== 工具函数 ====================

def api(method, path, data=None, token=None, files=None):
    """API 请求"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"{BASE}{path}"
    
    if method == "GET":
        r = requests.get(url, headers=headers, params=data)
    elif method == "POST":
        if files:
            r = requests.post(url, headers=headers, files=files)
        else:
            r = requests.post(url, headers=headers, json=data)
    elif method == "DELETE":
        r = requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return r


def check(name, condition, detail=""):
    """检查测试结果"""
    if condition:
        print(f"  ✅ {name}" + (f" ({detail})" if detail else ""))
        return True
    else:
        print(f"  ❌ {name}" + (f" ({detail})" if detail else ""))
        return False


# ==================== 测试用例 ====================

def test_01_health():
    """测试1: 服务健康检查"""
    print("\n🏥 测试1: 服务健康检查")
    r = api("GET", "/api/status")
    check("服务运行中", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("版本号正确", data.get("version") == "2.0.0")
        return True
    return False


def test_02_register():
    """测试2: 邮箱注册"""
    print("\n📧 测试2: 邮箱注册 (grantftd365@gmail.com)")
    global TOKEN, USER
    
    r = api("POST", "/api/register", {
        "email": "grantftd365@gmail.com",
        "username": "grant",
        "password": "test123456",
        "nickname": "Grant",
        "avatar": "😎",
        "role_in_family": "儿子",
    })
    
    check("注册成功", r.status_code == 200, f"status={r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        TOKEN = data.get("token", "")
        USER = data.get("user", {})
        AGENT = data.get("agent", {})
        
        check("返回 token", bool(TOKEN), f"token={TOKEN[:20]}...")
        check("返回用户信息", bool(USER), f"user_id={USER.get('id','')}")
        check("返回 Agent", bool(AGENT), f"agent_id={AGENT.get('id','')}")
        check("Agent 已创建", AGENT.get("status") == "created")
        return True
    
    # 如果已注册，尝试登录
    if "已注册" in r.text or "已存在" in r.text:
        print("  ⚠️ 用户已存在，尝试登录...")
        return test_03_login()
    
    print(f"  错误: {r.text}")
    return False


def test_03_login():
    """测试3: 邮箱登录"""
    print("\n🔑 测试3: 邮箱登录")
    global TOKEN, USER
    
    r = api("POST", "/api/login", {
        "email": "grantftd365@gmail.com",
        "password": "test123456",
    })
    
    check("登录成功", r.status_code == 200, f"status={r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        TOKEN = data.get("token", "")
        USER = data.get("user", {})
        
        check("返回 token", bool(TOKEN))
        check("用户信息完整", "nickname" in USER)
        check("关联 Agent", bool(USER.get("agent_id")), f"agent_id={USER.get('agent_id','')}")
        return True
    
    print(f"  错误: {r.text}")
    return False


def test_04_get_me():
    """测试4: 获取当前用户"""
    print("\n👤 测试4: 获取当前用户")
    
    r = api("GET", "/api/me", token=TOKEN)
    check("获取成功", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("邮箱正确", data.get("email") == "grantftd365@gmail.com")
        check("昵称正确", data.get("nickname") == "Grant")
        return True
    return False


def test_05_list_agents():
    """测试5: 列出 Agent"""
    print("\n🤖 测试5: 列出 Agent")
    
    r = api("GET", "/api/agents", token=TOKEN)
    check("获取成功", r.status_code == 200)
    
    if r.status_code == 200:
        agents = r.json()
        check("Agent 数量 > 0", len(agents) > 0, f"count={len(agents)}")
        
        # 找到自己的 Agent
        my_agent = None
        for a in agents:
            if a.get("id") == USER.get("agent_id"):
                my_agent = a
                break
        
        if my_agent:
            check("自己的 Agent 存在", True, f"name={my_agent.get('name')}")
            check("灵魂数据存在", bool(my_agent.get("soul_values")))
            check("身份数据存在", bool(my_agent.get("identity")))
        else:
            check("自己的 Agent 存在", False, "未找到")
        
        # 检查默认 Agent
        default_agents = [a for a in agents if a["id"].startswith("agent_d") or a["id"].startswith("agent_m") or a["id"].startswith("agent_g")]
        check("默认 Agent 存在", len(default_agents) >= 3, f"默认Agent: {[a['name'] for a in default_agents]}")
        
        return True
    return False


def test_06_groups():
    """测试6: 群组"""
    print("\n👥 测试6: 群组管理")
    
    # 列出群组
    r = api("GET", "/api/groups", token=TOKEN)
    check("获取群组成功", r.status_code == 200)
    
    if r.status_code == 200:
        groups = r.json()
        check("默认群存在", len(groups) > 0, f"群数: {len(groups)}")
        
        if groups:
            group_id = groups[0]["id"]
            check("群名称正确", "家庭" in groups[0].get("name", ""), f"name={groups[0].get('name')}")
            
            # 获取群成员
            r2 = api("GET", f"/api/groups/{group_id}/members", token=TOKEN)
            if r2.status_code == 200:
                members = r2.json()
                check("群成员 > 0", len(members) > 0, f"成员数: {len(members)}")
                
                agents_in_group = [m for m in members if m.get("is_agent")]
                humans_in_group = [m for m in members if not m.get("is_agent")]
                check("有真人成员", len(humans_in_group) > 0)
                check("有数字人成员", len(agents_in_group) > 0, f"数字人: {[m['name'] for m in agents_in_group]}")
            
            return group_id
    
    return None


def test_07_send_message(group_id):
    """测试7: 发送消息"""
    print("\n💬 测试7: 发送消息")
    
    if not group_id:
        check("群组ID有效", False, "无群组")
        return False
    
    r = api("POST", "/api/messages", {
        "group_id": group_id,
        "content": "大家好，我是Grant！今天天气真不错 ☀️",
        "msg_type": "text",
    }, token=TOKEN)
    
    check("消息发送成功", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("返回消息ID", bool(data.get("id")))
        return True
    return False


def test_08_get_messages(group_id):
    """测试8: 获取消息"""
    print("\n📜 测试8: 获取消息历史")
    
    r = api("GET", f"/api/messages/{group_id}", token=TOKEN)
    check("获取成功", r.status_code == 200)
    
    if r.status_code == 200:
        msgs = r.json()
        check("消息数量 > 0", len(msgs) > 0, f"消息数: {len(msgs)}")
        
        text_msgs = [m for m in msgs if m["msg_type"] == "text"]
        check("有文本消息", len(text_msgs) > 0)
        
        return True
    return False


def test_09_at_mention(group_id):
    """测试9: @提及测试"""
    print("\n📢 测试9: @提及测试")
    
    # @爸爸
    r = api("POST", "/api/messages", {
        "group_id": group_id,
        "content": "@爸爸 你今天去钓鱼了吗？",
        "msg_type": "text",
    }, token=TOKEN)
    
    check("@爸爸 消息发送", r.status_code == 200)
    
    # @所有人
    r2 = api("POST", "/api/messages", {
        "group_id": group_id,
        "content": "@所有人 明天家庭聚餐，记得来哦！",
        "msg_type": "text",
    }, token=TOKEN)
    
    check("@所有人 消息发送", r2.status_code == 200)
    
    return True


def test_10_emoji(group_id):
    """测试10: Emoji 消息"""
    print("\n😊 测试10: Emoji 消息")
    
    emojis = ["🎉🎊🥳", "❤️💕", "😂🤣", "👍👏"]
    
    for emoji in emojis:
        r = api("POST", "/api/messages", {
            "group_id": group_id,
            "content": emoji,
            "msg_type": "text",
        }, token=TOKEN)
        check(f"Emoji 发送: {emoji}", r.status_code == 200)
    
    return True


def test_11_image_upload():
    """测试11: 图片上传"""
    print("\n📷 测试11: 图片上传")
    
    # 创建一个测试图片 (1x1 pixel PNG)
    import struct
    import zlib
    
    def create_test_png():
        # 最小 PNG 文件
        signature = b'\x89PNG\r\n\x1a\n'
        
        def chunk(chunk_type, data):
            c = chunk_type + data
            crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            return struct.pack('>I', len(data)) + c + crc
        
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        ihdr = chunk(b'IHDR', ihdr_data)
        
        raw_data = b'\x00\xff\x00\x00'  # filter byte + RGB
        compressed = zlib.compress(raw_data)
        idat = chunk(b'IDAT', compressed)
        
        iend = chunk(b'IEND', b'')
        
        return signature + ihdr + idat + iend
    
    png_data = create_test_png()
    
    r = api("POST", "/api/upload/image", token=TOKEN, files={
        "file": ("test.png", png_data, "image/png"),
    })
    
    check("图片上传成功", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("返回图片URL", bool(data.get("url")), f"url={data.get('url')}")
        return data.get("url")
    return None


def test_12_send_image(group_id, image_url):
    """测试12: 发送图片消息"""
    print("\n🖼️ 测试12: 发送图片消息")
    
    if not image_url:
        check("图片URL有效", False, "无图片URL")
        return False
    
    r = api("POST", "/api/messages", {
        "group_id": group_id,
        "content": image_url,
        "msg_type": "image",
    }, token=TOKEN)
    
    check("图片消息发送成功", r.status_code == 200)
    return r.status_code == 200


def test_13_voice_upload():
    """测试13: 语音上传"""
    print("\n🎤 测试13: 语音上传")
    
    # 创建一个简单的测试音频 (空的 webm header)
    fake_audio = b'\x1a\x45\xdf\xa3' + b'\x00' * 100  # WebM signature + padding
    
    r = api("POST", "/api/voice/upload", token=TOKEN, files={
        "file": ("test_voice.webm", fake_audio, "audio/webm"),
    })
    
    check("语音上传成功", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("返回语音URL", bool(data.get("url")), f"url={data.get('url')}")
        return data.get("url")
    return None


def test_14_send_voice(group_id, voice_url):
    """测试14: 发送语音消息"""
    print("\n🔊 测试14: 发送语音消息")
    
    if not voice_url:
        check("语音URL有效", False, "无语音URL")
        return False
    
    r = api("POST", "/api/messages", {
        "group_id": group_id,
        "content": "[语音消息]",
        "msg_type": "voice",
        "voice_url": voice_url,
    }, token=TOKEN)
    
    check("语音消息发送成功", r.status_code == 200)
    return r.status_code == 200


def test_15_refine_text():
    """测试15: 文本炼化"""
    print("\n🧪 测试15: 文本炼化 (Agent 性格训练)")
    
    agent_id = USER.get("agent_id", "")
    if not agent_id:
        check("Agent ID 有效", False, "无 Agent ID")
        return False
    
    # 用文本炼化
    r = api("POST", "/api/agents/refine/text", {
        "agent_id": agent_id,
        "text": """我叫Grant，今年28岁，在北京做软件开发工作。
我平时喜欢打篮球、看电影、玩游戏。
说话比较直接，喜欢用网络用语。
性格开朗，喜欢交朋友。
口头禅：'好的没问题'、'这个可以有'、'绝了'""",
        "source": "text",
    }, token=TOKEN)
    
    check("文本炼化请求", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("炼化成功", data.get("status") == "ok")
        check("提取了特征", bool(data.get("traits") or data.get("raw")))
        return True
    
    print(f"  错误: {r.text[:200]}")
    return False


def test_16_refine_chat():
    """测试16: 聊天记录炼化"""
    print("\n💬 测试16: 聊天记录炼化")
    
    agent_id = USER.get("agent_id", "")
    
    r = api("POST", "/api/agents/refine/chat", {
        "agent_id": agent_id,
        "text": """昨天和朋友打篮球打到很晚，今天浑身酸痛
不过赢了比赛还是很开心的！
晚上准备看看电影放松一下
最近在追那部新的科幻片，特效真的绝了
周末打算去爬山，有没有人一起？
对了，昨天我妈打电话来让我回家吃饭
我说下周末回去，她就开始唠叨了😂
不过我知道她是关心我""",
        "source": "chat_history",
    }, token=TOKEN)
    
    check("聊天记录炼化", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("炼化成功", data.get("status") == "ok")
        extracted = data.get("extracted", {})
        check("提取兴趣", bool(extracted.get("interests")), f"interests={extracted.get('interests',[])}")
        check("提取口头禅", bool(extracted.get("catchphrases")), f"catchphrases={extracted.get('catchphrases',[])}")
        return True
    return False


def test_17_refine_voice():
    """测试17: 语音炼化"""
    print("\n🎙️ 测试17: 语音炼化")
    
    agent_id = USER.get("agent_id", "")
    
    r = api("POST", "/api/agents/refine/voice", {
        "agent_id": agent_id,
        "voice_url": "/api/voices/test_voice.webm",
        "description": "Grant的语音样本，语速中等，声音偏年轻",
    }, token=TOKEN)
    
    check("语音炼化", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("炼化成功", data.get("status") == "ok")
        return True
    return False


def test_18_llm_config():
    """测试18: LLM 配置"""
    print("\n⚙️ 测试18: LLM 配置管理")
    
    # 获取当前配置
    r = api("GET", "/api/config/llm", token=TOKEN)
    check("获取配置", r.status_code == 200)
    
    if r.status_code == 200:
        cfg = r.json()
        check("配置包含 provider", "provider" in cfg)
        check("API Key 已隐藏", "***" in cfg.get("api_key", ""))
    
    # 获取支持的提供商
    r2 = api("GET", "/api/config/providers")
    check("获取提供商列表", r2.status_code == 200)
    
    if r2.status_code == 200:
        providers = r2.json().get("providers", [])
        check("支持多个提供商", len(providers) >= 4, f"提供商: {[p['name'] for p in providers]}")
    
    return True


def test_19_memory_search():
    """测试19: 记忆搜索"""
    print("\n🧠 测试19: 记忆搜索")
    
    agent_id = USER.get("agent_id", "")
    
    r = api("GET", "/api/agents/agent_id/memories", {"q": "Grant", "agent_id": agent_id}, token=TOKEN)
    check("记忆搜索", r.status_code == 200)
    
    if r.status_code == 200:
        results = r.json()
        check("有搜索结果", len(results) > 0, f"结果数: {len(results)}")
        return True
    return False


def test_20_create_group():
    """测试20: 创建新群"""
    print("\n👥 测试20: 创建新群")
    
    r = api("POST", "/api/groups", {
        "name": "家庭小分队",
        "description": "核心家庭成员群",
    }, token=TOKEN)
    
    check("创建群成功", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("返回群ID", bool(data.get("id")))
        return data.get("id")
    return None


def test_21_create_agent():
    """测试21: 手动创建Agent"""
    print("\n🤖 测试21: 手动创建新 Agent")
    
    r = api("POST", "/api/agents", {
        "name": "爷爷",
        "avatar": "👴",
        "backstory": "退休军人，严肃但内心柔软，最疼孙子",
        "speaking_style": "说话简洁有力，偶尔用军事术语",
        "traits": ["严肃", "正直", "军人作风", "疼孙子"],
        "interests": ["太极拳", "看新闻", "下棋"],
        "catchphrases": ["立正！", "报告！", "收到！"],
    }, token=TOKEN)
    
    check("创建 Agent 成功", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("返回 Agent ID", bool(data.get("id")))
        check("名称正确", data.get("name") == "爷爷")
        return data.get("id")
    return None


def test_22_agent_memories():
    """测试22: Agent 记忆"""
    print("\n📚 测试22: Agent 记忆系统")
    
    agent_id = USER.get("agent_id", "")
    
    # 获取记忆
    r = api("GET", f"/api/agents/{agent_id}/memories", token=TOKEN)
    check("获取记忆", r.status_code == 200)
    
    if r.status_code == 200:
        memories = r.json()
        check("有记忆", len(memories) > 0, f"记忆数: {len(memories)}")
        
        # 检查记忆类型
        types = set(m.get("type") for m in memories)
        check("记忆类型多样", len(types) > 0, f"类型: {types}")
    
    return True


def test_23_voices():
    """测试23: 语音列表"""
    print("\n🔊 测试23: 语音列表")
    
    r = api("GET", "/api/voices")
    check("获取语音列表", r.status_code == 200)
    
    if r.status_code == 200:
        voices = r.json().get("voices", [])
        check("有可用语音", len(voices) > 0, f"语音数: {len(voices)}")
        return True
    return False


def test_24_create_user_agent():
    """测试24: 模拟另一个家庭成员注册"""
    print("\n👨 测试24: 模拟爸爸注册")
    
    r = api("POST", "/api/register", {
        "email": "dad@example.com",
        "username": "dad",
        "password": "test123456",
        "nickname": "爸爸",
        "avatar": "👨",
        "role_in_family": "爸爸",
    })
    
    check("爸爸注册成功", r.status_code == 200)
    
    if r.status_code == 200:
        data = r.json()
        check("自动创建 Agent", bool(data.get("agent")))
        check("Agent ID 正确", "agent_" in data.get("agent", {}).get("id", ""))
        return True
    
    if "已注册" in r.text or "已存在" in r.text:
        check("爸爸已存在", True, "之前已注册")
        return True
    
    return False


# ==================== 主测试流程 ====================

def main():
    print("=" * 60)
    print("🏠 FamilyChat 端到端集成测试")
    print("=" * 60)
    
    passed = 0
    failed = 0
    total = 0
    
    def run_test(name, func, *args):
        nonlocal passed, failed, total
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
    
    # 1. 健康检查
    if not run_test("健康检查", test_01_health):
        print("\n❌ 服务未启动！请先运行: python run.py")
        sys.exit(1)
    
    # 2. 注册
    run_test("邮箱注册", test_02_register)
    
    # 3. 登录（如果注册失败）
    if not TOKEN:
        run_test("邮箱登录", test_03_login)
    
    # 4. 获取用户信息
    run_test("获取用户", test_04_get_me)
    
    # 5. Agent 列表
    run_test("Agent列表", test_05_list_agents)
    
    # 6. 群组
    group_id = run_test("群组管理", test_06_groups)
    
    # 7. 发消息
    if group_id:
        run_test("发送消息", test_07_send_message, group_id)
    
    # 8. 获取消息
    if group_id:
        run_test("获取消息", test_08_get_messages, group_id)
    
    # 9. @提及
    if group_id:
        run_test("@提及", test_09_at_mention, group_id)
    
    # 10. Emoji
    if group_id:
        run_test("Emoji", test_10_emoji, group_id)
    
    # 11. 图片上传
    image_url = run_test("图片上传", test_11_image_upload)
    
    # 12. 发送图片
    if group_id and image_url:
        run_test("发送图片", test_12_send_image, group_id, image_url)
    
    # 13. 语音上传
    voice_url = run_test("语音上传", test_13_voice_upload)
    
    # 14. 发送语音
    if group_id and voice_url:
        run_test("发送语音", test_14_send_voice, group_id, voice_url)
    
    # 15. 文本炼化
    run_test("文本炼化", test_15_refine_text)
    
    # 16. 聊天记录炼化
    run_test("聊天炼化", test_16_refine_chat)
    
    # 17. 语音炼化
    run_test("语音炼化", test_17_refine_voice)
    
    # 18. LLM 配置
    run_test("LLM配置", test_18_llm_config)
    
    # 19. 记忆搜索
    run_test("记忆搜索", test_19_memory_search)
    
    # 20. 创建新群
    run_test("创建新群", test_20_create_group)
    
    # 21. 创建新 Agent
    run_test("创建Agent", test_21_create_agent)
    
    # 22. Agent 记忆
    run_test("Agent记忆", test_22_agent_memories)
    
    # 23. 语音列表
    run_test("语音列表", test_23_voices)
    
    # 24. 模拟家庭成员
    run_test("家庭成员注册", test_24_create_user_agent)
    
    # ==================== 结果 ====================
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过 | {failed} 失败")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 全部测试通过！")
    else:
        print(f"⚠️ 有 {failed} 个测试失败，请检查日志")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
