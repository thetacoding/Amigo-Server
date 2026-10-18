from typing import Dict, Callable
from langchain_core.language_models.chat_models import BaseChatModel
from .providers import LLMProvider
from app.core.config import settings
from loguru import logger

class LLMFactory:
    # 策略映射表：核心解耦点
    _strategies: Dict[str, Callable[..., BaseChatModel]] = {
        "aliyun": LLMProvider.aliyun,
        "deepseek": LLMProvider.deepseek,
        "tencent": LLMProvider.tencent,
        "newapi": LLMProvider.newapi,
    }

    @classmethod
    def get_model(
        cls,
        provider: str = None,
        model: str = None,
        streaming: bool = True,
        reasoning: bool = True,
        **kwargs,
    ) -> BaseChatModel:
        """
        获取文本模型实例
        :param provider: 供应商名称 (aliyun/deepseek/tencent/newapi)
        :param kwargs: 初始化的模型参数
        """
        target_provider = provider or settings.default_llm_provider
        logger.info(f"target_provider: {target_provider}")
        handler = cls._strategies.get(target_provider.lower())
        
        if not handler:
            raise ValueError(f"❌ 不支持的供应商: {target_provider}")
        
        return handler(
            model=model,
            streaming=streaming,
            reasoning_mode=reasoning,
        )