"""FamilyChat E2E Test Suite"""
import requests, json, sys, os, time

BASE = "http://localhost:8000"
errors = []
passed = 0
total = 0

def test(name, method, path, data=None, token=None, expect_status=200, files=None):
    global passed, errors, total
    total += 1
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        url = f"{BASE}{path}"
        kwargs = {"headers": headers, "timeout": 15}
        if files:
            kwargs["files"] = files
            if data:
                kwargs["data"] = data
        elif method in ("POST", "PUT"):
            kwargs["json"] = data
        r = getattr(requests, method.lower().replace("delete","delete"), requests.get)(url, **kwargs)
        if isinstance(expect_status, list):
            if r.status_code not in expect_status:
                errors.append(f"  ❌ {name}: HTTP {r.status_code} (expected {expect_status}) - {r.text[:200]}")
                return None
        elif r.status_code != expect_status:
            errors.append(f"  ❌ {name}: HTTP {r.status_code} (expected {expect_status}) - {r.text[:200]}")
            return None
        result = r.json() if "json" in r.headers.get("content-type","") else {}
        passed += 1
        print(f"  ✅ {name}")
        return result
    except Exception as e:
        errors.append(f"  ❌ {name}: {e}")
        return None

# ==================== TESTS ====================

print("\n" + "="*60)
print("🏥 FamilyChat E2E Test Suite")
print("="*60)

# 1. AUTH
print("\n🔐 [Auth]")
r = test("Register", "POST", "/api/register",
    {"email":"e2e@family.com","password":"pass123","nickname":"测试用户","username":"e2e"})
TOKEN = r.get("token","") if r else ""
USER_ID = r.get("user",{}).get("id","") if r else ""

test("Login", "POST", "/api/login", {"email":"e2e@family.com","password":"pass123"})
test("Login wrong password", "POST", "/api/login", {"email":"e2e@family.com","password":"wrong"}, expect_status=401)
test("Get profile", "GET", "/api/me", token=TOKEN)
test("Update profile", "PUT", "/api/me", {"nickname":"E2E测试","signature":"自动化测试"}, token=TOKEN)

# 2. GROUPS
print("\n💬 [Groups]")
r = test("Create group", "POST", "/api/groups", {"name":"测试家庭群","description":"E2E"}, token=TOKEN)
GROUP_ID = r.get("id","") if r else ""
test("List groups", "GET", "/api/groups", token=TOKEN)
test("Get members", "GET", f"/api/groups/{GROUP_ID}/members", token=TOKEN)

# 3. MESSAGES
print("\n📨 [Messages]")
r = test("Send text msg", "POST", "/api/messages",
    {"group_id":GROUP_ID,"content":"Hello FamilyChat!","msg_type":"text"}, token=TOKEN)
MSG_ID = r.get("id","") if r else ""
test("Get messages", "GET", f"/api/messages/{GROUP_ID}?limit=50", token=TOKEN)
test("Send reply", "POST", "/api/messages",
    {"group_id":GROUP_ID,"content":"Reply!","msg_type":"text","reply_to":MSG_ID}, token=TOKEN)
test("React to msg", "POST", f"/api/messages/{MSG_ID}/reactions", {"emoji":"👍"}, token=TOKEN)

# 4. AGENTS
print("\n🤖 [Agents]")
test("List agents", "GET", "/api/agents", token=TOKEN)
r = test("Create agent", "POST", "/api/agents",
    {"name":"测试AI","avatar":"🧑","backstory":"测试数字人","speaking_style":"友好",
     "traits":["聪明"],"interests":["聊天"],"role_in_family":"测试"}, token=TOKEN)
AGENT_ID = r.get("id","") if r else ""
test("Get agent detail", "GET", f"/api/agents/{AGENT_ID}", token=TOKEN, expect_status=[200,404])

# 5. REFINEMENT
print("\n🧪 [Refinement]")
test("Refine from text", "POST", "/api/agents/refine/text",
    {"agent_id":AGENT_ID,"text":"我性格开朗爱笑","source":"text"}, token=TOKEN)

# 6. VOICE PROFILES
print("\n🎤 [Voice Profiles]")
test("List profiles", "GET", "/api/voice-profiles", token=TOKEN)
r = test("Create profile", "POST", "/api/voice-profiles",
    {"name":"测试音色","edge_voice_id":"zh-CN-XiaoxiaoNeural"}, token=TOKEN)
VP_ID = r.get("id","") if r else ""
test("List available", "GET", "/api/voice-profiles/available", token=TOKEN)
test("Assign to agent", "POST", "/api/voice-profiles/assign",
    {"agent_id":AGENT_ID,"profile_id":VP_ID}, token=TOKEN)
test("Get agent voice", "GET", f"/api/voice-profiles/agent/{AGENT_ID}", token=TOKEN)

# 7. FRIENDS
print("\n👥 [Friends]")
test("List friends", "GET", "/api/friends", token=TOKEN)
test("Friend requests", "GET", "/api/friends/requests", token=TOKEN)

# 8. FAVORITES
print("\n⭐ [Favorites]")
test("Add favorite", "POST", "/api/favorites",
    {"message_id":MSG_ID,"content":"Hello!","msg_type":"text","source_name":"测试"}, token=TOKEN)
test("List favorites", "GET", "/api/favorites", token=TOKEN)

# 9. MOMENTS
print("\n📷 [Moments]")
test("Publish moment", "POST", "/api/moments", {"content":"E2E测试动态🎉","images":[]}, token=TOKEN)
test("List moments", "GET", "/api/moments", token=TOKEN)

# 10. SEARCH
print("\n🔍 [Search]")
test("Search all", "GET", "/api/search?q=E2E", token=TOKEN)

# 11. SYSTEM
print("\n📊 [System]")
test("System stats", "GET", "/api/system/stats", token=TOKEN)
test("Create backup", "POST", "/api/system/backup", token=TOKEN)

# 12. LLM CONFIG
print("\n🤖 [LLM Config]")
test("Save config", "POST", "/api/config/llm",
    {"provider":"deepseek","api_key":"test","model":"deepseek-chat"}, token=TOKEN)

# 13. NOTIFICATIONS
print("\n🔔 [Notifications]")
test("List notifications", "GET", "/api/notifications", token=TOKEN)

# 14. CLEANUP
print("\n🗑️ [Cleanup]")
test("Delete voice profile", "DELETE", f"/api/voice-profiles/{VP_ID}", token=TOKEN)

# 15. FRONTEND
print("\n🌐 [Frontend]")
r = requests.get("http://localhost:8000/", timeout=5)
if r.status_code == 200 and "FamilyChat" in r.text:
    passed += 1; total += 1
    print("  ✅ Frontend loads")
else:
    total += 1
    errors.append(f"  ❌ Frontend: HTTP {r.status_code}")

# ==================== RESULTS ====================
print(f"\n{'='*60}")
print(f"📊 Results: {passed}/{total} passed, {len(errors)} failed")
if errors:
    print(f"\n❌ Failures:")
    for e in errors:
        print(e)
else:
    print("🎉 All tests passed!")
print(f"{'='*60}")
sys.exit(0 if not errors else 1)
