import sys
import logging
from pydantic_settings import BaseSettings
from pydantic import field_validator

_startup_logger = logging.getLogger("deepresearch.config")


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    DATABASE_URL: str

    JWT_SECRET: str
    JWT_EXPIRES_IN: int = 86400
    JWT_REMEMBER_ME_EXPIRES_IN: int = 604800

    BCRYPT_ROUNDS: int = 12

    LLM_API_KEY: str
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_TIMEOUT: int = 60

    BRAVE_API_KEY: str
    BRAVE_MCP_URL: str = "http://brave-mcp:3000"
    MCP_TIMEOUT: int = 30
    SUB_AGENT_TIMEOUT: int = 300
    TAVILY_API_KEY: str | None = None

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "console"

    @field_validator("JWT_SECRET")
    @classmethod
    def check_jwt_secret(cls, v: str) -> str:
        # 启动前安全校验 — structlog 此时未初始化，使用 stderr
        if not v:
            print("[FATAL] JWT_SECRET 未配置，拒绝启动 (EC-AUTH-006)", file=sys.stderr)
            sys.exit(1)
        if len(v) < 32:
            print("[FATAL] JWT_SECRET 长度不足 32 字符，拒绝启动 (EC-AUTH-006)", file=sys.stderr)
            sys.exit(1)
        if v.startswith("CHANGE_ME"):
            print("[WARN] JWT_SECRET 使用占位符，仅适用于开发环境", file=sys.stderr)
        return v


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
