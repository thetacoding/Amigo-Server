from abc import ABC, abstractmethod
from langchain_core.language_models.chat_models import BaseChatModel

class LLMProvider(ABC):
    @abstractmethod
    def create(self) -> BaseChatModel:
        """子类必须实现此方法，返回一个 LangChain 模型对象"""
        pass