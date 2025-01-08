from typing import Optional
from app.core.scheduler import Scheduler
from app.services.tgtg_service.tgtg_service import TgtgService
from app.services.tgtg_service.exceptions import TgtgAPIConnectionError, TgtgAPIParsingError, TgtgLoginError, ForbiddenError
from app.common.logger import LOGGER
from app.common.utils import Utils

class MonitoringTgtgService:
    def __init__(
        self, 
        scheduler: Scheduler
    ):
        self.scheduler = scheduler
        self.user_email: Optional[str] = Utils.get_environment_variable("USER_EMAIL")
        self.access_token: Optional[str] = Utils.get_environment_variable("ACCESS_TOKEN")
        self.refresh_token: Optional[str] = Utils.get_environment_variable("REFRESH_TOKEN")
        self.user_id: Optional[str] = Utils.get_environment_variable("USER_ID")
        self.tgtg_cookie: Optional[str] = Utils.get_environment_variable("TGTG_COOKIE")
    
    def start_monitoring(self) -> None:
        """Initialize monitoring by checking credentials and creating a TgtgService instance."""
        tgtg_service = self._get_tgtg_service_instance()
        if tgtg_service:
            self._monitor_favorites(tgtg_service)
        else:
            LOGGER.error("Failed to initialize TgtgService due to missing credentials.")

    def _get_tgtg_service_instance(self) -> Optional[TgtgService]:
        """Retrieve or initialize the TgtgService with available credentials."""
        if all([self.access_token, self.refresh_token, self.user_id, self.tgtg_cookie]):
            LOGGER.info("User credentials available, initializing TgtgService.")
            try:
                tgtg_service = TgtgService(
                    email=self.user_email,
                    access_token=self.access_token,
                    refresh_token=self.refresh_token,
                    user_id=self.user_id,
                    cookie=self.tgtg_cookie
                )
                tgtg_service.login()
                return tgtg_service

            except TgtgLoginError as e:
                LOGGER.error(f"Failed to login to TGTG API: {e}")
                return self._retrieve_and_login()

            except Exception as e:
                LOGGER.error(f"Unexpected error initializing TgtgService: {e}")
                return None
        else:
            LOGGER.info("Credentials missing - please ensure that all your environment variables are set")
    
    def _retrieve_and_login(self) -> Optional[TgtgService]:
        """Retrieve and log in to TgtgService using minimal credentials."""
        try:
            tgtg_service = TgtgService(email=self.user_email)
            tgtg_service.retrieve_credentials()
            tgtg_service.login()
            return tgtg_service

        except TgtgLoginError as e:
            LOGGER.error(f"Failed to log in with new credentials: {e}")
            return None

        except Exception as e:
            LOGGER.error(f"Unexpected error during credential retrieval: {e}")
            return None

    def _monitor_favorites(self, tgtg_service: TgtgService) -> None:
        """Check favorite items and send notifications if new items are available."""
        LOGGER.info("Checking favorite items and sending notifications if needed.")
        try:
            favorites = tgtg_service.get_favorites_items()
            messages = tgtg_service.get_notification_messages(favorites)

            for message in messages:
                LOGGER.info(f"Sending Telegram message: {message}")
                Utils.send_telegram_message(message)

            if not messages:
                LOGGER.info("No new items available - no notifications sent.")

        except TgtgAPIParsingError as e:
            error_msg = f"TgtgAPIParsingError encountered: {str(e)}"
            LOGGER.error(error_msg)
            Utils.send_telegram_message(f"TooGoodToNotify: System Error - {error_msg}")

        except ForbiddenError as e:
            LOGGER.error(f"ForbiddenError: {str(e)}")
            self.scheduler.activate_cooldown()
            Utils.send_telegram_message("API access forbidden. Monitoring paused temporarily.")

        except TgtgAPIConnectionError as e:
            LOGGER.error(f"Connection error to TGTG API. {str(e)}")
            Utils.send_telegram_message(f"TGTG API connection error: {str(e)}")