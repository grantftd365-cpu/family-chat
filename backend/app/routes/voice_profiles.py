"""语音音色管理 API"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from ..core.auth import get_current_user
from ..models.database import get_db

router = APIRouter(prefix="/api/voice-profiles")


def _get_voice_manager():
    """获取语音音色管理器（延迟导入避免循环）"""
    from ..main import voice_profile_manager
    if not voice_profile_manager:
        raise HTTPException(500, "语音音色管理器未初始化")
    return voice_profile_manager


class CreateProfileReq(BaseModel):
    name: str
    edge_voice_id: str = ""
    gender: str = ""


class UpdateProfileReq(BaseModel):
    name: str = ""
    edge_voice_id: str = ""
    pitch: float = 0
    speed: float = 0


class AssignVoiceReq(BaseModel):
    agent_id: str
    profile_id: str


@router.get("")
async def list_profiles(user=Depends(get_current_user)):
    """获取所有语音音色配置"""
    mgr = _get_voice_manager()
    profiles = await mgr.list_profiles()
    return {"profiles": profiles}


@router.get("/available")
async def list_available_voices(user=Depends(get_current_user)):
    """获取所有可用的 edge-tts 声音"""
    mgr = _get_voice_manager()
    return {"voices": mgr.get_available_voices()}


@router.post("")
async def create_profile(req: CreateProfileReq, user=Depends(get_current_user)):
    """创建语音音色配置（直接指定 edge-tts 声音）"""
    mgr = _get_voice_manager()
    profile = await mgr.create_profile(
        name=req.name,
        edge_voice_id=req.edge_voice_id,
        gender=req.gender,
    )
    return profile.to_dict()


@router.post("/upload")
async def upload_voice_profile(
    name: str = Form(...),
    gender: str = Form(""),
    voice_engine: str = Form("edge-tts"),
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """上传语音文件创建音色配置
    voice_engine='edge-tts': 分析音色特征匹配预设声音
    voice_engine='elevenlabs': 使用 ElevenLabs 克隆一模一样的声音
    """
    if not file.content_type or not file.content_type.startswith("audio/"):
        if not file.content_type or not file.content_type.startswith("video/"):
            raise HTTPException(400, "请上传音频或视频文件")

    import uuid, os
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "mp3"
    temp_path = f"data/voice_profiles/upload_{uuid.uuid4().hex[:8]}{ext}"
    os.makedirs("data/voice_profiles", exist_ok=True)

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "文件不能超过 50MB")

    # ElevenLabs 声音克隆需要至少 1 分钟音频
    if voice_engine == "elevenlabs" and len(content) < 500 * 1024:
        raise HTTPException(400, "声音克隆需要至少 1 分钟的音频，请上传更长的录音")

    with open(temp_path, "wb") as f:
        f.write(content)

    mgr = _get_voice_manager()
    try:
        profile = await mgr.create_profile(
            name=name,
            audio_file_path=temp_path,
            gender=gender,
            voice_engine=voice_engine,
        )
        return profile.to_dict()
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(500, f"创建音色配置失败: {e}")


@router.get("/{profile_id}")
async def get_profile(profile_id: str, user=Depends(get_current_user)):
    """获取单个音色配置"""
    mgr = _get_voice_manager()
    profile = await mgr.get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "音色配置不存在")
    return profile.to_dict()


@router.put("/{profile_id}")
async def update_profile(profile_id: str, req: UpdateProfileReq,
                          user=Depends(get_current_user)):
    """更新音色配置"""
    mgr = _get_voice_manager()
    kwargs = {}
    if req.name: kwargs["name"] = req.name
    if req.edge_voice_id: kwargs["edge_voice_id"] = req.edge_voice_id
    if req.pitch: kwargs["pitch"] = req.pitch
    if req.speed: kwargs["speed"] = req.speed

    success = await mgr.update_profile(profile_id, **kwargs)
    if not success:
        raise HTTPException(404, "音色配置不存在")
    return {"status": "ok"}


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, user=Depends(get_current_user)):
    """删除音色配置"""
    mgr = _get_voice_manager()
    success = await mgr.delete_profile(profile_id)
    if not success:
        raise HTTPException(404, "音色配置不存在")
    return {"status": "ok"}


@router.post("/assign")
async def assign_voice(req: AssignVoiceReq, user=Depends(get_current_user)):
    """将音色配置分配给数字人"""
    mgr = _get_voice_manager()
    success = await mgr.assign_to_agent(req.agent_id, req.profile_id)
    if not success:
        raise HTTPException(400, "分配失败，请检查 agent_id 和 profile_id")
    return {"status": "ok"}


@router.get("/agent/{agent_id}")
async def get_agent_voice(agent_id: str, user=Depends(get_current_user)):
    """获取数字人关联的音色配置"""
    mgr = _get_voice_manager()
    voice = await mgr.get_agent_voice(agent_id)
    if not voice:
        return {"profile": None, "message": "该数字人未配置专属音色"}
    return {"profile": voice}


@router.post("/synthesize")
async def synthesize_voice(
    text: str = Form(...),
    profile_id: str = Form(""),
    edge_voice_id: str = Form(""),
    user=Depends(get_current_user)
):
    """使用指定音色合成语音（预览）"""
    mgr = _get_voice_manager()
    output_path = await mgr.synthesize(text, profile_id=profile_id, edge_voice_id=edge_voice_id)
    if not output_path:
        raise HTTPException(500, "语音合成失败")
    from fastapi.responses import FileResponse
    return FileResponse(output_path, media_type="audio/mpeg")
