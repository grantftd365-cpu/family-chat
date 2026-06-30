"""Agent 路由 - 数字人管理/炼化"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from ..core.auth import get_current_user
from ..models.database import get_db, gen_id, now

router = APIRouter(prefix="/api/agents")


class CreateAgentReq(BaseModel):
    name: str
    avatar: str = "🤖"
    backstory: str = ""
    speaking_style: str = ""
    traits: list = []
    interests: list = []
    catchphrases: list = []
    relationships: dict = {}
    humor_style: str = ""


class UpdateAgentReq(BaseModel):
    name: str = ""
    avatar: str = ""
    backstory: str = ""
    speaking_style: str = ""
    traits: list = []
    interests: list = []
    catchphrases: list = []


class RefineTextReq(BaseModel):
    agent_id: str
    text: str
    source: str = "text"


class RefineVoiceReq(BaseModel):
    agent_id: str
    voice_url: str
    description: str = ""


@router.get("")
async def list_agents(user=Depends(get_current_user)):
    from ..main import agent_manager
    return agent_manager.get_all()


@router.get("/{agent_id}")
async def get_agent(agent_id: str, user=Depends(get_current_user)):
    from ..main import agent_manager
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    return {
        "id": agent.agent_id, "name": agent.name,
        "avatar": agent.personality.avatar,
        "backstory": agent.personality.backstory,
        "speaking_style": agent.personality.speaking_style,
        "traits": agent.personality.traits,
        "interests": agent.personality.interests,
        "catchphrases": agent.personality.catchphrases,
        "humor_style": agent.personality.humor_style,
        "emotion": agent.emotion.current,
        "soul": agent.soul.to_dict(),
        "identity": agent.identity.to_dict(),
    }


@router.post("")
async def create_agent(req: CreateAgentReq, user=Depends(get_current_user)):
    from ..main import agent_manager
    db = await get_db()
    try:
        agent_id = await agent_manager.create_agent(req.dict())
        await db.execute(
            "INSERT OR IGNORE INTO group_members (group_id,user_id,role,joined_at) VALUES (?,?,?,?)",
            ("family_default", agent_id, "agent", now())
        )
        await db.commit()
        return {"id": agent_id, "name": req.name}
    finally:
        await db.close()


@router.put("/{agent_id}")
async def update_agent(agent_id: str, req: UpdateAgentReq, user=Depends(get_current_user)):
    from ..main import agent_manager
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(404)

    p = agent.personality
    if req.name:
        agent.name = req.name
        p.name = req.name
    if req.avatar:
        p.avatar = req.avatar
    if req.backstory:
        p.backstory = req.backstory
    if req.speaking_style:
        p.speaking_style = req.speaking_style
    if req.traits:
        p.traits = req.traits
    if req.interests:
        p.interests = req.interests
    if req.catchphrases:
        p.catchphrases = req.catchphrases

    db = await get_db()
    await db.execute(
        "UPDATE agents SET name=?,avatar=?,backstory=?,speaking_style=?,traits=?,interests=?,catchphrases=?,updated_at=? WHERE id=?",
        (p.name, p.avatar, p.backstory, p.speaking_style,
         json.dumps(p.traits, ensure_ascii=False),
         json.dumps(p.interests, ensure_ascii=False),
         json.dumps(p.catchphrases, ensure_ascii=False),
         now(), agent_id)
    )
    await db.commit()
    await db.close()
    return {"status": "ok"}


@router.get("/{agent_id}/memories")
async def agent_memories(agent_id: str, user=Depends(get_current_user)):
    db = await get_db()
    try:
        memories = []
        async with db.execute(
            "SELECT id,content,importance,memory_type,category,created_at FROM agent_memories WHERE agent_id=? ORDER BY created_at DESC LIMIT 50",
            (agent_id,)
        ) as cursor:
            async for row in cursor:
                memories.append({
                    "id": row[0], "content": row[1], "importance": row[2],
                    "type": row[3], "category": row[4], "created_at": row[5],
                })
        return memories
    finally:
        await db.close()


# ==================== 炼化系统 ====================

@router.post("/refine/text")
async def refine_text(req: RefineTextReq, user=Depends(get_current_user)):
    from ..main import agent_manager
    agent = agent_manager.get_agent(req.agent_id)
    if not agent:
        raise HTTPException(404)

    prompt = f"""分析以下文本，提取说话人的性格特征、说话风格、兴趣爱好、口头禅。

文本来源: {req.source}
文本内容:
{req.text}

