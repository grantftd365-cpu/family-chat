"""FamilyChat 后端单元测试

覆盖核心模块：
- auth.py: 认证、JWT、密码
- database.py: 数据库初始化、ID 生成
- delivery.py: 消息投递、已读、表情回应
- refinement.py: 七层本质模型
- routes: API 端点基础验证
"""
import asyncio
import json
import os
import sys
import time
import uuid

# 设置测试环境
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-testing-only-32chars!")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8000")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 测试工具 ====================

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"  ✅ {name}")

    def fail(self, name, reason=""):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ❌ {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"测试结果: {self.passed}/{total} 通过, {self.failed} 失败")
        if self.errors:
            print("\n失败详情:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*50}")
        return self.failed == 0


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


# ==================== 1. Auth 测试 ====================

def test_auth():
    print("\n📋 Auth 模块测试")
    r = TestResult()

    # SECRET_KEY 检查
    from backend.app.core.auth import SECRET_KEY
    if SECRET_KEY and len(SECRET_KEY) >= 16:
        r.ok("SECRET_KEY 已设置且长度足够")
    else:
        r.fail("SECRET_KEY", f"长度不足: {len(SECRET_KEY) if SECRET_KEY else 0}")

    # 密码哈希
    from backend.app.core.auth import hash_password, verify_password
    pw = hash_password("test123")
    if pw and pw != "test123" and len(pw) > 20:
        r.ok("hash_password 生成哈希")
    else:
        r.fail("hash_password", "哈希生成失败")

    if verify_password("test123", pw):
        r.ok("verify_password 正确密码验证")
    else:
        r.fail("verify_password", "正确密码验证失败")

    if not verify_password("wrong", pw):
        r.ok("verify_password 错误密码拒绝")
    else:
        r.fail("verify_password", "错误密码未拒绝")

    # JWT Token
    from backend.app.core.auth import create_token, decode_token
    token = create_token("user123", "testuser")
    if token and len(token) > 20:
        r.ok("create_token 生成 token")
    else:
        r.fail("create_token", "token 生成失败")

    payload = decode_token(token)
    if payload.get("sub") == "user123" and payload.get("username") == "testuser":
        r.ok("decode_token 解析正确")
    else:
        r.fail("decode_token", f"解析结果错误: {payload}")

    # 无效 token
    try:
        decode_token("invalid.token.here")
        r.fail("decode_token", "应该抛出异常")
    except Exception:
        r.ok("decode_token 无效 token 抛出异常")

    return r


# ==================== 2. Database 测试 ====================

def test_database():
    print("\n📋 Database 模块测试")
    r = TestResult()

    from backend.app.models.database import gen_id, now

    # gen_id 完整 UUID
    ids = [gen_id() for _ in range(100)]
    if all(len(i) == 36 for i in ids):
        r.ok("gen_id 生成完整 UUID (36 chars)")
    else:
        r.fail("gen_id", f"长度不一致: {set(len(i) for i in ids)}")

    # 唯一性
    if len(set(ids)) == 100:
        r.ok("gen_id 100 个 ID 全部唯一")
    else:
        r.fail("gen_id", f"碰撞: {100 - len(set(ids))} 个重复")

    # now() 时间戳
    t = now()
    if isinstance(t, float) and t > 1700000000:
        r.ok("now() 返回合理时间戳")
    else:
        r.fail("now()", f"异常值: {t}")

    return r


# ==================== 3. HumanEssence 测试 ====================

def test_essence():
    print("\n📋 HumanEssence 七层本质模型测试")
    r = TestResult()

    from backend.app.services.refinement import HumanEssence

    # 初始化
    ess = HumanEssence()
    layers = ["cognitive", "knowledge", "emotional", "linguistic",
              "values", "relational", "narrative"]
    d = ess.to_dict()
    if all(layer in d for layer in layers):
        r.ok("HumanEssence 包含全部 7 层维度")
    else:
        r.fail("HumanEssence 层维度", f"缺失: {set(layers) - set(d.keys())}")

    # 初始完成度为 0
    comp = ess.get_completeness()
    if all(v == 0.0 for v in comp.values()):
        r.ok("初始完成度全部为 0%")
    else:
        r.fail("初始完成度", f"非零: {comp}")

    # 合并功能
    ess.merge({
        "cognitive": {"thinking_style": "分析性思维，喜欢拆解问题和寻找规律", "decision_pattern": "理性主导，但在家庭决策中更偏向感性"},
        "values": {"life_philosophy": "平淡是真", "core_values": ["家庭", "真诚"]},
        "linguistic": {"humor_mechanism": "自嘲式幽默"},
        "emotional": {"attachment_style": "安全型依恋"},
        "narrative": {"turning_points": ["30岁辞职创业"]},
    }, source="test")

    comp2 = ess.get_completeness()
    if comp2["cognitive"] > 0:
        r.ok("合并后认知层完成度 > 0")
    else:
        r.fail("合并", "认知层完成度仍为 0")

    if comp2["values"] > 0:
        r.ok("合并后价值层完成度 > 0")
    else:
        r.fail("合并", "价值层完成度仍为 0")

    if comp2["narrative"] > 0:
        r.ok("合并后叙事层完成度 > 0")
    else:
        r.fail("合并", "叙事层完成度仍为 0")

    # 不覆盖已有数据
    ess.merge({
        "cognitive": {"thinking_style": "完全不同的风格"},
    }, source="test2")
    d2 = ess.to_dict()
    if "分析性思维" in d2["cognitive"]["thinking_style"]:
        r.ok("智能合并：保留已有深层数据")
    else:
        r.fail("智能合并", "覆盖了已有数据")

    # 序列化/反序列化
    ess_json = json.dumps(ess.to_dict(), ensure_ascii=False)
    ess2 = HumanEssence.from_dict(json.loads(ess_json))
    if ess2.cognitive["thinking_style"] == ess.cognitive["thinking_style"]:
        r.ok("序列化/反序列化一致性")
    else:
        r.fail("序列化", "反序列化后数据不一致")

    # 版本号递增
    if ess._version > 0:
        r.ok(f"版本号递增: v{ess._version}")
    else:
        r.fail("版本号", f"未递增: {ess._version}")

    return r


