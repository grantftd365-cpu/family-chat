"""炼化 API — "人AI合一" 七层维度炼化接口"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from ..core.auth import get_current_user

router = APIRouter(prefix="/api/agents/refine")


def _get_refinement():
    from ..main import refinement_service
    if not refinement_service:
        raise HTTPException(500, "炼化服务未初始化")
    return refinement_service


# ==================== 请求模型 ====================

class TextRefineReq(BaseModel):
    agent_id: str
    text: str
    source: str = "text"


class ChatHistoryRefineReq(BaseModel):
    agent_id: str
    messages: list[dict]
    group_id: str = ""


class SelfDescriptionReq(BaseModel):
    agent_id: str
    answers: dict  # {"我是谁": "...", "我最看重什么": "...", ...}


# ==================== 炼化接口 ====================

@router.post("/text")
async def refine_from_text(req: TextRefineReq, user=Depends(get_current_user)):
    """从文本炼化 — 提取七层维度"""
    svc = _get_refinement()
    try:
        result = await svc.refine_from_text(req.agent_id, req.text, req.source)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"炼化失败: {e}")


@router.post("/voice")
async def refine_from_voice(
    agent_id: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """从语音炼化 — 音色 + 语言习惯 + 情感模式"""
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(400, "请上传音频文件")

    import uuid, os
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "mp3"
    temp_path = f"data/refinement_uploads/voice_{uuid.uuid4().hex[:8]}.{ext}"
    os.makedirs("data/refinement_uploads", exist_ok=True)

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(400, "音频文件不能超过 100MB")

    with open(temp_path, "wb") as f:
        f.write(content)

    svc = _get_refinement()
    try:
        result = await svc.refine_from_voice(agent_id, temp_path)
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/video")
async def refine_from_video(
    agent_id: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """从视频炼化 — 视觉 + 音频 + 语言"""
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(400, "请上传视频文件")

    import uuid, os
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "mp4"
    temp_path = f"data/refinement_uploads/video_{uuid.uuid4().hex[:8]}.{ext}"
    os.makedirs("data/refinement_uploads", exist_ok=True)

    content = await file.read()
    if len(content) > 500 * 1024 * 1024:
        raise HTTPException(400, "视频文件不能超过 500MB")

    with open(temp_path, "wb") as f:
        f.write(content)

    svc = _get_refinement()
    try:
        result = await svc.refine_from_video(agent_id, temp_path)
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/document")
async def refine_from_document(
    agent_id: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """从文档炼化 — 知识层 + 认知层重点"""
    import uuid, os
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "txt"
    temp_path = f"data/refinement_uploads/doc_{uuid.uuid4().hex[:8]}.{ext}"
    os.makedirs("data/refinement_uploads", exist_ok=True)

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "文档不能超过 50MB")

    with open(temp_path, "wb") as f:
        f.write(content)

    svc = _get_refinement()
    try:
        result = await svc.refine_from_document(agent_id, temp_path, f".{ext}")
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/chat-history")
async def refine_from_chat_history(req: ChatHistoryRefineReq,
                                     user=Depends(get_current_user)):
    """从聊天记录炼化 — 最丰富的数据源"""
    if not req.messages:
        raise HTTPException(400, "聊天记录不能为空")

    svc = _get_refinement()
    result = await svc.refine_from_chat_history(req.agent_id, req.messages)
    return result


@router.post("/self-description")
async def refine_from_self_description(req: SelfDescriptionReq,
                                         user=Depends(get_current_user)):
    """从自我描述炼化 — 最直接、最深层的数据源

    请求体:
    {
        "agent_id": "agent_xxx",
        "answers": {
            "我是谁": "我是一个...",
            "我最看重什么": "家庭、...",
            "我害怕什么": "...",
            "我骄傲什么": "...",
            "我的思维方式": "...",
            "我和家人的关系": "...",
            "我的人生哲学": "...",
            "我学到了什么": "...",
            "我怎么说话": "...",
            "我的矛盾": "..."
        }
    }
    """
    if not req.answers:
        raise HTTPException(400, "请至少回答一个问题")

    svc = _get_refinement()
    result = await svc.refine_from_self_description(req.agent_id, req.answers)
    return result


# ==================== 查询接口 ====================

@router.get("/essence/{agent_id}")
async def get_essence(agent_id: str, user=Depends(get_current_user)):
    """获取数字人的七层本质"""
    svc = _get_refinement()
    essence = await svc.get_essence(agent_id)
    return essence


@router.get("/completeness/{agent_id}")
async def get_completeness(agent_id: str, user=Depends(get_current_user)):
    """获取数字人各维度炼化完成度"""
    svc = _get_refinement()
    completeness = await svc.get_completeness(agent_id)
    return {
        "agent_id": agent_id,
        "dimensions": completeness,
        "overall": round(sum(completeness.values()) / len(completeness), 1),
    }


@router.get("/history/{agent_id}")
async def get_refinement_history(agent_id: str, limit: int = 20,
                                   user=Depends(get_current_user)):
    """获取炼化历史记录"""
    svc = _get_refinement()
    history = await svc.get_refinement_history(agent_id, limit)
    return history


# ==================== 自我描述问卷模板 ====================

@router.get("/questionnaire")
async def get_questionnaire(user=Depends(get_current_user)):
    """获取自我描述问卷模板"""
    return {
        "title": "数字人炼化问卷 — 让AI理解你",
        "description": "回答以下问题，帮助你的数字分身更深入地理解你。答案越详细，炼化效果越好。",
        "philosophy": "这不仅是数据采集，而是一次自我对话。你对自己的理解，决定了数字人理解你的深度。",
        "questions": [
            {
                "id": "identity",
                "category": "认知层",
                "question": "你是谁？不只是名字，而是你如何定义自己。",
                "hint": "你的角色、身份、自我认知",
                "depth": "表面"
            },
            {
                "id": "values",
                "category": "价值层",
                "question": "你最看重什么？如果必须放弃一切只保留三样，你会留什么？",
                "hint": "核心价值观、不可妥协的事物",
                "depth": "深层"
            },
            {
                "id": "fears",
                "category": "情感层",
                "question": "你害怕什么？不只是蜘蛛或高处，而是内心深处的恐惧。",
                "hint": "失败？被遗忘？孤独？失去控制？",
                "depth": "最深层"
            },
            {
                "id": "pride",
                "category": "叙事层",
                "question": "你最骄傲的是什么？不一定是什么大事，可以是任何让你觉得'这就是我'的时刻。",
                "hint": "人生高光时刻、克服的困难",
                "depth": "深层"
            },
            {
                "id": "thinking",
                "category": "认知层",
                "question": "你怎么思考问题？遇到难题时，你的第一反应是什么？",
                "hint": "理性分析？直觉感受？找人商量？先放一放？",
                "depth": "中层"
            },
            {
                "id": "family",
                "category": "关系层",
                "question": "你和家人的关系是怎样的？谁对你最重要？你们之间有什么未说出口的话？",
                "hint": "亲密/疏远、依赖/独立、未解的心结",
                "depth": "深层"
            },
            {
                "id": "philosophy",
                "category": "价值层",
                "question": "你的人生哲学是什么？你相信什么道理？",
                "hint": "你用什么信念支撑自己走过困难",
                "depth": "最深层"
            },
            {
                "id": "learned",
                "category": "知识层",
                "question": "你学到了什么？不一定是在学校学的，可以是生活教你的。",
                "hint": "教训、领悟、技能、智慧",
                "depth": "深层"
            },
            {
                "id": "speaking",
                "category": "语言层",
                "question": "你怎么说话？你说话有什么特点？别人怎么评价你的表达方式？",
                "hint": "语速、口头禅、幽默方式、沉默习惯",
                "depth": "表面"
            },
            {
                "id": "contradictions",
                "category": "认知层",
                "question": "你有什么矛盾？你觉得自己有哪些'说一套做一套'的地方？",
                "hint": "内心冲突、理想与现实的差距",
                "depth": "最深层"
            },
        ],
    }
