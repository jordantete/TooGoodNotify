import pytest, asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from telegram import Update, Message, Chat, User, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from app.core.telegram_bot_handler import TelegramBotHandler, CALLBACK_DATA_HELP, DEFAULT_LANGUAGE
from app.services.tgtg_service.exceptions import TgtgLoginError

class TestTelegramBotHandler:
    @pytest.fixture
    def telegram_bot_handler(self, mock_monitoring_service):
        with patch('telegram.ext.ApplicationBuilder.build', return_value=MagicMock()):
            handler = TelegramBotHandler(tgtg_service_monitor=mock_monitoring_service)
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

        help_text = telegram_bot_handler._get_localized_text('help-message')
        assert '/help' in help_text
        assert '/start' in help_text
    
    @pytest.mark.asyncio
    async def test_notifications_start_handler(self, telegram_bot_handler, mock_update, mock_context):
        await telegram_bot_handler._notifications_start_handler(mock_update, mock_context)
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=mock_update.effective_chat.id,
            text=telegram_bot_handler._get_localized_text("notifications-start"),
            parse_mode=ParseMode.HTML
        )

    @pytest.mark.asyncio
    async def test_notifications_stop_handler(self, telegram_bot_handler, mock_update, mock_context):
        await telegram_bot_handler._notifications_stop_handler(mock_update, mock_context)
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=mock_update.effective_chat.id,
            text=telegram_bot_handler._get_localized_text("notifications-stop"),
            parse_mode=ParseMode.HTML
        )

    @pytest.mark.asyncio
    async def test_about_handler(self, telegram_bot_handler, mock_update, mock_context):
        await telegram_bot_handler._about_handler(mock_update, mock_context)
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=mock_update.effective_chat.id,
            text=telegram_bot_handler._get_localized_text("about-message"),
            parse_mode=ParseMode.HTML        
        )

    @pytest.mark.asyncio
    async def test_language_handler_show_selection(self, telegram_bot_handler, mock_update, mock_context):
        mock_update.callback_query = None
        await telegram_bot_handler._language_handler(mock_update, mock_context)
        mock_context.bot.send_message.assert_called_once()
        call_args = mock_context.bot.send_message.call_args[1]

        localized_text = telegram_bot_handler._get_localized_text("language-selection")
        assert localized_text in call_args['text']
        assert isinstance(call_args['reply_markup'], InlineKeyboardMarkup)
        buttons = call_args['reply_markup'].inline_keyboard[0]
        button_texts = [button.text for button in buttons]
        expected_texts = ["🇬🇧 English", "🇫🇷 Français"]
        assert all(expected in button_texts for expected in expected_texts), f"Expected {expected_texts}, got {button_texts}"

    @pytest.mark.asyncio
    async def test_language_handler_process_callback(self, telegram_bot_handler, mock_update, mock_context):
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.data = "language_settings"
        await telegram_bot_handler._language_handler(mock_update, mock_context)
        mock_context.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_query_handler_help(self, telegram_bot_handler, mock_update, mock_context):
        mock_update.callback_query = AsyncMock()
        mock_update.callback_query.data = CALLBACK_DATA_HELP

        await telegram_bot_handler._callback_query_handler(mock_update, mock_context)

        mock_update.callback_query.answer.assert_called_once()

        mock_context.bot.send_message.assert_called_once()
        call_args = mock_context.bot.send_message.call_args[1]
        assert call_args['chat_id'] == mock_update.effective_chat.id

        localized_help_text = telegram_bot_handler._get_localized_text("help-message")
        assert localized_help_text == call_args['text']

    @pytest.mark.asyncio
    async def test_callback_query_handler_unhandled(self, telegram_bot_handler, mock_update, mock_context):
        mock_update.callback_query = AsyncMock()
        mock_update.callback_query.data = "unhandled_callback"

        await telegram_bot_handler._callback_query_handler(mock_update, mock_context)

        mock_update.callback_query.answer.assert_called_once()
        localized_unhandled_text = telegram_bot_handler._get_localized_text("unhandled-action")
        mock_context.bot.send_message.assert_called_once_with(chat_id=mock_update.callback_query.message.chat_id, text=localized_unhandled_text, parse_mode=ParseMode.HTML)

    @pytest.mark.asyncio
    async def test_register_account_handler_success(self, telegram_bot_handler, mock_update, mock_context):
        telegram_bot_handler.tgtg_service_monitor.request_new_tgtg_credentials.return_value = "PENDING"
        telegram_bot_handler.tgtg_service_monitor.check_credentials_ready.return_value = True
        
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.access_token = "new_access_token"
        mock_tgtg_service.refresh_token = "new_refresh_token"
        mock_tgtg_service.user_id = "new_user_id"
        mock_tgtg_service.cookie = "new_cookie"
        telegram_bot_handler.tgtg_service_monitor.tgtg_service = mock_tgtg_service
        
        await telegram_bot_handler._register_account_handler(mock_update, mock_context)
        
        assert mock_context.bot.send_message.call_count >= 2
        success_message = telegram_bot_handler._get_localized_text('register-success')
        assert any(call[1]['text'] == success_message for call in mock_context.bot.send_message.call_args_list)

    @pytest.mark.asyncio
    async def test_register_account_handler_failure(self, telegram_bot_handler, mock_update, mock_context):
        telegram_bot_handler.tgtg_service_monitor.request_new_tgtg_credentials.return_value = "FAILED"
        
        await telegram_bot_handler._register_account_handler(mock_update, mock_context)
        
        mock_context.bot.send_message.assert_called_once()
        failure_message = telegram_bot_handler._get_localized_text('register-failed')
        assert mock_context.bot.send_message.call_args[1]['text'] == failure_message

    def test_get_localized_text(self, telegram_bot_handler):
        text = telegram_bot_handler._get_localized_text('start-message')
        assert isinstance(text, str)
        assert len(text) > 0 

    @pytest.mark.asyncio
    async def test_register_account_handler_complete_flow(self, telegram_bot_handler, mock_update, mock_context):
        telegram_bot_handler.tgtg_service_monitor.request_new_tgtg_credentials.return_value = "PENDING"
        telegram_bot_handler.tgtg_service_monitor.check_credentials_ready.side_effect = [False, False, True]
        telegram_bot_handler.tgtg_service_monitor.tgtg_service = MagicMock()
        telegram_bot_handler.tgtg_service_monitor.tgtg_service.access_token = "new_access_token"
        telegram_bot_handler.tgtg_service_monitor.tgtg_service.refresh_token = "new_refresh_token"
        telegram_bot_handler.tgtg_service_monitor.tgtg_service.user_id = "new_user_id"
        telegram_bot_handler.tgtg_service_monitor.tgtg_service.cookie = "new_cookie"

        await telegram_bot_handler._register_account_handler(mock_update, mock_context)

        assert telegram_bot_handler.tgtg_service_monitor.request_new_tgtg_credentials.called
        assert telegram_bot_handler.tgtg_service_monitor.check_credentials_ready.call_count == 3
        assert telegram_bot_handler.tgtg_service_monitor.update_lambda_env_vars.called

        messages_sent = [call[1]['text'] for call in mock_context.bot.send_message.call_args_list]
        assert telegram_bot_handler._get_localized_text('register-pending') in messages_sent
        assert telegram_bot_handler._get_localized_text('register-success') in messages_sent

    @pytest.mark.asyncio
    async def test_register_account_handler_timeout(self, telegram_bot_handler, mock_update, mock_context):
        telegram_bot_handler.tgtg_service_monitor._retrieve_and_login.return_value = "PENDING"
        telegram_bot_handler.tgtg_service_monitor.check_credentials_ready.return_value = False

        original_sleep = asyncio.sleep
        
        async def mock_sleep(seconds):
            await original_sleep(0)  # Use minimal delay for tests
        
        with patch('asyncio.sleep', mock_sleep):
            await telegram_bot_handler._register_account_handler(mock_update, mock_context)

        # Verify timeout message
        timeout_message = telegram_bot_handler._get_localized_text('register-timeout')
        assert any(call[1]['text'] == timeout_message for call in mock_context.bot.send_message.call_args_list)

    @pytest.mark.asyncio
    async def test_register_account_handler_login_error(self, telegram_bot_handler, mock_update, mock_context):
        with patch.object(telegram_bot_handler.tgtg_service_monitor, '_retrieve_and_login', side_effect=TgtgLoginError("Login failed")):
            await telegram_bot_handler._register_account_handler(mock_update, mock_context)

            error_message = telegram_bot_handler._get_localized_text('register-error')

            mock_context.bot.send_message.assert_called_with(
                chat_id=mock_update.effective_chat.id,
                text=error_message,
                parse_mode=ParseMode.HTML
            )

    @pytest.mark.asyncio
    async def test_register_account_handler_credential_update(self, telegram_bot_handler, mock_update, mock_context):
        telegram_bot_handler.tgtg_service_monitor._retrieve_and_login.return_value = "PENDING"
        telegram_bot_handler.tgtg_service_monitor.check_credentials_ready.return_value = True
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.access_token = "new_access_token"
        mock_tgtg_service.refresh_token = "new_refresh_token"
        mock_tgtg_service.user_id = "new_user_id"
        mock_tgtg_service.cookie = "new_cookie"
        telegram_bot_handler.tgtg_service_monitor.tgtg_service = mock_tgtg_service

        await telegram_bot_handler._register_account_handler(mock_update, mock_context)

        expected_credentials = {
            "ACCESS_TOKEN": "new_access_token",
            "REFRESH_TOKEN": "new_refresh_token",
            "USER_ID": "new_user_id",
            "TGTG_COOKIE": "new_cookie"
        }

        telegram_bot_handler.tgtg_service_monitor.update_lambda_env_vars.assert_called_once_with(telegram_bot_handler.lambda_arn, expected_credentials)

        success_message = telegram_bot_handler._get_localized_text('register-success')
        assert any(call[1]['text'] == success_message for call in mock_context.bot.send_message.call_args_list)
    
    def test_get_localized_text(self, telegram_bot_handler):
        text = telegram_bot_handler._get_localized_text('start-message')
        assert isinstance(text, str)
        assert len(text) > 0

    def test_load_user_language(self, telegram_bot_handler):
        language = telegram_bot_handler._load_user_language()
        assert language == DEFAULT_LANGUAGE