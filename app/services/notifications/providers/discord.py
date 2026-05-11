import asyncio
import logging

import requests

from app.services.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)


class DiscordProvider(NotificationProvider):
    def __init__(self, webhook_url: str | None):
        self.webhook_url = webhook_url

    async def send_message(self, message: str):
        if not self.webhook_url:
            logger.warning("Discord webhook URL missing, skipping notification.")
            return
        await asyncio.to_thread(self._post_message, message)

    def _post_message(self, message: str) -> None:
        try:
            response = requests.post(
                self.webhook_url,
                json={"content": message},
                timeout=10,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.error("Failed to send Discord message: %s", exc, exc_info=True)