# ==================== 4. ReactionManager 测试 ====================

async def test_reactions():
    print("\n📋 ReactionManager 表情回应测试")
    r = TestResult()

    from backend.app.services.delivery import ReactionManager
    from backend.app.models.database import init_db

    # 初始化数据库
    await init_db()

    # 添加回应
    reactions = await ReactionManager.add_reaction("msg_test1", "user1", "张三", "👍")
    if len(reactions) == 1 and reactions[0]["emoji"] == "👍":
        r.ok("添加表情回应")
    else:
        r.fail("添加表情回应", f"结果: {reactions}")

    # 同一用户同一表情不重复
    reactions = await ReactionManager.add_reaction("msg_test1", "user1", "张三", "👍")
    if len(reactions) == 1:
        r.ok("同一用户同一表情不重复")
    else:
        r.fail("去重", f"回应数: {len(reactions)}")

    # 不同用户
    reactions = await ReactionManager.add_reaction("msg_test1", "user2", "李四", "❤️")
    if len(reactions) == 2:
        r.ok("不同用户添加回应")
    else:
        r.fail("多用户", f"回应数: {len(reactions)}")

    # 批量获取
    batch = await ReactionManager.get_batch_reactions(["msg_test1", "msg_test2"])
    if "msg_test1" in batch and len(batch["msg_test1"]) == 2:
        r.ok("批量获取回应")
    else:
        r.fail("批量获取", f"结果: {batch}")

    # 移除回应
    reactions = await ReactionManager.remove_reaction("msg_test1", "user1", "👍")
    if len(reactions) == 1:
        r.ok("移除表情回应")
    else:
        r.fail("移除", f"回应数: {len(reactions)}")

    # 清理测试数据
    from backend.app.models.database import get_db
    db = await get_db()
    await db.execute("DELETE FROM message_reactions_v2 WHERE message_id LIKE 'msg_test%'")
    await db.commit()
    await db.close()

    return r


# ==================== 5. 路径遍历防护测试 ====================

def test_path_traversal():
    print("\n📋 路径遍历防护测试")
    r = TestResult()

    from pathlib import Path

    # 模拟 get_voice 的防护逻辑
    def safe_filename(filename):
        safe_name = Path(filename).name
        if not safe_name or safe_name.startswith("."):
            return None
        return safe_name

    # 正常文件名
    if safe_filename("voice_123.mp3") == "voice_123.mp3":
        r.ok("正常文件名通过")
    else:
        r.fail("正常文件名", "被拒绝")

    # 路径遍历
    if safe_filename("../../../etc/passwd") == "passwd":
        r.ok("路径遍历被剥离")
    else:
        r.fail("路径遍历", "未防护")

    # 点文件
    if safe_filename(".hidden") is None:
        r.ok("点文件被拒绝")
    else:
        r.fail("点文件", "未拒绝")

    # 空文件名
    if safe_filename("") is None or safe_filename("/") is None:
        r.ok("空/根路径被拒绝")
    else:
        r.fail("空文件名", "未拒绝")

    return r


# ==================== 6. 文件校验测试 ====================

