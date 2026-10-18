class AIService:
    @classmethod
    async def chat_custom(cls, message: str, **kwargs):
        """
        **kwargs 可以接收 temperature, top_p, max_tokens 等任何参数
        """
        # 1. 获取基础模型实例 (来自你的注册表工厂)
        base_model = cls.get_model()
        
        # 2. 动态绑定运行参数 (这是关键！)
        # .bind 会创建一个新的临时实例，带上你传入的调教参数
        configurable_model = base_model.bind(
            temperature=kwargs.get("temperature", 0.7),
            top_p=kwargs.get("top_p", 0.9),
            extra_body={ # 针对某些模型特有的参数
                "top_k": kwargs.get("top_k", 50)
            }
        )
        
        # 3. 执行请求
        response = await configurable_model.ainvoke(message)
        return response.content