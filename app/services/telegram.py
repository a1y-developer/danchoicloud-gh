from typing import Optional
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.core.config import settings


class TelegramService:
    def __init__(self):
        if settings.TELEGRAM_BOT_TOKEN:
            self.bot = Bot(
                token=settings.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
            )
        else:
            self.bot = None

    async def send_message(
        self, chat_id: int, text: str, message_thread_id: Optional[int] = None
    ):
        if not self.bot:
            print("Telegram token not configured")
            return

        try:
            await self.bot.send_message(
                chat_id=chat_id, text=text, message_thread_id=message_thread_id
            )
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")

    async def close(self):
        if self.bot:
            await self.bot.session.close()


telegram_service = TelegramService()
