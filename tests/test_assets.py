import pytest
import json
from httpx import ASGITransport, AsyncClient
from app.main import app

def print_json(title, data):
    """辅助函数：美化打印 JSON"""
    print(f"\n{'='*20} {title} {'='*20}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"{'='*50}")

@pytest.mark.asyncio
async def test_get_app_config():
    """测试获取全局配置接口"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1_app/assets/config")
        
        assert response.status_code == 200
        data = response.json()
        print_json("APP CONFIG RESPONSE", data)
        assert data["code"] == 0
        assert data["msg"] == "success"
        
        # 验证返回的关键字段是否存在
        config = data["data"]
        assert "supported_providers" in config
        assert "payment_qrcode_url" in config
        assert isinstance(config["models"], dict)
        print(f"\n✅ App Config 验证通过: {config['supported_providers']}")

@pytest.mark.asyncio
async def test_get_presets_roles():
    """测试获取预置角色列表"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 模拟前端请求 type=roles
        response = await ac.get("/api/v1_app/assets/presets", params={"type": "roles"})
        
        assert response.status_code == 200
        data = response.json()
        print_json("APP CONFIG RESPONSE", data)
        assert data["code"] == 0
        
        # 验证返回的是列表且包含预设数据
        presets = data["data"]
        assert isinstance(presets, list)
        if len(presets) > 0:
            assert "id" in presets[0]
            assert "name" in presets[0]
        print(f"\n✅ Presets Roles 验证通过，获取到 {len(presets)} 个角色")

@pytest.mark.asyncio
async def test_get_presets_invalid_type():
    """测试传入不存在的类型时系统的表现"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1_app/assets/presets", params={"type": "non_existent"})
        
        assert response.status_code == 200
        data = response.json()
        print_json("APP CONFIG RESPONSE", data)
        # 根据 Service 逻辑，找不到类型应返回空列表 []
        assert data["data"] == []
        print("\n✅ 非法类型空值返回验证通过")