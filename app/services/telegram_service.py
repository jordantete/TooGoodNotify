from app.core.telegram_bot_handler import TelegramBotHandler
from app.services.monitoring_tgtg_service import MonitoringTgtgService
from app.common.logger import LOGGER

class TelegramService:
    def __init__(
        self, 
        monitoring_service: MonitoringTgtgService
    ):
        self.bot_handler = TelegramBotHandler(monitoring_service)

    async def process_webhook(self, event):
        LOGGER.info(f"Processing Telegram webhook with event: {event}")
        await self.bot_handler.start(event=event)