请以 JSON 格式输出：
{{
  "traits": ["性格特征1", "性格特征2"],
  "speaking_style": "说话风格描述",
  "interests": ["兴趣1", "兴趣2"],
  "catchphrases": ["口头禅1", "口头禅2"],
  "backstory_update": "根据文本推断的背景信息",
  "personality_summary": "性格总结"
}}"""

    try:
        result = await agent._call_llm(
            "你是一个专业的性格分析专家，从文本中提取人物特征。只输出JSON，不要其他内容。",
            prompt
        )
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]

        traits_data = json.loads(clean)
        p = agent.personality
        if traits_data.get("traits"):
            p.traits = list(set(p.traits + traits_data["traits"]))
        if traits_data.get("speaking_style"):
            p.speaking_style = traits_data["speaking_style"]
        if traits_data.get("interests"):
            p.interests = list(set(p.interests + traits_data["interests"]))
        if traits_data.get("catchphrases"):
            p.catchphrases = list(set(p.catchphrases + traits_data["catchphrases"]))
        if traits_data.get("backstory_update"):
            p.backstory += "\n" + traits_data["backstory_update"]

        await agent.memory.add_long_term(
            f"[炼化-文本] 来源: {req.source}\n{req.text[:500]}",
            importance=0.9, metadata={"type": "refinement", "source": "text"}
        )

        db = await get_db()
        await db.execute(
            "UPDATE agents SET traits=?,speaking_style=?,interests=?,catchphrases=?,backstory=?,refinement_count=refinement_count+1,updated_at=? WHERE id=?",
            (json.dumps(p.traits, ensure_ascii=False), p.speaking_style,
             json.dumps(p.interests, ensure_ascii=False),
             json.dumps(p.catchphrases, ensure_ascii=False),
             p.backstory, now(), req.agent_id)
        )
        await db.commit()
        await db.close()

        return {"status": "ok", "message": f"炼化完成！提取了 {len(traits_data.get('traits', []))} 个特征", "traits": traits_data}

    except json.JSONDecodeError:
        await agent.memory.add_long_term(f"[炼化分析] {result[:1000]}", importance=0.8)
        return {"status": "ok", "message": "数据已记录", "raw": result[:500]}
    except ValueError as e:
        # LLM not configured — do basic keyword extraction
        traits_data = {"traits": [], "speaking_style": "", "interests": [], "catchphrases": []}
        happy_words = ["开心", "高兴", "乐观", "开朗", "爱笑", "活泼"]
        kind_words = ["善良", "温柔", "体贴", "关心", "真诚"]
        for w in happy_words:
            if w in req.text: traits_data["traits"].append(w)
        for w in kind_words:
            if w in req.text: traits_data["traits"].append(w)
        if not traits_data["traits"]:
            traits_data["traits"] = ["善于表达"]
        p = agent.personality
        p.traits = list(set(p.traits + traits_data["traits"]))
        db = await get_db()
        await db.execute(
            "UPDATE agents SET traits=?,refinement_count=refinement_count+1,updated_at=? WHERE id=?",
            (json.dumps(p.traits, ensure_ascii=False), now(), req.agent_id)
        )
        await db.commit()
        await db.close()
        return {"status": "ok", "message": f"炼化完成（关键词模式）", "traits": traits_data, "note": "LLM未配置"}
    except Exception as e:
        logger.error(f"炼化失败: {e}")
        raise HTTPException(500, f"炼化失败: {e}")


@router.post("/refine/chat")
async def refine_chat(req: RefineTextReq, user=Depends(get_current_user)):
    from ..main import agent_manager
    agent = agent_manager.get_agent(req.agent_id)
    if not agent:
        raise HTTPException(404)

    text = req.text
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    all_traits, all_styles, all_interests, all_catchphrases = [], [], [], []

    for chunk in chunks[:5]:
        try:
            result = await agent._call_llm(
                "分析聊天记录，提取性格和风格。JSON: {traits:[], style:'', interests:[], catchphrases:[]}",
                chunk
            )
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(clean)
            all_traits.extend(data.get("traits", []))
            if data.get("style"):
                all_styles.append(data["style"])
            all_interests.extend(data.get("interests", []))
            all_catchphrases.extend(data.get("catchphrases", []))
        except:
            continue

    p = agent.personality
    if all_traits:
        p.traits = list(set(p.traits + all_traits))
    if all_styles:
        p.speaking_style = " ".join(set([p.speaking_style] + all_styles))
    if all_interests:
        p.interests = list(set(p.interests + all_interests))
    if all_catchphrases:
        p.catchphrases = list(set(p.catchphrases + all_catchphrases))

    db = await get_db()
    await db.execute(
        "UPDATE agents SET traits=?,speaking_style=?,interests=?,catchphrases=?,refinement_count=refinement_count+1,updated_at=? WHERE id=?",
        (json.dumps(p.traits, ensure_ascii=False), p.speaking_style,
         json.dumps(p.interests, ensure_ascii=False),
         json.dumps(p.catchphrases, ensure_ascii=False), now(), req.agent_id)
    )
    await db.commit()
    await db.close()

    return {"status": "ok", "message": f"分析了 {len(chunks)} 段", "extracted": {"traits": all_traits, "interests": all_interests, "catchphrases": all_catchphrases}}
