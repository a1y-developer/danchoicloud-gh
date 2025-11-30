import logging
import telegramify_markdown
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.services.notifications.base import NotificationProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramProvider(NotificationProvider):
    """
    Notification provider for Telegram.
    Handles conversion from standard Markdown to Telegram MarkdownV2.
    """

    def __init__(self):
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.thread_id = settings.TELEGRAM_THREAD_ID
        self.bot = None

        if settings.TELEGRAM_BOT_TOKEN:
            self.bot = Bot(
                token=settings.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
            )
        else:
            logger.warning(
                "TELEGRAM_BOT_TOKEN not set, Telegram notifications disabled."
            )

    def _convert_to_telegram_md(self, text: str) -> str:
        """
        Converts Markdown to Telegram MarkdownV2 format using telegramify-markdown.
        """
        if not text:
            return ""
        return telegramify_markdown.markdownify(text, normalize_whitespace=False)

    async def send_message(self, message: str):
        if not self.bot or not self.chat_id:
            logger.warning(
                "Cannot send Telegram message: Bot token or Chat ID missing."
            )
            return

        converted_message = self._convert_to_telegram_md(message)

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=converted_message,
                message_thread_id=self.thread_id,
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}", exc_info=True)

    async def close(self):
        if self.bot:
            await self.bot.session.close()
