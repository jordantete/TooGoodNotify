import pytz
from dateutil.parser import isoparse
from datetime import datetime, timedelta
from app.services.tgtg_service.models import ItemDetails, PickupInterval
from app.common.logger import LOGGER

class NotificationFormatter:
    """Helper class to format notification messages and time intervals."""

    @staticmethod
    def format_pickup_interval(
        interval: PickupInterval, 
        store_time_zone: str
    ) -> str:
        """Format pickup interval dates for display using the store's timezone."""
        if not interval or not interval.start or not interval.end:
            LOGGER.error("PickupInterval is missing or incomplete.")
            return "Pickup time unavailable"

        try:
            timezone = pytz.timezone(store_time_zone) if store_time_zone else pytz.UTC

            start_utc = isoparse(interval.start).astimezone(pytz.UTC)
            end_utc = isoparse(interval.end).astimezone(pytz.UTC)
            start_local = start_utc.astimezone(timezone)
            end_local = end_utc.astimezone(timezone)

            today_local = datetime.now(timezone).date()

            if start_local.date() == today_local:
                date_label = "*Aujourd'hui*"
            elif start_local.date() == today_local + timedelta(days=1):
                date_label = "*Demain*"
            else:
                date_label = start_local.strftime("%d/%m")

            return f"{date_label} de {start_local.strftime('%H:%M')} à {end_local.strftime('%H:%M')}"

        except pytz.UnknownTimeZoneError:
            LOGGER.error(f"Invalid timezone: {store_time_zone}")
            return "Pickup time unavailable"

        except ValueError as e:
            LOGGER.error(f"Error parsing datetime: {e}")
            return "Pickup time unavailable"

        except Exception as e:
            LOGGER.error(f"Unexpected error in format_pickup_interval: {e}")
            return "Pickup time unavailable"

    @staticmethod
    def format_message(item_details: ItemDetails) -> str:
        """Format a Telegram message for an available item."""
        item_url = f"https://share.toogoodtogo.com/item/{item_details.item.item_id}"
        nbr_of_item_string = ("nouveaux paniers disponibles chez" if item_details.items_available > 1 else "nouveau panier disponible chez")
        message = f"🍽 {item_details.items_available} {nbr_of_item_string} [{item_details.store.store_name}]({item_url})\n\n"

        if item_details.item.description:
            message += f"{item_details.item.description}\n\n"

        message += f"💰 *{item_details.item.item_price}* au lieu de {item_details.item.item_value}\n"

        pickup_time = NotificationFormatter.format_pickup_interval(item_details.pickup_interval, item_details.store.store_time_zone)

        location = (
            item_details.pickup_location.address.get('address_line', 'Unknown location')
            if item_details.pickup_location else "Unknown location"
        )

        message += f"⏰ {pickup_time}\n"
        message += f"📍 {location}"
        return message