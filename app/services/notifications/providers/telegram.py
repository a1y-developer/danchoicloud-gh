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

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: int | str | None = None,
        thread_id: int | str | None = None,
    ):
        self.chat_id = self._parse_int(chat_id)
        if self.chat_id is None:
            self.chat_id = settings.TELEGRAM_CHAT_ID

        self.thread_id = self._parse_int(thread_id)
        if self.thread_id is None:
            self.thread_id = settings.TELEGRAM_THREAD_ID

        resolved_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.bot = None

        if resolved_token:
            self.bot = Bot(
                token=resolved_token,
                default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
            )
        else:
            logger.warning(
                "TELEGRAM_BOT_TOKEN not set, Telegram notifications disabled."
            )

    @staticmethod
    def _parse_int(value: int | str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

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
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}", exc_info=True)

    async def close(self):
        if self.bot:
            await self.bot.session.close()
