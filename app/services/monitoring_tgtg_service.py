import boto3
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
        self.lambda_arn: Optional[str] = Utils.get_environment_variable("LAMBDA_MONITORING_ARN")
        self.user_email: Optional[str] = Utils.get_environment_variable("USER_EMAIL")
        self.access_token: Optional[str] = Utils.get_environment_variable("ACCESS_TOKEN")
        self.refresh_token: Optional[str] = Utils.get_environment_variable("REFRESH_TOKEN")
        self.user_id: Optional[str] = Utils.get_environment_variable("USER_ID")
        self.tgtg_cookie: Optional[str] = Utils.get_environment_variable("TGTG_COOKIE")
        self.lambda_client: boto3.client = boto3.client('lambda')
    
    def start_monitoring(self) -> None:
        """Initialize monitoring by checking credentials and creating a TgtgService instance."""
        self.tgtg_service = self._get_tgtg_service_instance()
        if self.tgtg_service:
            self._monitor_favorites()
        else:
            LOGGER.error("Failed to initialize TgtgService due to missing credentials.")

    def _get_tgtg_service_instance(self) -> Optional[TgtgService]:
        """Retrieve or initialize the TgtgService with available credentials."""
        if all([self.access_token, self.refresh_token, self.user_id, self.tgtg_cookie]):
            LOGGER.info("User credentials available, initializing TgtgService.")
            try:
                tgtg_service = TgtgService(self.user_email, self.access_token, self.refresh_token, self.user_id, self.tgtg_cookie)
                tgtg_service.login()
                return tgtg_service

            except TgtgLoginError as e:
                LOGGER.error(f"Failed to login to TGTG API: {e}")

            except Exception as e:
                LOGGER.error(f"Unexpected error initializing TgtgService: {e}")
                return None
        else:
            LOGGER.info("Credentials missing - please ensure that all your environment variables are set")

    def _retrieve_tgtg_credentials(self) -> str:
        """Retrieve TgtgService using minimal credentials."""
        try:
            tgtg_service = TgtgService(email=self.user_email)
            tgtg_service.retrieve_credentials()  # Sends the email for verification
            return "PENDING"  # Indicates waiting for user action

        except TgtgLoginError as e:
            LOGGER.error(f"Failed to retrieve new credential: {e}")
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
                self.tgtg_service.access_token and
                self.tgtg_service.refresh_token and
                self.tgtg_service.cookie and
                (self.tgtg_service.access_token != current_access_token or
                self.tgtg_service.refresh_token != current_refresh_token or
                self.tgtg_service.cookie != current_cookie)
            )
            
            return credentials_updated

        except Exception as e:
            LOGGER.error(f"Error checking credential readiness: {e}")
            return False

    def _monitor_favorites(self) -> None:
        """Check favorite items and send notifications if new items are available."""
        LOGGER.info("Checking favorite items and sending notifications if needed.")
        try:
            favorites = self.tgtg_service.get_favorites_items()
            messages = self.tgtg_service.get_notification_messages(favorites)

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
    
    def update_lambda_env_vars(self, new_env_vars: dict) -> None:
        """Update AWS Lambda environment variables with new credentials."""
        try:
            LOGGER.info("Updating AWS Lambda environment variables with new credentials.")            
            response = self.lambda_client.get_function_configuration(FunctionName=self.lambda_arn)
            current_env_vars = response['Environment']['Variables']
            LOGGER.info(f"Current environment variables: {current_env_vars}")

            updated_env_vars = current_env_vars.copy()
            updated_env_vars.update(new_env_vars)

            self.lambda_client.update_function_configuration(FunctionName=self.lambda_arn, Environment={'Variables': updated_env_vars})
            LOGGER.info("AWS Lambda environment variables updated successfully.")

        except Exception as e:
            LOGGER.error(f"Failed to update AWS Lambda environment variables: {e}")
            raise