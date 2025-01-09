from app.core.telegram_bot_handler import TelegramBotHandler
from app.services.tgtg_service_monitor import TgtgServiceMonitor
from app.common.logger import LOGGER

class TelegramService:
    def __init__(
        self, 
        tgtg_service_monitor: TgtgServiceMonitor
    ):
        self.bot_handler = TelegramBotHandler(tgtg_service_monitor)

    async def process_webhook(self, event):
        LOGGER.info(f"Processing Telegram webhook with event: {event}")
        await self.bot_handler.start(event=event)