# app/api/v1_app/assets.py
from fastapi import APIRouter, Query
from typing import Optional
from app.schemas.base import ResponseModel
from app.services.config_service import ConfigService
from app.api.v1_app.feedback import FEEDBACK_ASSETS_PAYLOAD

router = APIRouter()


@router.get("/all", response_model=ResponseModel)
async def get_all():
    """获取全部预置的数据（含反馈点踩可选问题类型等云侧固定项）"""
    all = ConfigService.get_all()
    merged = {**all, "feedback": FEEDBACK_ASSETS_PAYLOAD}
    return ResponseModel(data=merged)


@router.get("/config", response_model=ResponseModel)
async def get_app_config():
    """App 启动时调用的全局配置（含反馈等云侧固定项，便于单次拉取）"""
    config = ConfigService.get_app_config()
    merged = {**config, "feedback": FEEDBACK_ASSETS_PAYLOAD}
    return ResponseModel(data=merged)

@router.get("/presets", response_model=ResponseModel)
async def get_presets(type: Optional[str] = Query(None, description="character, agent, or skill")):
    """获取预置资产数据，支持按类型过滤"""
    assets = ConfigService.get_assets(asset_type=type)
    return ResponseModel(data=assets)

@router.get("/chatSessions", response_model=ResponseModel)
async def get_presets():
    """获取预置会话数据"""
    chatSessions = ConfigService.get_chatSessions()
    return ResponseModel(data=chatSessions)