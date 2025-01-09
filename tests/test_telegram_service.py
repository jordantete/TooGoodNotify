import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.telegram_service import TelegramService
from app.services.tgtg_service_monitor import TgtgServiceMonitor

class TestTelegramService:
    @pytest.fixture
    def mock_monitoring_service(self):
        return MagicMock(spec=TgtgServiceMonitor)

    @pytest.fixture
    def telegram_service(self, mock_monitoring_service):
        return TelegramService(tgtg_service_monitor=mock_monitoring_service)

    @patch("app.services.telegram_service.TelegramBotHandler")
    @pytest.mark.asyncio
    async def test_process_webhook_success(self, mock_bot_handler, mock_monitoring_service):
        mock_handler_instance = AsyncMock()
        mock_bot_handler.return_value = mock_handler_instance

        service = TelegramService(tgtg_service_monitor=mock_monitoring_service)
        test_event = {"update_id": 123456, "message": {"text": "/start"}}

        await service.process_webhook(test_event)

        mock_bot_handler.assert_called_once_with(mock_monitoring_service)
        mock_handler_instance.start.assert_awaited_once_with(event=test_event)
