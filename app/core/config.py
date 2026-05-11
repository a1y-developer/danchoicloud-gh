from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    # GitHub
    GITHUB_APP_ID: str
    GITHUB_PRIVATE_KEY: str
    GITHUB_WEBHOOK_SECRET: str

    # CLA Assistant
    CLA_ENABLED: bool = True
    CLA_DOCUMENT_URL: str | None = None
    CLA_SIGNATURES_REPO: str | None = None  # e.g. "a1y-developer/cla.db"
    CLA_SIGNATURES_PATH: str = "signatures/version1/cla.json"
    CLA_SIGNATURES_BRANCH: str = "main"
    CLA_ALLOWLIST: str = "bot"  # comma-separated usernames/bots
    CLA_AI_AGENT_ALLOWLIST: str = ""  # comma-separated AI agent usernames
    CLA_SIGN_PHRASE: str = "I have read the CLA Document and I hereby sign the CLA"
    CLA_RECHECK_PHRASE: str = "recheck"
    CLA_LOCK_AFTER_MERGE: bool = True

    # Google Gemini
    GEMINI_API_KEY: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: int  # ID of the group chat to send notifications to
    TELEGRAM_THREAD_ID: Optional[int] = (
        None  # ID of the topic (thread) within the group
    )

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
