import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.handlers import tgtg_monitoring_handler, lambda_scheduler, run_telegram_webhook

class TestHandlers:
    @pytest.fixture
    def mock_event(self):
        return {
            'resources': [
                'arn:aws:events:eu-west-3:123456789012:rule/TooGoodToGo_monitoring_invocation_rule_123'
            ]
        }

    @pytest.fixture
    def mock_context(self):
        return MagicMock()

    def test_tgtg_monitoring_handler_valid_event(self, mock_event, mock_context):
        with patch('app.handlers.Scheduler') as mock_scheduler, patch('app.handlers.TgtgServiceMonitor') as mock_monitoring_service:
            
            mock_monitoring_instance = mock_monitoring_service.return_value
            tgtg_monitoring_handler(mock_event, mock_context)
            
            mock_scheduler.assert_called_once()
            mock_monitoring_service.assert_called_once()
            mock_monitoring_instance.start_monitoring.assert_called_once()

    def test_tgtg_monitoring_handler_invalid_event(self, mock_context):
        invalid_event = {'resources': ['some-other-resource']}
        
        with patch('app.handlers.Scheduler') as mock_scheduler, patch('app.handlers.TgtgServiceMonitor') as mock_monitoring_service:
            
            tgtg_monitoring_handler(invalid_event, mock_context)
            
            mock_scheduler.assert_not_called()
            mock_monitoring_service.assert_not_called()

    def test_lambda_scheduler(self, mock_event, mock_context):
        with patch('app.handlers.Scheduler') as mock_scheduler:
            mock_scheduler_instance = mock_scheduler.return_value
            
            lambda_scheduler(mock_event, mock_context)
            
            mock_scheduler.assert_called_once()
            mock_scheduler_instance.schedule_next_invocation.assert_called_once()

    @pytest.mark.asyncio
    async def test_telegram_webhook_handler(self):
        test_event = {'body': '{"message": {"text": "/start", "chat": {"id": 123456789}}}'}
        
        with patch('app.handlers.TelegramService') as mock_telegram_service, patch('app.handlers.Scheduler'), patch('app.handlers.TgtgServiceMonitor'):
            mock_telegram_instance = mock_telegram_service.return_value
            mock_telegram_instance.process_webhook = AsyncMock()
            
            response = await run_telegram_webhook(test_event, None)
            
            assert response['statusCode'] == 200
            mock_telegram_instance.process_webhook.assert_called_once_with(test_event)

    @pytest.mark.asyncio
    async def test_telegram_webhook_handler_error(self):
        test_event = {'body': '{"message": {"text": "/start", "chat": {"id": 123456789}}}'}
        
        with patch('app.handlers.TelegramService') as mock_telegram_service, patch('app.handlers.Scheduler'), patch('app.handlers.TgtgServiceMonitor'):
            mock_telegram_instance = mock_telegram_service.return_value
            mock_telegram_instance.process_webhook = AsyncMock(side_effect=Exception("Test error"))
            
            response = await run_telegram_webhook(test_event, None)
            
            assert response['statusCode'] == 400
            assert "Oops" in response['body'] 