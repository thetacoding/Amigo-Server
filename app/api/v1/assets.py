# app/api/v1/assets.py
from fastapi import APIRouter
from app.schemas.base import ResponseModel

router = APIRouter()

@router.get("/all", response_model=ResponseModel)
async def get_all_assets():
    # 这里未来可以改成从数据库读取
    mock_assets = {
        "characters": [
            {"id": "c1", "name": "诸葛亮", "emoji": "👨‍🎓", "cat": "智能角色", "stage": "stable", "desc": "智绝千古的蜀汉丞相"},
            {"id": "c2", "name": "张飞", "emoji": "🧔", "cat": "智能角色", "stage": "stable", "desc": "燕人张翼德"}
        ],
        "skills": [
            {"id": "s1", "name": "文案润色", "emoji": "✍️", "cat": "实用技能", "stage": "stable", "desc": "让你的文字更有深度"}
        ]
    }
    return ResponseModel(data=mock_assets)