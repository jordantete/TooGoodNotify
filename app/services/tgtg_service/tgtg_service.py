import pytz
from pydantic import ValidationError
from datetime import datetime
from typing import Optional, List, Dict
from tgtg import TgtgClient
from app.common.logger import LOGGER
from app.core.database_handler import DatabaseHandler
from app.core.exceptions import DatabaseQueryError
from app.services.tgtg_service.notification_formatter import NotificationFormatter
from app.services.tgtg_service.models import ItemDetails
from app.services.tgtg_service.exceptions import TgtgLoginError, TgtgAPIConnectionError, TgtgAPIParsingError, ForbiddenError

class TgtgService:
    USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"

    def __init__(
        self, 
        email: Optional[str] = None, 
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None, 
        user_id: Optional[str] = None, 
        cookie: Optional[str] = None
    ):
        self.email = email
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.cookie = cookie
        self.database_handler = DatabaseHandler(table_name="UserNotifications")
        self.tgtg_client: Optional[TgtgClient] = None

    def login(self) -> None:
        """Initialize the TGTG client with credentials."""
        LOGGER.info(f"Login to TGTG API with user_id: {self.user_id}, using device: IPHONE")
        try:
            self.tgtg_client = TgtgClient(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                cookie=self.cookie,
                user_agent=self.USER_AGENT,
                device_type="IPHONE"
            )
        except Exception as e:
            raise TgtgLoginError("Unable to login with provided credentials.") from e

    def retrieve_credentials(self) -> None:
        """Retrieve new credentials from the TGTG API."""
        LOGGER.info("Retrieving new credentials from TGTG API.")
        try:
            client = TgtgClient(email=self.email)
            creds = client.get_credentials()
            self.access_token = creds['access_token']
            self.refresh_token = creds['refresh_token']
            self.user_id = creds['user_id']
            self.cookie = creds['cookie']
            LOGGER.info("Credentials successfully retrieved and stored.")

        except KeyError as e:
            raise TgtgAPIParsingError("Missing expected key in TGTG API response.") from e

        except Exception as e:
            raise TgtgLoginError("Failed to retrieve credentials due to an unexpected error.") from e

    def get_favorites_items(self) -> List[ItemDetails]:
        """Fetch and parse favorite items from TGTG API."""
        LOGGER.info("Fetching favorite items from TGTG API.")
        try:
            json_data = self.tgtg_client.get_favorites()
            LOGGER.info(f"Raw API response: {json_data}")
            favorites = [ItemDetails(**item) for item in json_data]
            LOGGER.info(f"Parsed {len(favorites)} favorite items from TGTG API.")
            return favorites
        
        except ValidationError as e:
            LOGGER.error(f"Validation error while parsing item details: {e}")
            raise TgtgAPIParsingError("Error parsing item details.") from e

        except Exception as e:
            error_message = str(e)
            LOGGER.error(f"Unexpected error occurred: {error_message}")

            if "captcha" in error_message.lower():
                LOGGER.error("Anti-bot CAPTCHA challenge detected.")
                raise ForbiddenError("Blocked by CAPTCHA challenge.") from e
            else:
                raise TgtgAPIConnectionError("An unexpected error occurred while connecting to TGTG API.") from e

    def get_notification_messages(
        self, 
        item_details_list: List[ItemDetails]
    ) -> List[str]:
        """Generate notification messages for available favorite items."""
        messages = []
        for item_details in item_details_list:
            try:
                notifications = self.database_handler.get_items("storeId", str(item_details.store.store_id))
            
                if item_details.items_available > 0 and not self._is_notification_sent_today(notifications):
                    message = NotificationFormatter.format_message(item_details)
                    messages.append(message)
                    self._record_notification(item_details)

            except DatabaseQueryError:
                continue
        return messages

    def _is_notification_sent_today(
        self, 
        notifications: List[Dict[str, str]]
    ) -> bool:
        """Check if a notification was sent for a specific store today."""
        today_date = datetime.now(pytz.UTC).date()
        for notification in notifications:
            last_date_str = notification.get('lastNotificationDate')
            if not last_date_str:
                continue

            try:
                notification_date = datetime.fromisoformat(last_date_str).date()
                if notification_date == today_date:
                    return True

            except ValueError:
                LOGGER.error(f"Invalid date format: {last_date_str}")
                continue
        return False

    def _record_notification(
        self, 
        item_details: ItemDetails
    ) -> None:
        """Save notification data in the database."""
        try:
            self.database_handler.put_item({
                'storeId': str(item_details.store.store_id),
                'lastNotificationDate': datetime.now(pytz.utc).isoformat(),
                'itemsAvailable': str(item_details.items_available),
            })
        except DatabaseQueryError as e:
            LOGGER.error(f"Failed to record notification for store ID {item_details.store.store_id}: {e}")