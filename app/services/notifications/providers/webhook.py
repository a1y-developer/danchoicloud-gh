import asyncio
import logging

import requests

from app.services.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)


class WebhookProvider(NotificationProvider):
    def __init__(
        self, url: str | None, headers: dict | None = None, method: str = "POST"
    ):
        self.url = url
        self.headers = headers or {}
        self.method = method.upper() if method else "POST"

    async def send_message(self, message: str):
        if not self.url:
            logger.warning("Webhook URL missing, skipping notification.")
            return
        await asyncio.to_thread(self._post_message, message)

    def _post_message(self, message: str) -> None:
        payload = {"message": message, "format": "markdown"}
        try:
            response = requests.request(
                self.method,
                self.url,
                json=payload,
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.error("Failed to send webhook notification: %s", exc, exc_info=True)
