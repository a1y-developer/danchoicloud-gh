import logging

from app.services.notifications.base import NotificationProvider
from app.services.notifications.providers.discord import DiscordProvider
from app.services.notifications.providers.slack import SlackProvider
from app.services.notifications.providers.telegram import TelegramProvider
from app.services.notifications.providers.webhook import WebhookProvider

logger = logging.getLogger(__name__)


def create_provider(channel_type: str, config: dict) -> NotificationProvider | None:
    channel_type = channel_type.lower()
    if channel_type == "telegram":
        return TelegramProvider(
            bot_token=config.get("bot_token"),
            chat_id=config.get("chat_id"),
            thread_id=config.get("thread_id"),
        )
    if channel_type == "slack":
        return SlackProvider(config.get("webhook_url"))
    if channel_type == "discord":
        return DiscordProvider(config.get("webhook_url"))
    if channel_type == "webhook":
        url = config.get("url") or config.get("webhook_url")
        return WebhookProvider(
            url,
            headers=config.get("headers"),
            method=config.get("method", "POST"),
        )

    logger.warning("Unsupported notification channel type: %s", channel_type)
    return None
