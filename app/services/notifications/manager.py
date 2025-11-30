import asyncio
import logging
from typing import List
from app.services.notifications.base import NotificationProvider
from app.services.notifications.providers.telegram import TelegramProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manager to handle broadcasting messages to all registered notification providers.
    """

    def __init__(self):
        self.providers: List[NotificationProvider] = []
        self._register_default_providers()

    def _register_default_providers(self):
        """
        Registers providers based on configuration.
        """
        # Telegram
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            self.register_provider(TelegramProvider())
            logger.info("Telegram provider registered")

    def register_provider(self, provider: NotificationProvider):
        """
        Register a new notification provider.
        """
        self.providers.append(provider)

    async def broadcast_message(self, message: str):
        """
        Send the message to all registered providers.
        """
        if not self.providers:
            logger.warning("No notification providers registered")
            return

        tasks = []
        for provider in self.providers:
            tasks.append(provider.send_message(message))

        # Run all send tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)


notification_manager = NotificationManager()
