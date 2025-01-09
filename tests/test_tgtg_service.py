import pytest, pytz
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.services.tgtg_service.tgtg_service import TgtgService
from app.services.tgtg_service.exceptions import TgtgLoginError, TgtgAPIConnectionError, TgtgAPIParsingError, ForbiddenError
from app.services.tgtg_service.models import ItemDetails

class TestTgtgService:
    @pytest.fixture
    def tgtg_service(self):
        return TgtgService()

    def test_init(self, tgtg_service):
        assert tgtg_service.credentials == {}

    def test_retrieve_credentials_success(self, tgtg_service):
        with patch("app.services.tgtg_service.tgtg_service.TgtgClient") as mock_tgtg:
            mock_client = MagicMock()
            mock_client.get_credentials.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "user_id": "new_user_id",
                "cookie": "new_cookie",
            }
            mock_tgtg.return_value = mock_client

            tgtg_service.retrieve_credentials(email="test@example.com")

            assert tgtg_service.credentials["access_token"] == "new_access_token"
            assert tgtg_service.credentials["refresh_token"] == "new_refresh_token"
            assert tgtg_service.credentials["user_id"] == "new_user_id"
            assert tgtg_service.credentials["cookie"] == "new_cookie"

    def test_retrieve_credentials_failure(self, tgtg_service):
        with patch("tgtg.TgtgClient", side_effect=Exception("API error")):
            with pytest.raises(TgtgLoginError):
                tgtg_service.retrieve_credentials(email="test@example.com")

    def test_get_favorites_items_success(self, tgtg_service, mock_item_details):
        with patch('app.services.tgtg_service.tgtg_service.TgtgClient') as mock_tgtg_client:
            mock_instance = MagicMock()
            mock_instance.get_credentials.return_value = {
                "access_token": "access_token", 
                "refresh_token": "refresh_token", 
                "user_id": "user_id", 
                "cookie": "cookie"
            }
            
            mock_instance.get_favorites.return_value = [mock_item_details.dict()]
            mock_tgtg_client.return_value = mock_instance
            items = tgtg_service.get_favorites_items_list("access_token", "refresh_token", "cookie")

            assert len(items) == 1
            assert isinstance(items[0], ItemDetails)
            assert items[0].items_available == 2

    def test_get_favorites_items_validation_error(self, tgtg_service, mock_tgtg_client):
        with patch('app.services.tgtg_service.tgtg_service.TgtgClient') as mock_tgtg_client_class:
            mock_instance = MagicMock()
            mock_instance.get_favorites.return_value = [{"invalid_key": "value"}]
            mock_tgtg_client_class.return_value = mock_instance
            
            with pytest.raises(TgtgAPIParsingError):
                tgtg_service.get_favorites_items_list("access_token", "refresh_token", "cookie")

    def test_get_favorites_items_forbidden_error(self, tgtg_service, mock_tgtg_client):
        with patch('app.services.tgtg_service.tgtg_service.TgtgClient') as mock_tgtg_client_class:
            mock_instance = MagicMock()
            mock_instance.get_favorites.side_effect = Exception("captcha required")
            mock_tgtg_client_class.return_value = mock_instance
            
            with pytest.raises(ForbiddenError):
                tgtg_service.get_favorites_items_list("access_token", "refresh_token", "cookie")

    def test_get_favorites_items_unexpected_error(self, tgtg_service, mock_tgtg_client):
        mock_tgtg_client.get_favorites.side_effect = Exception("Unexpected error")
        tgtg_service.tgtg_client = mock_tgtg_client

        with pytest.raises(TgtgAPIConnectionError):
            tgtg_service.get_favorites_items_list("access_token", "refresh_token", "cookie")

    def test_get_notification_messages(self, tgtg_service, mock_item_details):
        mock_db_instance = MagicMock()
        tgtg_service.database_handler = mock_db_instance
        mock_db_instance.get_items.return_value = []  # Simulate no notifications in the database

        messages = tgtg_service.get_notification_messages([mock_item_details])

        assert len(messages) == 1
        assert "Test Store" in messages[0]

    def test_is_notification_sent_today(self, tgtg_service):
        today_date = datetime.now(pytz.UTC).date()
        notifications = [{"lastNotificationDate": today_date.isoformat()}]

        assert tgtg_service._is_notification_sent_today(notifications) is True

        notifications = [{"lastNotificationDate": "2023-01-01T00:00:00Z"}]
        assert tgtg_service._is_notification_sent_today(notifications) is False