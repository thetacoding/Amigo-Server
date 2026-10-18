import pytest
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.ai.llm.factory import LLMFactory
from langchain_core.messages import HumanMessage

# 配置 pytest-asyncio，允许测试异步函数
pytestmark = pytest.mark.asyncio

def print_json(title, data):
    """辅助函数：美化打印 JSON"""
    print(f"\n{'='*20} {title} {'='*20}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"{'='*50}")

async def test_llm_factory_connectivity():
    """
    测试 Service 层：直接调用模型，看能否收到回复
    """
    print("\n[开始测试] Service 层模型调用...")
    try:
        # 1. 获取默认模型
        llm = LLMFactory.get_model()
        
        # 2. 构造一个简单的消息
        messages = [HumanMessage(content="你好，请自我介绍一下")]
        
        # 3. 发起请求
        response = await llm.ainvoke(messages)
        
        print(f"✅ Service 层成功收到回复: {response.content[:50]}...")
        assert response.content is not None
        assert len(response.content) > 0
    except Exception as e:
        pytest.fail(f"❌ Service 层连接失败: {str(e)}")

async def test_api_chat_completions():
    """
    测试 API 层：通过 FastAPI 路由进行端到端测试
    """
    print("\n[开始测试] API 接口调用...")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "messages": [
                {"role": "user", "content": "帮我写一首关于张飞的短诗", "name": "user1"}
            ],
            "session_id": "test_session_123",
            "temperature": 0.5
        }
        
        response = await ac.post("/api/v1_app/chat/completions", json=payload)
        
        # assert response.status_code == 200
        data = response.json()
        print_json("APP CONFIG RESPONSE", data)
        if response.status_code != 200 or data["code"] != 0:
            print(f"\n❌ API 报错内容: {data.get('msg')}") # 👈 加上这一行
        assert data["code"] == 0
        assert "reply" in data["data"]
        print(f"✅ API 层成功收到回复: {data['data']['reply'][:50]}...")