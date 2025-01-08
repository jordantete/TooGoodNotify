from freezegun import freeze_time
from app.services.tgtg_service.notification_formatter import NotificationFormatter
from app.services.tgtg_service.models import PickupInterval

class TestNotificationFormatter:
    @freeze_time("2024-03-20 12:00:00")
    def test_format_pickup_interval_today(self, mock_item_details):
        interval_str = NotificationFormatter.format_pickup_interval(
            mock_item_details.pickup_interval,
            mock_item_details.store.store_time_zone
        )
        assert "*Aujourd'hui*" in interval_str
        assert "15:00" in interval_str
        assert "19:00" in interval_str

    @freeze_time("2024-03-19 12:00:00")
    def test_format_pickup_interval_tomorrow(self, mock_item_details):
        interval_str = NotificationFormatter.format_pickup_interval(
            mock_item_details.pickup_interval,
            mock_item_details.store.store_time_zone
        )
        assert "*Demain*" in interval_str

    @freeze_time("2024-03-18 12:00:00")
    def test_format_pickup_interval_future_date(self, mock_item_details):
        interval_str = NotificationFormatter.format_pickup_interval(
            mock_item_details.pickup_interval,
            mock_item_details.store.store_time_zone
        )
        assert "20/03" in interval_str

    def test_format_pickup_interval_invalid_timezone(self, mock_item_details):
        mock_item_details.store.store_time_zone = "Invalid/Timezone"
        interval_str = NotificationFormatter.format_pickup_interval(
            mock_item_details.pickup_interval,
            mock_item_details.store.store_time_zone
        )
        assert interval_str == "Pickup time unavailable"

    def test_format_pickup_interval_missing_start_or_end(self):
        incomplete_interval = PickupInterval(start="", end="2024-03-20T18:00:00Z")
        interval_str = NotificationFormatter.format_pickup_interval(incomplete_interval, "Europe/Paris")
        assert interval_str == "Pickup time unavailable"

        incomplete_interval = PickupInterval(start="2024-03-20T14:00:00Z", end="")
        interval_str = NotificationFormatter.format_pickup_interval(incomplete_interval, "Europe/Paris")
        assert interval_str == "Pickup time unavailable"
    
    def test_format_pickup_interval_none_interval(self):
        interval_str = NotificationFormatter.format_pickup_interval(None, "Europe/Paris")
        assert interval_str == "Pickup time unavailable"

    def test_format_message_complete(self, mock_item_details):
        message = NotificationFormatter.format_message(mock_item_details)
        assert "Test Store" in message
        assert "2 nouveaux paniers disponibles" in message
        assert "Test Description" in message
        assert "5.99" in message
        assert "15.99" in message
        assert "123 Test Street" in message

    def test_format_message_missing_location(self, mock_item_details):
        mock_item_details.pickup_location = None
        message = NotificationFormatter.format_message(mock_item_details)
        assert "Unknown location" in message