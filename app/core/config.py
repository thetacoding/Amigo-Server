from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # 注意：变量名要和 .env 里的 key 保持一致
    # 1. 供应商配置
    default_llm_provider: str = "aliyun"
    llm_provider: str = "aliyun"

    # 1.1 New API / one-api 等 OpenAI 兼容网关（统一转发各厂家模型）
    newapi_base_url: str = Field(
        default="http://127.0.0.1:3000/v1",
        env="NEWAPI_BASE_URL",
    )
    newapi_api_key: str = Field(
        default="sk-mock-replace-me",
        env="NEWAPI_API_KEY",
    )
    newapi_default_model: str = Field(
        default="gpt-4o-mini",
        env="NEWAPI_DEFAULT_MODEL",
    )

    # 2. 密钥配置
    dashscope_api_key: str
    tencent_hunyuan_api_key: str = Field(default="", env="TENCENT_HUNYUAN_API_KEY")
    tavily_api_key: str = Field(default="", env="TAVILY_API_KEY")

    # 3. Tavily Web Search 配置
    tavily_api_url: str = Field(default="https://api.tavily.com/search", env="TAVILY_API_URL")
    tavily_search_depth: str = Field(default="basic", env="TAVILY_SEARCH_DEPTH")
    tavily_include_answer: bool = Field(default=True, env="TAVILY_INCLUDE_ANSWER")
    tavily_include_raw_content: bool = Field(default=False, env="TAVILY_INCLUDE_RAW_CONTENT")
    tavily_max_results: int = Field(default=5, env="TAVILY_MAX_RESULTS")
    tavily_timeout_seconds: int = Field(default=20, env="TAVILY_TIMEOUT_SECONDS")

    # 3.1 百度 Web Search 配置（POST /v2/ai_search/web_search，非 chat/completions）
    baidu_search_api_key: str = Field(default="", env="BAIDU_SEARCH_API_KEY")
    baidu_search_api_url: str = Field(
        default="https://qianfan.baidubce.com/v2/ai_search/web_search",
        env="BAIDU_SEARCH_API_URL",
    )
    baidu_search_source: str = Field(
        default="baidu_search_v2",
        env="BAIDU_SEARCH_SOURCE",
    )
    baidu_search_max_results: int = Field(default=5, env="BAIDU_SEARCH_MAX_RESULTS")
    baidu_search_timeout_seconds: int = Field(default=20, env="BAIDU_SEARCH_TIMEOUT_SECONDS")

    # 3.2 火山（路由 id=volcengine）：字节系 FeedCoop open.feedcoopapi.com /search_api/web_search
    volcengine_search_api_key: str = Field(default="", env="VOLCENGINE_SEARCH_API_KEY")
    volcengine_search_api_url: str = Field(
        default="https://open.feedcoopapi.com/search_api/web_search",
        env="VOLCENGINE_SEARCH_API_URL",
    )
    # web=原始网页结果；web_summary=带模型总结（以接口方文档为准）
    volcengine_search_type: str = Field(default="web", env="VOLCENGINE_SEARCH_TYPE")
    volcengine_search_need_content: bool = Field(
        default=True,
        env="VOLCENGINE_SEARCH_NEED_CONTENT",
    )
    volcengine_search_need_summary: bool = Field(
        default=True,
        env="VOLCENGINE_SEARCH_NEED_SUMMARY",
    )
    volcengine_search_max_results: int = Field(default=5, env="VOLCENGINE_SEARCH_MAX_RESULTS")
    volcengine_search_timeout_seconds: int = Field(
        default=20,
        env="VOLCENGINE_SEARCH_TIMEOUT_SECONDS",
    )

    # 4. 使用新版 Pydantic V2 的配置方式，消除警告
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  # 👈 核心建议：设置为 ignore，这样即便 .env 里有多余变量也不会报错
    )

settings = Settings()