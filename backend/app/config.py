import os

from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    # OpenAI 兼容协议配置，切换厂商只需改 .env，无需改代码
    # DeepSeek:  https://api.deepseek.com/v1
    # Qwen:      https://dashscope.aliyuncs.com/compatible-mode/v1
    # Kimi:      https://api.moonshot.cn/v1
    # GLM:       https://open.bigmodel.cn/api/paas/v4
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    system_prompt: str = "你是一个乐于助人的 AI 助手，请用简洁准确的中文回答问题。"
    history_limit: int = 20  # 每次请求携带的最近历史消息条数
    max_tokens: int = 2048
    temperature: float = 0.7
    stream_idle_timeout: float = 120.0  # SSE 读超时（秒）

    thinking_enabled_default: bool = True
    reasoning_effort: str = "high"  # low/high/max，映射见 README

    database_path: str = os.path.join(BASE_DIR, "data", "chat.db")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    class Config:
        env_file = os.path.join(BASE_DIR, ".env")
        env_file_encoding = "utf-8"


settings = Settings()
