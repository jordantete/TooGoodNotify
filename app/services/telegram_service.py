from app.core.telegram_bot_handler import TelegramBotHandler
from app.core.scheduler import Scheduler
from app.common.logger import LOGGER

class TelegramService:
    def __init__(
        self, 
        scheduler: Scheduler
    ):
        self.bot_handler = TelegramBotHandler(scheduler)

    async def process_webhook(self, event):
        LOGGER.info(f"Processing Telegram webhook with event: {event}")
        await self.bot_handler.start(event=event)