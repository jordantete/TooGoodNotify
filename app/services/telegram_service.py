from app.core.telegram_bot_handler import TelegramBotHandler
from app.common.logger import LOGGER

class TelegramService:
    def __init__(self):
        self.bot_handler = TelegramBotHandler()

    async def process_webhook(self, event):
        LOGGER.info(f"Processing Telegram webhook with event: {event}")
        await self.bot_handler.start(event=event)