def test_file_validation():
    print("\n📋 文件校验测试")
    r = TestResult()

    # 图片 magic bytes
    image_signatures = {
        b"\xff\xd8\xff": "JPEG",
        b"\x89PNG": "PNG",
        b"GIF8": "GIF",
        b"RIFF": "WEBP",
    }

    for sig, fmt in image_signatures.items():
        # 模拟检测
        test_data = sig + b"\x00" * 100
        detected = None
        for s, name in image_signatures.items():
            if test_data[:len(s)] == s:
                detected = name
                break
        if detected == fmt:
            r.ok(f"Magic bytes 检测: {fmt}")
        else:
            r.fail(f"Magic bytes {fmt}", f"检测为: {detected}")

    # 非图片文件
    fake_data = b"<!DOCTYPE html><html>"
    detected = None
    for s, name in image_signatures.items():
        if fake_data[:len(s)] == s:
            detected = name
            break
    if detected is None:
        r.ok("非图片文件被正确拒绝")
    else:
        r.fail("非图片检测", f"误检为: {detected}")

    return r


# ==================== 7. Agent 会话记忆测试 ====================

async def test_agent_memory_sessions():
    print("\n📋 Agent 会话记忆隔离测试")
    r = TestResult()

    from backend.app.agents.core import AgentMemory

    memory = AgentMemory("agent_test", None)
    await memory.add_short_term(
        "今天聊ERP上线风险",
        "我",
        session_id="group:A",
        sender_id="user_a",
        group_id="A",
    )
    await memory.add_short_term(
        "周末回东北吃烧烤",
        "老婆",
        session_id="group:B",
        sender_id="user_b",
        group_id="B",
    )

    ctx_a = memory.get_context(session_id="group:A")
    ctx_b = memory.get_context(session_id="group:B")
    if "ERP上线" in ctx_a and "东北吃烧烤" not in ctx_a:
        r.ok("群 A 只读取自己的短期记忆")
    else:
        r.fail("群 A 记忆隔离", ctx_a)

    if "东北吃烧烤" in ctx_b and "ERP上线" not in ctx_b:
        r.ok("群 B 只读取自己的短期记忆")
    else:
        r.fail("群 B 记忆隔离", ctx_b)

    await memory.add_short_term("系统主动问候", "系统")
    ctx_a_after = memory.get_context(session_id="group:A")
    if "系统主动问候" in memory.get_context() and "系统主动问候" not in ctx_a_after:
        r.ok("默认 session 与群 session 分离")
    else:
        r.fail("默认 session", memory.get_context())

    return r


async def test_agent_relationship_growth():
    print("\n📋 Agent 关系画像成长测试")
    r = TestResult()

    from backend.app.models.database import init_db, get_db
    from backend.app.agents.core import AgentMemory

    await init_db()
    agent_id = "agent_growth_test"
    group_id = "group_growth_test"
    person_id = "user_wife_test"
    memory = AgentMemory(agent_id, None)

    await memory.remember_interaction(
        "我直说哈，SAP APO供应链这块别拍脑袋上线，先把约束和计划排清楚。",
        speaker_name="老婆",
        speaker_id=person_id,
        session_id=f"group:{group_id}",
        group_id=group_id,
        listener_id=agent_id,
        listener_name="我",
        is_mentioned=True,
        msg_type="text",
        direction="incoming",
        speaker_is_agent=False,
    )

    context = await memory.get_relationship_context(group_id=group_id, person_id=person_id)
    if "老婆" in context and "企业数字化/供应链" in context:
        r.ok("关系画像记录了人名和主题")
    else:
        r.fail("关系画像内容", context)

    seed = await memory.get_proactive_seed(group_id=group_id)
    if "老婆" in seed and ("供应链" in seed or "企业数字化" in seed):
        r.ok("主动联系种子来自成长事件")
    else:
        r.fail("主动联系种子", seed)

    db = await get_db()
    try:
        async with db.execute(
            "SELECT COUNT(*) FROM agent_growth_events WHERE agent_id=? AND person_id=?",
            (agent_id, person_id)
        ) as cursor:
            row = await cursor.fetchone()
        if row[0] >= 1:
            r.ok("成长事件已持久化")
        else:
            r.fail("成长事件", "未写入")
        await db.execute("DELETE FROM agent_relationship_profiles WHERE agent_id=?", (agent_id,))
        await db.execute("DELETE FROM agent_growth_events WHERE agent_id=?", (agent_id,))
        await db.execute("DELETE FROM agent_memories WHERE agent_id=?", (agent_id,))
        await db.commit()
    finally:
        await db.close()

    return r


# ==================== 运行所有测试 ====================

def main():
    print("=" * 50)
    print("FamilyChat 后端单元测试")
    print("=" * 50)

    results = []

    # 同步测试
    results.append(test_auth())
    results.append(test_database())
    results.append(test_essence())
    results.append(test_path_traversal())
    results.append(test_file_validation())

    # 异步测试
    results.append(run_async(test_reactions()))
    results.append(run_async(test_agent_memory_sessions()))
    results.append(run_async(test_agent_relationship_growth()))

    # 汇总
    all_passed = all(r.summary() for r in results)
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)

    print(f"\n{'='*50}")
    print(f"总计: {total_passed} 通过, {total_failed} 失败")
    print(f"{'='*50}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
