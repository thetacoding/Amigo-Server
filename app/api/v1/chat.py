# app/api/v1/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.schemas.base import ResponseModel
import openai
import os

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: str = "gemini-1.5-flash"

@router.post("/completions", response_model=ResponseModel)
async def chat_completions(req: ChatRequest):
    try:
        # 这里建议封装进 services/ai_service.py
        # 目前先直接演示调用逻辑
        client = openai.OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        response = client.chat.completions.create(
            model=req.model,
            messages=[{"role": "user", "content": req.message}]
        )
        
        ai_reply = response.choices[0].message.content
        return ResponseModel(data={"reply": ai_reply})
    except Exception as e:
        return ResponseModel(code=500, msg=str(e))