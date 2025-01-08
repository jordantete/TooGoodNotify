import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.telegram_service import TelegramService
from app.services.monitoring_tgtg_service import MonitoringTgtgService

class TestTelegramService:
    @pytest.fixture
    def mock_monitoring_service(self):
        return MagicMock(spec=MonitoringTgtgService)

    @pytest.fixture
    def telegram_service(self, mock_monitoring_service):
        return TelegramService(monitoring_service=mock_monitoring_service)

    @patch("app.services.telegram_service.TelegramBotHandler")
    @pytest.mark.asyncio
    async def test_process_webhook_success(self, mock_bot_handler, mock_monitoring_service):
        mock_handler_instance = AsyncMock()
        mock_bot_handler.return_value = mock_handler_instance

        service = TelegramService(monitoring_service=mock_monitoring_service)
        test_event = {"update_id": 123456, "message": {"text": "/start"}}

        await service.process_webhook(test_event)

        mock_bot_handler.assert_called_once_with(mock_monitoring_service)
        mock_handler_instance.start.assert_awaited_once_with(event=test_event)
