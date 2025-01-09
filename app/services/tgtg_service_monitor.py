import boto3
from typing import Optional
from app.core.scheduler import Scheduler
from app.services.tgtg_service.tgtg_service import TgtgService
from app.services.tgtg_service.exceptions import TgtgAPIConnectionError, TgtgAPIParsingError, TgtgLoginError, ForbiddenError
from app.common.logger import LOGGER
from app.common.utils import Utils

class TgtgServiceMonitor:
    def __init__(self):
        self.user_email: Optional[str] = Utils.get_environment_variable("USER_EMAIL")
        self.access_token: Optional[str] = Utils.get_environment_variable("ACCESS_TOKEN")
        self.refresh_token: Optional[str] = Utils.get_environment_variable("REFRESH_TOKEN")
        self.user_id: Optional[str] = Utils.get_environment_variable("USER_ID")
        self.tgtg_cookie: Optional[str] = Utils.get_environment_variable("TGTG_COOKIE")
    
    def start_monitoring(self, scheduler: Scheduler) -> None:
        """
        Start the monitoring process by checking for valid credentials. 
        If the credentials are valid, it proceeds to monitor the favorites.
        """
        if not self._are_credentials_valid():
            LOGGER.error("Missing or invalid credentials. Please ensure that all your environment variables are set correctly.")
            LOGGER.error(f"Current credentials are: user_email: {self.user_email}, access_token: {self.access_token}, refresh_token: {self.refresh_token}, user_id: {self.user_id}, tgtg_cookie: {self.tgtg_cookie}")
            return None

        self._monitor_favorites(scheduler)

    def _are_credentials_valid(self) -> bool:
        """Checks whether all necessary credentials are available."""
        return all([self.access_token, self.refresh_token, self.user_id, self.tgtg_cookie])

    def request_new_tgtg_credentials(self) -> str:
        """Retrieve TgtgService using minimal credentials."""
        try:
            tgtg_service = TgtgService()
            tgtg_service.retrieve_credentials(email=self.user_email)  # Sends the email for verification
            return "PENDING"  # Indicates waiting for user action

        except TgtgLoginError as e:
            LOGGER.error(f"Failed to retrieve new credentials: {e}")
            return "FAILED"

        except Exception as e:
            LOGGER.error(f"Unexpected error during credential retrieval: {e}")
            return "FAILED"
    
    def check_credentials_ready(self) -> bool:
        """Check if new credentials have been retrieved and differ from the current ones."""
        try:
            # Get current environment variables
            current_access_token = Utils.get_environment_variable("ACCESS_TOKEN")
            current_refresh_token = Utils.get_environment_variable("REFRESH_TOKEN")
            current_cookie = Utils.get_environment_variable("TGTG_COOKIE")

            # Compare with new credentials from TgtgService
            credentials_updated = (
                'access_token' in self.tgtg_service.credentials and
                'refresh_token' in self.tgtg_service.credentials and
                'cookie' in self.tgtg_service.credentials and
                (self.tgtg_service.credentials['access_token'] != current_access_token or
                self.tgtg_service.credentials['refresh_token'] != current_refresh_token or
                self.tgtg_service.credentials['cookie'] != current_cookie)
            )
            return credentials_updated

        except Exception as e:
            LOGGER.error(f"Error checking credential readiness: {e}")
            return False

    def _monitor_favorites(self, scheduler: Scheduler) -> None:
        """Check favorite items and send notifications if new items are available."""
        LOGGER.info("Checking favorite items and sending notifications if needed.")
        try:
            tgtg_service = TgtgService()
            favorites = tgtg_service.get_favorites_items_list(email=self.user_email, access_token=self.access_token, refresh_token=self.refresh_token, cookie=self.tgtg_cookie)
            messages = tgtg_service.get_notification_messages(favorites)

            for message in messages:
                LOGGER.info(f"Sending Telegram message: {message}")
                Utils.send_telegram_message(message)

            if not messages:
                LOGGER.info("No new items available - no notifications sent.")

        except TgtgAPIParsingError as e:
            error_msg = f"TgtgAPIParsingError encountered: {str(e)}"
            LOGGER.error(error_msg)
            Utils.send_telegram_message(f"TgtgAPIParsingError: {error_msg}")

        except ForbiddenError as e:
            LOGGER.error(f"ForbiddenError: {str(e)}")
            scheduler.activate_cooldown()
            Utils.send_telegram_message("API access forbidden. Monitoring paused temporarily.")

        except TgtgAPIConnectionError as e:
            LOGGER.error(f"Connection error to TGTG API. {str(e)}")
            Utils.send_telegram_message(f"TGTG API connection error: {str(e)}")
        
        except Exception as e:
            LOGGER.error(f"Unexpected error in _monitor_favorites: {str(e)}")
            Utils.send_telegram_message(f"TooGoodToNotify: Unexpected system error - {str(e)}")
    
    def update_lambda_env_vars(
        self, 
        lambda_arn: str, 
        new_env_vars: dict
    ) -> None:
        """Update AWS Lambda environment variables with new credentials."""
        try:
            LOGGER.info("Updating AWS Lambda environment variables with new credentials.")      
            lambda_client = boto3.client('lambda')
            response = lambda_client.get_function_configuration(FunctionName=lambda_arn)
            current_env_vars = response['Environment']['Variables']
            LOGGER.info(f"Current environment variables: {current_env_vars}")

            updated_env_vars = current_env_vars.copy()
            updated_env_vars.update(new_env_vars)

            lambda_client.update_function_configuration(FunctionName=lambda_arn, Environment={'Variables': updated_env_vars})
            LOGGER.info("AWS Lambda environment variables updated successfully.")

        except Exception as e:
            raise Exception(f"Failed to update AWS Lambda environment variables: {e}")