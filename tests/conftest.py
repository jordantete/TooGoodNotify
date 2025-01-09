import pytest
from unittest.mock import MagicMock
from app.core.scheduler import Scheduler
from app.services.tgtg_service_monitor import TgtgServiceMonitor
from app.services.tgtg_service.models import ItemDetails, Store, Item, PickupInterval, PickupLocation, PriceInfo, Picture, Address

@pytest.fixture
def mock_dynamodb_table():
    with MagicMock() as mock_table:
        mock_table.scan = MagicMock(return_value={'Items': []})
        mock_table.put_item = MagicMock()
        mock_table.delete_item = MagicMock()
        yield mock_table

@pytest.fixture
def mock_boto3_resource(mock_dynamodb_table):
    with MagicMock() as mock_resource:
        mock_resource.Table.return_value = mock_dynamodb_table
        return mock_resource

@pytest.fixture
def mock_tgtg_client():
    return MagicMock()

@pytest.fixture
def mock_scheduler():
    return MagicMock(spec=Scheduler)

@pytest.fixture
def mock_monitoring_service():
    mock_service = MagicMock(spec=TgtgServiceMonitor)
    # Add the required methods to the mock
    mock_service._retrieve_and_login = MagicMock()
    mock_service.check_credentials_ready = MagicMock()
    mock_service.update_lambda_env_vars = MagicMock()
    return mock_service

@pytest.fixture
def test_environment(monkeypatch):
    """Set up test environment variables."""
    env_vars = {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "123456789",
        "USER_EMAIL": "test@example.com",
        "ACCESS_TOKEN": "test_access_token",
        "REFRESH_TOKEN": "test_refresh_token",
        "USER_ID": "test_user_id",
        "TGTG_COOKIE": "test_cookie",
        "LAMBDA_MONITORING_ARN": "test_arn",
        "USER_AWS_ACCOUNT_ID": "123456789012"
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars 

@pytest.fixture
def mock_item_details():
    return ItemDetails(
        item=Item(
            item_id="456",
            item_price=PriceInfo(code="EUR", minor_units=599, decimals=2),
            item_value=PriceInfo(code="EUR", minor_units=1599, decimals=2),
            cover_picture=Picture(
                picture_id="test_item_cover",
                current_url="http://test.com/item_cover",
                is_automatically_created=False
            ),
            logo_picture=Picture(
                picture_id="test_item_logo",
                current_url="http://test.com/item_logo",
                is_automatically_created=False
            ),
            name="Test Item",
            description="Test Description"
        ),
        store=Store(
            store_id="123",
            store_name="Test Store",
            website=None,
            store_location=Address(
                address={
                    "address_line": "123 Test Street",
                    "latitude": 48.8566,
                    "longitude": 2.3522
                }
            ),
            logo_picture=Picture(
                picture_id="test_logo",
                current_url="http://test.com/logo",
                is_automatically_created=False
            ),
            cover_picture=Picture(
                picture_id="test_cover",
                current_url="http://test.com/cover",
                is_automatically_created=False
            ),
            store_time_zone="Europe/Paris"
        ),
        display_name="Test Item",
        items_available=2,
        distance=1.5,
        favorite=True,
        item_type="MAGIC_BAG",
        pickup_location=PickupLocation(
            address={"address_line": "123 Test Street"},
            location={"latitude": 48.8566, "longitude": 2.3522}
        ),
        pickup_interval=PickupInterval(
            start="2024-03-20T14:00:00Z",
            end="2024-03-20T18:00:00Z"
        )
    )