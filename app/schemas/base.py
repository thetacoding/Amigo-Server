# app/schemas/base.py
from pydantic import BaseModel
from typing import Optional, Any

class ResponseModel(BaseModel):
    code: int = 0
    msg: str = "success"
    data: Optional[Any] = None