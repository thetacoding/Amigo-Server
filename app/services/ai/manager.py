
class AIHubManager:
    @classmethod
    def get_llm(cls, provider: str = None) -> BaseChatModel:
        """获取文本大模型实例"""
        return LLMFactory.get_provider(provider or settings.default_llm)

    @classmethod
    def get_image_engine(cls, provider: str = None):
        """获取文生图引擎实例"""
        return ImageFactory.get_provider(provider or settings.default_image_gen)

    @classmethod
    async def text_to_image(cls, prompt: str, **kwargs):
        """
        文生图任务统一接口
        :param kwargs: 接收 width, height, style, negative_prompt 等参数
        """
        engine = cls.get_image_engine()
        return await engine.generate(prompt, **kwargs)