from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import settings
from app.services.new_api.client import normalized_newapi_v1_base
from loguru import logger


def _attach_runtime_meta(llm: BaseChatModel, provider: str, model: str) -> BaseChatModel:
    """
    在模型对象上附加统一元信息，供上层从 runnable 读取。
    """
    setattr(llm, "_runtime_provider", provider)
    setattr(llm, "_runtime_model", model)
    return llm


class LLMProvider:
    """
    文本模型供应商：负责具体的实例化
    """
    @staticmethod
    def aliyun(model: str = None, streaming: bool = False, reasoning_mode: bool = False) -> BaseChatModel:
        # dashscope_api_key 是基础配置，kwargs 是运行时调教参数
        model_name = model or "qwen-plus"
        llm = ChatTongyi(
            model_name=model_name,
            dashscope_api_key=settings.dashscope_api_key,
            streaming=streaming
        )
        return _attach_runtime_meta(llm, provider="aliyun", model=model_name)
    
    @staticmethod
    def tencent(model: str = None, streaming: bool = False, reasoning_mode: bool = False) -> BaseChatModel:
        # 腾讯的思考模型通常是特定的 ID，如 hunyuan-reasoner
        default_model = "hunyuan-reasoner" if reasoning_mode else "hunyuan-standard"
        if not model:
            model = default_model
        logger.info(f"model_name={model}")
        
        llm = ChatOpenAI(
            model=model,
            openai_api_key=settings.tencent_hunyuan_api_key,
            # 🚀 关键点：指向腾讯混元的 OpenAI 兼容地址
            openai_api_base="https://api.hunyuan.cloud.tencent.com/v1",
            streaming=streaming
        )
        return _attach_runtime_meta(llm, provider="tencent", model=model)

    @staticmethod
    def deepseek(model: str = None, streaming: bool = False, reasoning_mode: bool = False) -> BaseChatModel:
        model_name = model or "deepseek-chat"
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=settings.deepseek_api_key,
            openai_api_base=settings.deepseek_base_url,
            streaming=streaming
        )
        return _attach_runtime_meta(llm, provider="deepseek", model=model_name)

    @staticmethod
    def newapi(model: str = None, streaming: bool = False, reasoning_mode: bool = False) -> BaseChatModel:
        """
        通过 New API 网关的 OpenAI 兼容 /v1 访问聊天接口；base/key 与
        `app.services.new_api.client.NewApiClient` 使用的配置一致。
        """
        model_name = model or settings.newapi_default_model
        base = normalized_newapi_v1_base()
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=settings.newapi_api_key,
            openai_api_base=base,
            streaming=streaming,
        )
        return _attach_runtime_meta(llm, provider="newapi", model=model_name)

    # 未来你学了 Gemini，只需要在这里加一个静态方法即可