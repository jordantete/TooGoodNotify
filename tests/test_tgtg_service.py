import pytest, pytz
from unittest.mock import patch, MagicMock
from app.services.tgtg_service.tgtg_service import TgtgService
from app.services.tgtg_service.exceptions import TgtgAPIParsingError, ForbiddenError
from app.services.tgtg_service.models import ItemDetails
from datetime import datetime

class TestTgtgService:
    @pytest.fixture
    def tgtg_service(self):
        return TgtgService()

    def test_init(self, tgtg_service):
        assert tgtg_service.credentials is None

    @patch('app.services.tgtg_service.tgtg_service.TgtgClient')
    def test_get_favorites_items_success(self, mock_tgtg_client, mock_item_details, tgtg_service):
        mock_instance = MagicMock()
        mock_instance.get_credentials.return_value = {
            "access_token": "access_token", 
            "refresh_token": "refresh_token", 
            "cookie": "cookie"
        }
        mock_instance.get_favorites.return_value = [mock_item_details.dict()]
        mock_tgtg_client.return_value = mock_instance

        items = tgtg_service.get_favorites_items_list(
            email="test@example.com",
            access_token="access_token",
            refresh_token="refresh_token",
            cookie="cookie",
            last_time_token_refreshed_str=None
        )

        assert len(items) == 1
        assert isinstance(items[0], ItemDetails)
        assert items[0].items_available == 2

    @patch('app.services.tgtg_service.tgtg_service.TgtgClient')
    def test_get_favorites_items_validation_error(self, mock_tgtg_client, tgtg_service):
        mock_instance = MagicMock()
        mock_instance.get_favorites.return_value = [{"invalid_key": "value"}]
        mock_tgtg_client.return_value = mock_instance

        with pytest.raises(TgtgAPIParsingError):
            tgtg_service.get_favorites_items_list(
                email="test@example.com",
                access_token="access_token",
                refresh_token="refresh_token",
                cookie="cookie",
                last_time_token_refreshed_str=None
            )

    @patch('app.services.tgtg_service.tgtg_service.TgtgClient')
    def test_get_favorites_items_forbidden_error(self, mock_tgtg_client, tgtg_service):
        mock_instance = MagicMock()
        mock_instance.get_favorites.side_effect = Exception("captcha required")
        mock_tgtg_client.return_value = mock_instance

        with pytest.raises(ForbiddenError):
            tgtg_service.get_favorites_items_list(
                email="test@example.com",
                access_token="access_token",
                refresh_token="refresh_token",
                cookie="cookie",
                last_time_token_refreshed_str=None
            )

    def test_get_notification_messages(self, tgtg_service, mock_item_details):
        mock_db_instance = MagicMock()
        tgtg_service.database_handler = mock_db_instance
        mock_db_instance.get_items.return_value = []

        messages = tgtg_service.get_notification_messages([mock_item_details])

        assert len(messages) == 1
        assert "Test Store" in messages[0]

    def test_is_notification_sent_today(self, tgtg_service):
        today_date = datetime.now(pytz.UTC).date()
        notifications = [{"lastNotificationDate": today_date.isoformat()}]

        assert tgtg_service._is_notification_sent_today(notifications) is True

        notifications = [{"lastNotificationDate": "2023-01-01T00:00:00Z"}]
        assert tgtg_service._is_notification_sent_today(notifications) is False