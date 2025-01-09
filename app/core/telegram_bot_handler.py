import json, asyncio
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from app.core.database_handler import DatabaseHandler
from app.common.utils import Utils
from app.common.logger import LOGGER
from app.services.tgtg_service_monitor import TgtgServiceMonitor
from app.common.constants import WELCOME_GIF_URL

TELEGRAM_BOT_TOKEN = Utils.get_environment_variable("TELEGRAM_BOT_TOKEN")
CALLBACK_DATA_START = "start"
CALLBACK_DATA_HELP = "help"
CALLBACK_DATA_SETTINGS = "settings"
CALLBACK_DATA_REGISTER = "register"
CALLBACK_DATA_ABOUT = "about"
CALLBACK_DATA_LANGUAGE = "language"
CALLBACK_NOTIFICATIONS_START = "notifications_start"
CALLBACK_NOTIFICATIONS_STOP = "notifications_stop"
LANGUAGE_OPTIONS = {"en": "🇬🇧 English", "fr": "🇫🇷 Français"}
DEFAULT_LANGUAGE = "fr"

class TelegramBotHandler:
    def __init__(
        self, 
        tgtg_service_monitor: TgtgServiceMonitor
    ):
        LOGGER.info("Initializing TelegramBotHandler")
        self.application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        self.localizable_strings = Utils.load_localizable_data()
        self.database_handler = DatabaseHandler(table_name="User")
        self.chat_id = Utils.get_environment_variable("TELEGRAM_CHAT_ID")
        self.user_language = self._load_user_language()
        self.notifications_enabled = True
        self.tgtg_service_monitor = tgtg_service_monitor
        self.register_handlers()
    
    def _load_user_language(self) -> str:
        """Load the user's preferred language from the database, or default to the configured language."""
        # user_data = self.database_handler.get_item("chat_id", str(self.chat_id))
        # return user_data.get("language", DEFAULT_LANGUAGE) if user_data else DEFAULT_LANGUAGE
        return DEFAULT_LANGUAGE

    def register_handlers(self) -> None:
        """Register Telegram command handlers."""
        self.application.add_handler(CommandHandler(CALLBACK_DATA_START, self._start_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_HELP, self._help_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_SETTINGS, self._settings_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_REGISTER, self._register_account_handler))
        self.application.add_handler(CommandHandler(CALLBACK_NOTIFICATIONS_START, self._notifications_start_handler))
        self.application.add_handler(CommandHandler(CALLBACK_NOTIFICATIONS_STOP, self._notifications_stop_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_ABOUT, self._about_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_LANGUAGE, self._language_handler))

        self.application.add_handler(CallbackQueryHandler(self._language_handler, pattern="^language_"))
        self.application.add_handler(CallbackQueryHandler(self._callback_query_handler))
        LOGGER.info("Command handlers registered.")

    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Start command received.")
        await context.bot.send_animation(chat_id=update.effective_chat.id, animation=WELCOME_GIF_URL)

        text = Utils.escape_markdown_v2(self._get_localized_text("start-message"))
        buttons = [
            InlineKeyboardButton("💡 Register", callback_data=CALLBACK_DATA_REGISTER),
            InlineKeyboardButton("📖 Help", callback_data=CALLBACK_DATA_HELP),
            InlineKeyboardButton("⚙️ Settings", callback_data=CALLBACK_DATA_SETTINGS)
        ]
        reply_markup = InlineKeyboardMarkup([buttons])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode="MarkdownV2")

    async def _help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Help command received.")
        text = Utils.escape_markdown_v2(self._get_localized_text("help-message"))

        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="MarkdownV2")

    async def _settings_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Settings command received.")
        text = self._get_localized_text("settings-message")
        
        buttons = [
            [
                InlineKeyboardButton("Enable Notifications", callback_data=CALLBACK_NOTIFICATIONS_START),
                InlineKeyboardButton("Disable Notifications", callback_data=CALLBACK_NOTIFICATIONS_STOP)
            ],
            [InlineKeyboardButton("Change Language", callback_data="language_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

    async def _register_account_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Register command received. Refreshing TGTG credentials.")
        chat_id = update.effective_chat.id

        try:
            creds_request_status = self.tgtg_service_monitor.request_new_tgtg_credentials()
            if creds_request_status == "FAILED":
                await context.bot.send_message(chat_id=chat_id, text=self._get_localized_text("register-failed"))
                return

            await context.bot.send_message(chat_id=chat_id, text=self._get_localized_text("register-pending"))

            timeout = 300  # 5 minutes
            poll_interval = 10  # Check every 10 seconds
            elapsed_time = 0

            while elapsed_time < timeout:
                if self.tgtg_service_monitor.check_credentials_ready():
                    new_env_vars = {
                        "ACCESS_TOKEN": self.tgtg_service_monitor.tgtg_service.access_token,
                        "REFRESH_TOKEN": self.tgtg_service_monitor.tgtg_service.refresh_token,
                        "USER_ID": self.tgtg_service_monitor.tgtg_service.user_id,
                        "TGTG_COOKIE": self.tgtg_service_monitor.tgtg_service.cookie
                    }
                    self.tgtg_service_monitor.update_lambda_env_vars(new_env_vars)

                    await context.bot.send_message(chat_id=chat_id, text=self._get_localized_text("register-success"))
                    return

                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

            await context.bot.send_message(chat_id=chat_id, text=self._get_localized_text("register-timeout"))

        except Exception as e:
            LOGGER.error(f"Error during registration process: {e}")
            await context.bot.send_message(chat_id=chat_id, text=self._get_localized_text("register-error"))

    async def _notifications_start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Notifications start command received.")
        text = self._get_localized_text("notifications-start")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    async def _notifications_stop_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Notifications stop command received.")
        text = self._get_localized_text("notifications-stop")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    async def _about_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("About command received.")
        text = self._get_localized_text("about-message")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    
    async def _language_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle language selection initiation and processing."""
        if update.callback_query:
            await self._process_language_callback(update, context)
        else:
            await self._show_language_selection(update, context)
    
    async def _process_language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process callback data for language selection."""
        query = update.callback_query
        callback_data = query.data

        if callback_data == "language_settings":
            LOGGER.info("Change Language button clicked.")
            await self._show_language_selection(update, context)
        elif callback_data.startswith("language_"):
            await self._handle_language_selection(update, context)
        else:
            LOGGER.warning(f"Unexpected callback data: {callback_data}")
            await query.answer()
    
    async def _show_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send language selection options to the user."""
        LOGGER.info("Displaying language selection options.")
        buttons = [
            InlineKeyboardButton(lang, callback_data=f"language_{code}")
            for code, lang in LANGUAGE_OPTIONS.items()
        ]
        reply_markup = InlineKeyboardMarkup([buttons])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self._get_localized_text("language-selection"),
            reply_markup=reply_markup
        )
    
    async def _handle_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle user's language selection."""
        query = update.callback_query
        selected_language = query.data.split("_")[1]

        LOGGER.info(f"User selected language: {selected_language}")
        chat_id = update.effective_chat.id

        # TODO: Save the selected language (uncomment and implement if using a database)
        # self.database_handler.put_item({"chat_id": str(chat_id), "language": selected_language})

        await query.answer()
        text = self._get_localized_text("language-message").format(language=LANGUAGE_OPTIONS[selected_language])
        await context.bot.send_message(chat_id=chat_id, text=text)
    
    async def _callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button presses (Help, Settings, etc.)."""
        query = update.callback_query
        await query.answer()

        if query.data == CALLBACK_DATA_HELP:
            LOGGER.info("Help button clicked.")
            await self._help_handler(update, context)
        elif query.data == CALLBACK_DATA_SETTINGS:
            LOGGER.info("Settings button clicked.")
            await self._settings_handler(update, context)
        elif query.data == CALLBACK_DATA_START:
            LOGGER.info("Start button clicked.")
            await self._start_handler(update, context)
        elif query.data == CALLBACK_NOTIFICATIONS_START:
            LOGGER.info("Enable Notifications button clicked.")
            await self._notifications_start_handler(update, context)
        elif query.data == CALLBACK_NOTIFICATIONS_STOP:
            LOGGER.info("Disable Notifications button clicked.")
            await self._notifications_stop_handler(update, context)
        elif query.data == CALLBACK_DATA_REGISTER:
            LOGGER.info("Register Account button clicked.")
            await self._register_account_handler(update, context)
        else:
            LOGGER.warning(f"Unhandled callback data: {query.data}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=self._get_localized_text("unhandled-action"))

    def _get_localized_text(self, message_key: str) -> str:
        """Retrieve localized text based on the user's selected language."""
        return Utils.localize(message_key, self.user_language, self.localizable_strings)

    async def _set_bot_commands(self):
        """Register bot commands for Telegram UI."""
        commands = [
            BotCommand("start", self._get_localized_text("command_start")),
            BotCommand("help", self._get_localized_text("command_help")),
            BotCommand("settings", self._get_localized_text("command_settings")),
            BotCommand("register", self._get_localized_text("command_register")),
            BotCommand("about", self._get_localized_text("command_about")),
        ]
        await self.application.bot.set_my_commands(commands)
    
    async def start(self, event: Dict) -> None:
        """Process incoming Telegram webhook event."""
        try:
            LOGGER.info("Starting TelegramNotifier application.")
            await self.application.initialize()
            await self._set_bot_commands()
            update = Update.de_json(json.loads(event["body"]), self.application.bot)
            await self.application.process_update(update)

        except Exception as e:
            LOGGER.error(f"Error in TelegramNotifier: {e}")

        finally:
            await self.application.shutdown()
            LOGGER.info("TelegramNotifier application shutdown.")