"""增强炼化 API - 支持多模态输入"""
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


class TextRefineReq(BaseModel):
    agent_id: str
    text: str
    source: str = "text"


class ChatHistoryRefineReq(BaseModel):
    agent_id: str
    messages: list[dict]
    group_id: str = ""


@router.post("/text")
async def refine_from_text(req: TextRefineReq, user=Depends(get_current_user)):
    """从文本炼化数字人"""
    svc = _get_refinement()
    try:
        result = await svc.refine_from_text(req.agent_id, req.text)
        return result
    except ValueError as e:
        # LLM not configured — do basic keyword extraction instead
        from ..models.database import get_db, now
        import json
        traits = {"traits": [], "speaking_style": "", "interests": [], "catchphrases": []}
        text = req.text
        # Simple keyword extraction
        happy_words = ["开心", "高兴", "乐观", "开朗", "爱笑", "活泼"]
        kind_words = ["善良", "温柔", "体贴", "关心", "真诚"]
        for w in happy_words:
            if w in text: traits["traits"].append(w)
        for w in kind_words:
            if w in text: traits["traits"].append(w)
        if not traits["traits"]:
            traits["traits"] = ["善于表达"]
        db = await get_db()
        try:
            await db.execute(
                "UPDATE agents SET traits=?,speaking_style=?,refinement_count=refinement_count+1,updated_at=? WHERE id=?",
                (json.dumps(traits["traits"], ensure_ascii=False), traits["speaking_style"], now(), req.agent_id)
            )
            await db.commit()
        finally:
            await db.close()
        return {"success": True, "traits": traits, "source": "text", "note": "LLM未配置，使用关键词提取"}


@router.post("/voice")
async def refine_from_voice(
    agent_id: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """从语音炼化数字人
    上传音频文件 -> 语音转文字 -> 提取性格特征
    """
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(400, "请上传音频文件")

    import uuid, os
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "mp3"
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
    """从视频炼化数字人
    上传视频 -> 提取音频 -> 语音转文字 + 音色提取 -> 性格提取
    """
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(400, "请上传视频文件")

    import uuid, os
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "mp4"
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
    """从文档炼化数字人
    支持: txt, pdf, docx, xlsx, md, json
    """
    allowed_types = [
        "text/plain", "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/markdown", "application/json",
    ]

    import uuid, os
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "txt"
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
    """从聊天记录炼化数字人
    分析消息模式、说话习惯、性格特征
    """
    if not req.messages:
        raise HTTPException(400, "聊天记录不能为空")

    svc = _get_refinement()
    result = await svc.refine_from_chat_history(req.agent_id, req.messages)
    return result
