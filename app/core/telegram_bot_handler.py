import json
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from app.core.database_handler import DatabaseHandler
from app.common.utils import Utils
from app.common.logger import LOGGER

TELEGRAM_BOT_TOKEN = Utils.get_environment_variable("TELEGRAM_BOT_TOKEN")
CALLBACK_DATA_START = "start"
CALLBACK_DATA_HELP = "help"
CALLBACK_DATA_SETTINGS = "settings"
LANGUAGE_OPTIONS = {"en": "English", "fr": "Français"}
DEFAULT_LANGUAGE = "fr"

class TelegramBotHandler:
    def __init__(self):
        LOGGER.info("Initializing TelegramBotHandler")
        self.application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        self.localizable_strings = Utils.load_localizable_data()
        self.database_handler = DatabaseHandler(table_name="User")
        self.chat_id = Utils.get_environment_variable("TELEGRAM_CHAT_ID")
        self.user_language = self._load_user_language()
        self.notifications_enabled = True
        self.register_handlers()
    
    def _load_user_language(self) -> str:
        """Load the user's preferred language from the database, or default to the configured language."""
        # user_data = self.database_handler.get_item("chat_id", str(self.chat_id))
        # return user_data.get("language", DEFAULT_LANGUAGE) if user_data else DEFAULT_LANGUAGE
        return DEFAULT_LANGUAGE

    def register_handlers(self) -> None:
        """Register Telegram command handlers."""
        self.application.add_handler(CommandHandler('start', self._start_handler))
        self.application.add_handler(CommandHandler('help', self._help_handler))
        self.application.add_handler(CommandHandler('settings', self._settings_handler))
        self.application.add_handler(CommandHandler('register', self._register_account_handler))
        self.application.add_handler(CommandHandler('notifications_start', self._notifications_start_handler))
        self.application.add_handler(CommandHandler('notifications_stop', self._notifications_stop_handler))
        self.application.add_handler(CommandHandler('status', self._status_handler))
        self.application.add_handler(CommandHandler('about', self._about_handler))
        self.application.add_handler(CallbackQueryHandler(self._language_selection_handler, pattern="^language_"))
        LOGGER.info("Command handlers registered.")

    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Start command received.")
        text = self._get_localized_text("start-message")
        buttons = [
            InlineKeyboardButton("Start", callback_data=CALLBACK_DATA_START),
            InlineKeyboardButton("Help", callback_data=CALLBACK_DATA_HELP),
            InlineKeyboardButton("Settings", callback_data=CALLBACK_DATA_SETTINGS)
        ]
        reply_markup = InlineKeyboardMarkup([buttons])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

    async def _help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Help command received.")
        text = self._get_localized_text("help-message")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    async def _settings_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Settings command received.")
        text = self._get_localized_text("settings-message")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    async def _register_account_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Register command received.")
        text = self._get_localized_text("register-message")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    async def _notifications_start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Notifications start command received.")
        text = self._get_localized_text("notifications-start")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    async def _notifications_stop_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Notifications stop command received.")
        text = self._get_localized_text("notifications-stop")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    async def _status_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Status command received.")
        status_text = self._get_localized_text("status-message").format(
            status="enabled" if self.notifications_enabled else "disabled",
            email="user@example.com"  # TODO: Replace with actual user data
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=status_text)

    async def _about_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("About command received.")
        text = self._get_localized_text("about-message")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    async def _language_command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Command to initiate language selection."""
        LOGGER.info("Language command received.")
        buttons = [InlineKeyboardButton(lang, callback_data=f"language_{code}") for code, lang in LANGUAGE_OPTIONS.items()]
        reply_markup = InlineKeyboardMarkup([buttons])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please select your language / Veuillez sélectionner votre langue:",
            reply_markup=reply_markup
        )

    async def _language_selection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler to process the language selection from inline buttons."""
        selected_language = update.callback_query.data.split("_")[1]
        chat_id = update.effective_chat.id
        # self.database_handler.put_item({"chat_id": str(chat_id), "language": selected_language})
        await update.callback_query.answer()

        text = self._get_localized_text("language-message").format(language=LANGUAGE_OPTIONS[selected_language])
        await context.bot.send_message(chat_id=chat_id, text=text)

    def _get_localized_text(self, message_key: str) -> str:
        """Retrieve localized text based on the user's selected language."""
        return Utils.localize(message_key, self.user_language, self.localizable_strings)
    
    async def start(self, event: Dict) -> None:
        """Process incoming Telegram webhook event."""
        try:
            LOGGER.info("Starting TelegramNotifier application.")
            await self.application.initialize()
            update = Update.de_json(json.loads(event["body"]), self.application.bot)
            await self.application.process_update(update)

        except Exception as e:
            LOGGER.error(f"Error in TelegramNotifier: {e}")

        finally:
            await self.application.shutdown()
            LOGGER.info("TelegramNotifier application shutdown.")