from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    # GitHub
    GITHUB_APP_ID: str
    GITHUB_PRIVATE_KEY: str
    GITHUB_WEBHOOK_SECRET: str
    GITHUB_APP_SLUG: str | None = None
    GITHUB_OAUTH_CLIENT_ID: str | None = None
    GITHUB_OAUTH_CLIENT_SECRET: str | None = None
    GITHUB_OAUTH_SCOPES: str = "read:user"
    GITHUB_OAUTH_REDIRECT_URI: str | None = None
    WEB_BASE_URL: str = "http://localhost:3000"
    SESSION_COOKIE_NAME: str = "danchoicloud_session"
    SESSION_EXPIRES_DAYS: int = 7
    COOKIE_SECURE: bool = False

    # CLA Assistant
    CLA_ENABLED: bool = True
    CLA_DOCUMENT_URL: str | None = None
    CLA_SIGNATURES_REPO: str | None = None  # e.g. "a1y-developer/cla.db"
    CLA_SIGNATURES_PATH: str = "signatures/version1/cla.json"
    CLA_SIGNATURES_BRANCH: str = "main"
    CLA_ALLOWLIST: str = "bot"  # comma-separated usernames/bots
    CLA_SIGN_PHRASE: str = "I have read the CLA Document and I hereby sign the CLA"
    CLA_RECHECK_PHRASE: str = "recheck"
    CLA_LOCK_AFTER_MERGE: bool = True

    # Google Gemini
    GEMINI_API_KEY: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: int | None = None  # ID of the group chat to send notifications to
    TELEGRAM_THREAD_ID: Optional[int] = (
        None  # ID of the topic (thread) within the group
    )

    # Database
    DATABASE_URL: str | None = None
    LOCAL_DB_PATH: str = "./data/app.db"

    # Integration scope (optional hard limit)
    INTEGRATION_SCOPE_TYPE: str | None = None
    INTEGRATION_SCOPE_NAME: str | None = None

    # CORS
    EXTRA_CORS_ORIGINS: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
