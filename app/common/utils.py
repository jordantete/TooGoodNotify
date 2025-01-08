import os, json, requests
from typing import Optional
from urllib.parse import quote
from app.common.logger import LOGGER
from app.common.constants import LOCALIZATIONS_FILE_PATH, TELEGRAM_API_URL

class Utils:
    @classmethod
    def get_environment_variable(cls, var_name: str, default=None):
        """Retrieve an environment variable, defaulting to the provided value if not found."""
        value = os.getenv(var_name, default)
        if value is None:
            LOGGER.warning(f"Environment variable '{var_name}' is not set and no default value was provided.")
        return value

    @staticmethod
    def load_localizable_data():
        """Load localization data from JSON."""
        try:
            with open(LOCALIZATIONS_FILE_PATH, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            LOGGER.error(f"Localization file not found at {LOCALIZATIONS_FILE_PATH}")
        except json.JSONDecodeError as e:
            LOGGER.error(f"Error decoding JSON in localization file: {e}")
        return {}

    @staticmethod
    def localize(key, language, localizable_data):
        """Retrieve a localized string by key and language."""
        translation = localizable_data.get(language, {}).get(key)
        if not translation:
            LOGGER.warning(f"Missing translation for '{key}' in '{language}'")
            return ""
        return translation

    @staticmethod
    def send_telegram_message(text: str, chat_id: Optional[str] = None):
        """Send a message via Telegram."""
        bot_token = Utils.get_environment_variable("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            LOGGER.error("Telegram bot token is missing.")
            return
        
        if chat_id is None:
            chat_id = Utils.get_environment_variable("TELEGRAM_CHAT_ID")
            if not chat_id:
                LOGGER.error("Telegram chat ID is missing and was not provided.")
                return

        encoded_text = quote(text, safe='')
        url = TELEGRAM_API_URL.format(token=bot_token) + f"?chat_id={chat_id}&disable_web_page_preview=True&parse_mode=Markdown&text={encoded_text}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            LOGGER.info("Telegram message sent successfully.")
        except requests.RequestException as e:
            LOGGER.error(f"Failed to send Telegram message: {e}")

    @staticmethod
    def ok_response():
        """Standard success response."""
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps('ok')
        }

    @staticmethod
    def error_response(message: str):
        """Standard error response with a message."""
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(message)
        }