# app/schemas/base.py
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum

class SessionInfo(BaseModel):
    session_id: str = Field(..., description="会话ID，用于服务端缓存或追踪")
    interaction_id: str = Field(..., description="会话轮次，用于服务端缓存或追踪")

class UserInfo(BaseModel):
    user_id: str = Field(..., description="用户id")

class DeviceInfo(BaseModel):
    device_id: str = Field(..., description="设备id")

class AppBaseInfo(BaseModel):
    package_name: str = Field(..., description="应用包名")

class SystemSetting(BaseModel):
    gps: str = Field(..., description="GPS")

class ResponseModel(BaseModel):
    code: int = 0
    msg: str = "success"
    data: Optional[Any] = None

class ChunkEvent(str, Enum):
    TEXT = "text"
    THINKING = "thinking"
    DEBUG = "debug"
    SUGGESTION = "suggestion"
    STEP = "step"
    DONE = "done"

class ChunkMeta(BaseModel):
    provider: str = Field(..., description="提供者")
    model: str = Field(..., description="模型")

class SseChunk(BaseModel):
    event: ChunkEvent = ChunkEvent.TEXT
    content: str = ""
    request: Optional[str] = None
    index: Optional[int] = None
    meta: Optional[ChunkMeta] = None
    stepId: Optional[str] = None
    stepLabel: Optional[str] = None
    extra: Optional[dict] = None

    def to_sse(self) -> str:
        """封装成标准 SSE 格式"""
        # ensure_ascii=False 保证中文不被转义，提高可读性
        data_str = self.model_dump_json(exclude_none=True, by_alias=True)
        return f"data: {data_str}\n\n"