from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "instagram-upsell"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "changethislater123"

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres123"
    POSTGRES_DB: str = "instagram_upsell"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = ""

    # Meta
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_PAGE_ACCESS_TOKEN: str = ""
    META_INSTAGRAM_ACCOUNT_ID: str = ""
    META_INSTAGRAM_USER_TOKEN: str = ""
    META_FACEBOOK_PAGE_ID: str = ""
    META_FB_PAGE_TOKEN: str = ""
    META_WEBHOOK_VERIFY_TOKEN: str = "startnow123"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
