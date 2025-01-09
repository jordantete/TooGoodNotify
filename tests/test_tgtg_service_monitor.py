import pytest
from unittest.mock import patch, MagicMock
from app.services.tgtg_service_monitor import TgtgServiceMonitor
from app.services.tgtg_service.exceptions import TgtgAPIConnectionError, TgtgAPIParsingError, TgtgLoginError, ForbiddenError

class TestTgtgServiceMonitor:
    @pytest.fixture
    def monitoring_service(self, test_environment):
        return TgtgServiceMonitor()

    def test_init(self, monitoring_service, test_environment):
        assert monitoring_service.lambda_arn == test_environment["LAMBDA_MONITORING_ARN"]
        assert monitoring_service.user_email == test_environment["USER_EMAIL"]
        assert monitoring_service.access_token == test_environment["ACCESS_TOKEN"]

    def test_start_monitoring_success(self, monitoring_service, mock_scheduler):
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.get_favorites_items.return_value = []

        with patch.object(monitoring_service, '_get_tgtg_service_logged_in_instance', return_value=mock_tgtg_service):
            monitoring_service.start_monitoring(mock_scheduler)

            mock_tgtg_service.get_favorites_items.assert_called_once()

            with patch.object(monitoring_service, '_monitor_favorites') as mock_monitor_favorites:
                monitoring_service.start_monitoring(mock_scheduler)
                mock_monitor_favorites.assert_called_once_with(mock_tgtg_service, mock_scheduler)

    def test_start_monitoring_no_credentials(self, monitoring_service, mock_scheduler):
        with patch.object(monitoring_service, '_get_tgtg_service_logged_in_instance', return_value=None), patch("app.common.logger.LOGGER.error") as mock_logger:
            monitoring_service.start_monitoring(mock_scheduler)

            mock_logger.assert_called_once_with("Missing or invalid credentials. Please ensure that all your environment variables are set correctly.")

    def test_get_tgtg_service_logged_in_instance_success(self, monitoring_service):
        with patch("app.services.tgtg_service_monitor.TgtgService") as mock_tgtg_service:
            mock_instance = mock_tgtg_service.return_value
            mock_instance.login.return_value = None  # Mock login behavior
            result = monitoring_service._get_tgtg_service_logged_in_instance()
            assert result == mock_instance
            mock_tgtg_service.assert_called_once_with(
                monitoring_service.user_email,
                monitoring_service.access_token,
                monitoring_service.refresh_token,
                monitoring_service.user_id,
                monitoring_service.tgtg_cookie
            )
    
    def test_retrieve_tgtg_credentials_success(self, monitoring_service):
        with patch("app.services.tgtg_service_monitor.TgtgService") as mock_tgtg_service:
            mock_instance = mock_tgtg_service.return_value
            mock_instance.retrieve_credentials.return_value = None
            result = monitoring_service.request_new_tgtg_credentials()
            assert result == "PENDING"

    def test_retrieve_tgtg_credentials_failure(self, monitoring_service):
        with patch("app.services.tgtg_service_monitor.TgtgService") as mock_tgtg_service, \
            patch("app.common.logger.LOGGER.error") as mock_logger:
            mock_instance = mock_tgtg_service.return_value
            mock_instance.retrieve_credentials.side_effect = TgtgLoginError("Credential retrieval failed")
            result = monitoring_service.request_new_tgtg_credentials()
            assert result == "FAILED"
            mock_logger.assert_called_once_with("Failed to retrieve new credential: TgtgLoginError: Credential retrieval failed")

    def test_get_tgtg_service_instance_missing_credentials(self, monitoring_service):
        monitoring_service.access_token = None
        result = monitoring_service._get_tgtg_service_logged_in_instance()
        assert result is None

    def test_get_tgtg_service_instance_login_failure(self, monitoring_service):
        with patch("app.services.tgtg_service_monitor.TgtgService") as mock_tgtg_service, patch("app.common.logger.LOGGER.error") as mock_logger:
            mock_instance = mock_tgtg_service.return_value
            mock_instance.login.side_effect = TgtgLoginError("Login failed")
            result = monitoring_service._get_tgtg_service_logged_in_instance()

            assert result is None
            mock_logger.assert_called_once_with("Failed to login to TGTG API: TgtgLoginError: Login failed")

    def test_monitor_favorites_success(self, monitoring_service, mock_scheduler):
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.get_favorites_items.return_value = []
        monitoring_service.tgtg_service = mock_tgtg_service
        
        with patch.object(monitoring_service, '_get_tgtg_service_logged_in_instance', return_value=mock_tgtg_service):
            monitoring_service.start_monitoring(mock_scheduler)
        
            mock_tgtg_service.get_favorites_items.assert_called_once()

    def test_monitor_favorites_parsing_error(self, monitoring_service, mock_scheduler):
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.get_favorites_items.side_effect = TgtgAPIParsingError("Parsing error")
        monitoring_service.tgtg_service = mock_tgtg_service

        with patch("app.common.utils.Utils.send_telegram_message") as mock_send_message, patch("app.common.logger.LOGGER.error") as mock_logger:
            with patch.object(monitoring_service, '_get_tgtg_service_logged_in_instance', return_value=mock_tgtg_service):
                monitoring_service.start_monitoring(mock_scheduler)

            mock_logger.assert_called_once_with("TgtgAPIParsingError encountered: TgtgAPIParsingError: Parsing error")
            mock_send_message.assert_called_once()

    def test_monitor_favorites_forbidden_error(self, monitoring_service, mock_scheduler):
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.get_favorites_items.side_effect = ForbiddenError("Forbidden")
        monitoring_service.tgtg_service = mock_tgtg_service

        with patch("app.common.utils.Utils.send_telegram_message") as mock_send_message, patch.object(mock_scheduler, "activate_cooldown") as mock_activate_cooldown:
            with patch.object(monitoring_service, '_get_tgtg_service_logged_in_instance', return_value=mock_tgtg_service):
                monitoring_service.start_monitoring(mock_scheduler)
            
            mock_activate_cooldown.assert_called_once()
            mock_send_message.assert_called_once_with("API access forbidden. Monitoring paused temporarily.")

    def test_monitor_favorites_connection_error(self, monitoring_service, mock_scheduler):
        mock_tgtg_service = MagicMock()
        mock_tgtg_service.get_favorites_items.side_effect = TgtgAPIConnectionError("Connection error")
        monitoring_service.tgtg_service = mock_tgtg_service

        with patch("app.common.utils.Utils.send_telegram_message") as mock_send_message, patch("app.common.logger.LOGGER.error") as mock_logger:
            with patch.object(monitoring_service, '_get_tgtg_service_logged_in_instance', return_value=mock_tgtg_service):
                monitoring_service.start_monitoring(mock_scheduler)
            
            mock_logger.assert_called_once_with("Connection error to TGTG API. TgtgAPIConnectionError: Connection error")
            mock_send_message.assert_called_once_with("TGTG API connection error: TgtgAPIConnectionError: Connection error")

    def test_update_lambda_env_vars(self, monitoring_service):
        new_env_vars = {
            "ACCESS_TOKEN": "new_token",
            "REFRESH_TOKEN": "new_refresh_token"
        }

        mock_lambda_client = MagicMock()
        mock_lambda_client.get_function_configuration.return_value = {'Environment': {'Variables': {'EXISTING_VAR': 'value'}}}

        monitoring_service.lambda_client = mock_lambda_client
        monitoring_service.update_lambda_env_vars(new_env_vars)

        mock_lambda_client.update_function_configuration.assert_called_once()
        called_args = mock_lambda_client.update_function_configuration.call_args[1]
        assert "new_token" in str(called_args)

    def test_update_lambda_env_vars_failure(self, monitoring_service):
        new_env_vars = {
            "ACCESS_TOKEN": "new_token",
            "REFRESH_TOKEN": "new_refresh_token"
        }

        mock_lambda_client = MagicMock()
        mock_lambda_client.update_function_configuration.side_effect = Exception("Update failed")
        monitoring_service.lambda_client = mock_lambda_client

        with pytest.raises(Exception, match="Update failed"):
            monitoring_service.update_lambda_env_vars(new_env_vars)
    
    def test_check_credentials_ready_updated(self, monitoring_service):
        monitoring_service.tgtg_service = MagicMock()
        monitoring_service.tgtg_service.access_token = "new_token"
        monitoring_service.tgtg_service.refresh_token = "new_refresh"
        monitoring_service.tgtg_service.cookie = "new_cookie"

        with patch("app.common.utils.Utils.get_environment_variable", side_effect=["old_token", "old_refresh", "old_cookie"]):
            assert monitoring_service.check_credentials_ready() is True

    def test_check_credentials_ready_no_update(self, monitoring_service):
        monitoring_service.tgtg_service = MagicMock()
        monitoring_service.tgtg_service.access_token = "current_token"
        monitoring_service.tgtg_service.refresh_token = "current_refresh"
        monitoring_service.tgtg_service.cookie = "current_cookie"

        with patch("app.common.utils.Utils.get_environment_variable", side_effect=["current_token", "current_refresh", "current_cookie"]):
            assert monitoring_service.check_credentials_ready() is False