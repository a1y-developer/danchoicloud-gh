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
        if settings.TELEGRAM_BOT_TOKEN:
            channels = self._parse_telegram_channels(settings.TELEGRAM_CHANNELS)
            if channels:
                for chat_id, thread_id in channels:
                    self.register_provider(
                        TelegramProvider(chat_id=chat_id, thread_id=thread_id)
                    )
                logger.info("Registered %d Telegram channel provider(s)", len(channels))
            elif settings.TELEGRAM_CHAT_ID:
                self.register_provider(
                    TelegramProvider(
                        chat_id=settings.TELEGRAM_CHAT_ID,
                        thread_id=settings.TELEGRAM_THREAD_ID,
                    )
                )
                logger.info("Telegram provider registered (legacy single channel)")
            else:
                logger.warning(
                    "TELEGRAM_BOT_TOKEN is set but no TELEGRAM_CHANNELS/TELEGRAM_CHAT_ID configured"
                )

    def _parse_telegram_channels(
        self, raw_channels: str | None
    ) -> list[tuple[int, int | None]]:
        """
        Parse TELEGRAM_CHANNELS values formatted as:
        "<chat_id>" or "<chat_id>:<thread_id>" entries separated by commas.

        Returns:
            A list of (chat_id, thread_id) tuples where thread_id may be None.
        """
        if not raw_channels:
            return []

        channels_list: list[tuple[int, int | None]] = []
        for raw_entry in raw_channels.split(","):
            entry = raw_entry.strip()
            if not entry:
                continue

            chat_id_part, _, thread_id_part = entry.partition(":")
            chat_id_text = chat_id_part.strip()
            thread_id_text = thread_id_part.strip()
            if not chat_id_text:
                logger.warning(
                    "Invalid TELEGRAM_CHANNELS entry '%s'; missing chat_id", entry
                )
                continue

            try:
                chat_id = int(chat_id_text)
                thread_id = int(thread_id_text) if thread_id_text else None
            except ValueError:
                logger.warning(
                    "Invalid TELEGRAM_CHANNELS entry '%s'; expected chat_id[:thread_id]",
                    entry,
                )
                continue

            channels_list.append((chat_id, thread_id))

        return channels_list

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
