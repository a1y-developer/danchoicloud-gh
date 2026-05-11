import asyncio
import logging
from typing import List
from app.services.notifications.base import NotificationProvider
from app.services.notifications.factory import create_provider
from app.services.notifications.providers.telegram import TelegramProvider
from app.services.notifications.store import resolve_channels
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

    async def _get_scoped_providers(
        self, org_name: str | None, repo_full_name: str | None
    ) -> List[NotificationProvider]:
        channels = await asyncio.to_thread(resolve_channels, org_name, repo_full_name)
        providers: List[NotificationProvider] = []
        for channel in channels:
            provider = create_provider(channel.channel_type, channel.config or {})
            if provider:
                providers.append(provider)
        return providers

    async def _close_providers(self, providers: List[NotificationProvider]):
        for provider in providers:
            close_method = getattr(provider, "close", None)
            if close_method:
                await close_method()

    async def broadcast_message(
        self,
        message: str,
        org_name: str | None = None,
        repo_full_name: str | None = None,
    ):
        """
        Send the message to all registered providers.
        """
        scoped_providers = await self._get_scoped_providers(org_name, repo_full_name)
        providers = scoped_providers or self.providers

        if not providers:
            logger.warning("No notification providers registered")
            return

        tasks = []
        for provider in providers:
            tasks.append(provider.send_message(message))

        # Run all send tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        if scoped_providers:
            await self._close_providers(scoped_providers)

    async def close(self):
        if self.providers:
            await self._close_providers(self.providers)


notification_manager = NotificationManager()
