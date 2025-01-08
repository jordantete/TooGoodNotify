import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from telegram import Update, Message, Chat, User, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes
from app.core.telegram_bot_handler import TelegramBotHandler
from app.services.monitoring_tgtg_service import MonitoringTgtgService
import asyncio
from app.services.tgtg_service.exceptions import TgtgLoginError

class TestTelegramBotHandler:
    @pytest.fixture
    def telegram_bot_handler(self, mock_monitoring_service, test_environment):
        with patch('telegram.ext.ApplicationBuilder.build', return_value=MagicMock()):
            handler = TelegramBotHandler(monitoring_service=mock_monitoring_service)
            handler.application.bot = AsyncMock()
            return handler

    @pytest.fixture
    def mock_update(self):
        update = MagicMock(spec=Update)
        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = 123456789
        update.message = MagicMock(spec=Message)
        update.message.from_user = MagicMock(spec=User)
        update.message.from_user.id = 123456789
        return update

    @pytest.fixture
    def mock_context(self):
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_start_handler(self, telegram_bot_handler, mock_update, mock_context):
        await telegram_bot_handler._start_handler(mock_update, mock_context)
        
        mock_context.bot.send_message.assert_called_once()
        call_args = mock_context.bot.send_message.call_args[1]
        assert call_args['chat_id'] == mock_update.effective_chat.id
        assert isinstance(call_args['reply_markup'], InlineKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_help_handler(self, telegram_bot_handler, mock_update, mock_context):
        await telegram_bot_handler._help_handler(mock_update, mock_context)
        
        mock_context.bot.send_message.assert_called_once()
        call_args = mock_context.bot.send_message.call_args[1]
        assert call_args['chat_id'] == mock_update.effective_chat.id
        # Check for command presence instead of exact message
        help_text = telegram_bot_handler._get_localized_text('help-message')
        assert '/help' in help_text
        assert '/start' in help_text

    @pytest.mark.asyncio
    async def test_register_account_handler_success(self, telegram_bot_handler, mock_update, mock_context):
        # Mock successful registration
        telegram_bot_handler.monitoring_service._retrieve_and_login.return_value = "PENDING"
        telegram_bot_handler.monitoring_service.check_credentials_ready.return_value = True
        
        # Create a mock tgtg_service
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.access_token = "new_access_token"
        mock_tgtg_service.refresh_token = "new_refresh_token"
        mock_tgtg_service.user_id = "new_user_id"
        mock_tgtg_service.cookie = "new_cookie"
        telegram_bot_handler.monitoring_service.tgtg_service = mock_tgtg_service
        
        await telegram_bot_handler._register_account_handler(mock_update, mock_context)
        
        assert mock_context.bot.send_message.call_count >= 2
        success_message = telegram_bot_handler._get_localized_text('register-success')
        assert any(
            call[1]['text'] == success_message 
            for call in mock_context.bot.send_message.call_args_list
        )

    @pytest.mark.asyncio
    async def test_register_account_handler_failure(self, telegram_bot_handler, mock_update, mock_context):
        # Mock failed registration
        telegram_bot_handler.monitoring_service._retrieve_and_login.return_value = "FAILED"
        
        await telegram_bot_handler._register_account_handler(mock_update, mock_context)
        
        mock_context.bot.send_message.assert_called_once()
        failure_message = telegram_bot_handler._get_localized_text('register-failed')
        assert mock_context.bot.send_message.call_args[1]['text'] == failure_message

    @pytest.mark.asyncio
    async def test_status_handler(self, telegram_bot_handler, mock_update, mock_context):
        await telegram_bot_handler._status_handler(mock_update, mock_context)
        
        mock_context.bot.send_message.assert_called_once()
        call_args = mock_context.bot.send_message.call_args[1]
        assert call_args['chat_id'] == mock_update.effective_chat.id
        assert 'test@example.com' in call_args['text']

    def test_get_localized_text(self, telegram_bot_handler):
        text = telegram_bot_handler._get_localized_text('start-message')
        assert isinstance(text, str)
        assert len(text) > 0 

    @pytest.mark.asyncio
    async def test_register_account_handler_complete_flow(self, telegram_bot_handler, mock_update, mock_context):
        """Test the complete registration flow with credential refresh and update."""
        # Mock the monitoring service methods
        telegram_bot_handler.monitoring_service._retrieve_and_login.return_value = "PENDING"
        telegram_bot_handler.monitoring_service.check_credentials_ready.side_effect = [False, False, True]
        telegram_bot_handler.monitoring_service.tgtg_service = MagicMock()
        telegram_bot_handler.monitoring_service.tgtg_service.access_token = "new_access_token"
        telegram_bot_handler.monitoring_service.tgtg_service.refresh_token = "new_refresh_token"
        telegram_bot_handler.monitoring_service.tgtg_service.user_id = "new_user_id"
        telegram_bot_handler.monitoring_service.tgtg_service.cookie = "new_cookie"

        # Execute registration handler
        await telegram_bot_handler._register_account_handler(mock_update, mock_context)

        # Verify the flow
        assert telegram_bot_handler.monitoring_service._retrieve_and_login.called
        assert telegram_bot_handler.monitoring_service.check_credentials_ready.call_count == 3
        assert telegram_bot_handler.monitoring_service.update_lambda_env_vars.called

        # Verify messages sent
        messages_sent = [call[1]['text'] for call in mock_context.bot.send_message.call_args_list]
        assert telegram_bot_handler._get_localized_text('register-pending') in messages_sent
        assert telegram_bot_handler._get_localized_text('register-success') in messages_sent

    @pytest.mark.asyncio
    async def test_register_account_handler_timeout(self, telegram_bot_handler, mock_update, mock_context):
        """Test registration timeout when credentials are not ready."""
        # Mock the monitoring service to simulate timeout
        telegram_bot_handler.monitoring_service._retrieve_and_login.return_value = "PENDING"
        telegram_bot_handler.monitoring_service.check_credentials_ready.return_value = False

        # Reduce timeout for testing
        original_sleep = asyncio.sleep
        
        async def mock_sleep(seconds):
            await original_sleep(0)  # Use minimal delay for tests
        
        with patch('asyncio.sleep', mock_sleep):
            await telegram_bot_handler._register_account_handler(mock_update, mock_context)

        # Verify timeout message
        timeout_message = telegram_bot_handler._get_localized_text('register-timeout')
        assert any(
            call[1]['text'] == timeout_message 
            for call in mock_context.bot.send_message.call_args_list
        )

    @pytest.mark.asyncio
    async def test_register_account_handler_login_error(self, telegram_bot_handler, mock_update, mock_context):
        """Test handling of login errors during registration."""
        # Mock the monitoring service to raise an error
        telegram_bot_handler.monitoring_service._retrieve_and_login.side_effect = TgtgLoginError("Login failed")

        await telegram_bot_handler._register_account_handler(mock_update, mock_context)

        # Verify error message
        error_message = telegram_bot_handler._get_localized_text('register-error')
        mock_context.bot.send_message.assert_called_with(
            chat_id=mock_update.effective_chat.id,
            text=error_message
        )

    @pytest.mark.asyncio
    async def test_register_account_handler_credential_update(self, telegram_bot_handler, mock_update, mock_context):
        """Test successful credential update after registration."""
        # Mock successful registration flow
        telegram_bot_handler.monitoring_service._retrieve_and_login.return_value = "PENDING"
        telegram_bot_handler.monitoring_service.check_credentials_ready.return_value = True
        
        # Create a real mock for tgtg_service with actual attributes
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.access_token = "new_access_token"
        mock_tgtg_service.refresh_token = "new_refresh_token"
        mock_tgtg_service.user_id = "new_user_id"
        mock_tgtg_service.cookie = "new_cookie"
        
        telegram_bot_handler.monitoring_service.tgtg_service = mock_tgtg_service

        await telegram_bot_handler._register_account_handler(mock_update, mock_context)

        # Verify credential update with the exact dictionary
        expected_credentials = {
            "ACCESS_TOKEN": "new_access_token",
            "REFRESH_TOKEN": "new_refresh_token",
            "USER_ID": "new_user_id",
            "TGTG_COOKIE": "new_cookie"
        }
        telegram_bot_handler.monitoring_service.update_lambda_env_vars.assert_called_once_with(expected_credentials)

        # Verify success message
        success_message = telegram_bot_handler._get_localized_text('register-success')
        assert any(
            call[1]['text'] == success_message 
            for call in mock_context.bot.send_message.call_args_list
        ) 