import json
from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，读取项目根目录下的 .env，并兼容 Render 注入的环境变量。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "quiz-server"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # SQLite 默认；切换 PostgreSQL / Neon 只改这一项即可。
    # Neon 连接串通常形如：
    #   postgresql+psycopg://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
    DB_URL: str = "sqlite:///./data/quiz.db"
    DB_ECHO: bool = False

    # 跨域白名单（原始字符串，支持两种写法，渲染成列表见 cors_origins_list）：
    #   - JSON 数组：  CORS_ORIGINS=["https://a.com","https://b.com"]
    #   - 逗号分隔：  CORS_ORIGINS=https://a.com,https://b.com
    CORS_ORIGINS: str = "http://localhost:5173"

    # Render 注入的监听端口，本地默认 8001。
    PORT: int = 8001

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        s = (self.CORS_ORIGINS or "").strip()
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except (json.JSONDecodeError, ValueError):
                pass
        return [x.strip() for x in s.split(",") if x.strip()]

    # 代码题沙箱（默认关闭，见 DESIGN §8）
    SANDBOX_ENABLED: bool = False
    SANDBOX_IMAGE: str = "python:3.12-alpine"
    SANDBOX_TIMEOUT_MS: int = 2000
    SANDBOX_MEMORY_MB: int = 128

    # 连续答对多少次后从错题本清除
    CLEAR_STREAK: int = 2

    # 心跳超时（秒），超时后服务端把 active 会话置 paused
    HEARTBEAT_TIMEOUT_SEC: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
