from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    # GitHub
    GITHUB_APP_ID: str
    GITHUB_PRIVATE_KEY: str
    GITHUB_WEBHOOK_SECRET: str

    # Google Gemini
    GEMINI_API_KEY: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: int # ID of the group chat to send notifications to
    TELEGRAM_THREAD_ID: Optional[int] = None # ID of the topic (thread) within the group
    
    # Logging
    LOG_LEVEL: str = "INFO"

settings = Settings()
