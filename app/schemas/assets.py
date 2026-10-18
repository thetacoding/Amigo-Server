import time
from pydantic import BaseModel
from typing import List, Dict, Optional

class ModelInfo(BaseModel):
    reasoning: bool

class ModelProvider(BaseModel):
    default_model: str
    models: Dict[str, List[ModelInfo]]

class AppConfigResp(BaseModel):
    supported_providers: List[str]
    default_provider: str
    payment_qrcode_url: str
    model_providers: Dict[str, ModelProvider]

class AssetPreset(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    emoji: Optional[str] = None
    desc: Optional[str] = None
    stage: Optional[str] = None
    systemPrompt: Optional[str] = None  # Agent 可能会用到

class ChatSession(BaseModel):
    id : str
    title : str
    lastMsg : Optional[str] = None
    updateTime : Optional[str] = int(time.time() * 1000)
    avatar : Optional[str] = None
    templateId : Optional[str] = None
    systemPrompt : Optional[str] = None