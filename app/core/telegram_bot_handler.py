import json
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
from app.core.database_handler import DatabaseHandler
from app.common.utils import Utils
from app.common.logger import LOGGER
from app.core.scheduler import Scheduler
from app.common.constants import WELCOME_GIF_URL

CALLBACK_DATA_START = "start"
CALLBACK_DATA_HELP = "help"
CALLBACK_DATA_SETTINGS = "settings"
CALLBACK_DATA_PAUSE_BOT = "pause"
CALLBACK_DATA_IS_BOT_PAUSED = "is-bot-paused"
CALLBACK_DATA_WAKE_UP_BOT = "wake-up"
CALLBACK_DATA_ABOUT = "about"
CALLBACK_DATA_LANGUAGE = "language"
LANGUAGE_OPTIONS = {"en": "🇬🇧 English", "fr": "🇫🇷 Français"}

class TelegramBotHandler:
    def __init__(
        self, 
        scheduler: Scheduler
    ):
        LOGGER.info("Initializing TelegramBotHandler")
        telegram_token = Utils.get_environment_variable("TELEGRAM_BOT_TOKEN")
        self.application = ApplicationBuilder().token(telegram_token).build()
        self.localizable_strings = Utils.load_localizable_data()
        self.database_handler = DatabaseHandler(table_name="User")
        self.chat_id = Utils.get_environment_variable("TELEGRAM_CHAT_ID")
        self.user_language = Utils.get_environment_variable("USER_LANGUAGE", default="en")
        self.scheduler = scheduler
        self.register_handlers()

    def register_handlers(self) -> None:
        """Register Telegram command handlers."""
        self.application.add_handler(CommandHandler(CALLBACK_DATA_START, self._start_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_HELP, self._help_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_SETTINGS, self._settings_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_PAUSE_BOT, self._pause_bot_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_IS_BOT_PAUSED, self._is_bot_paused_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_WAKE_UP_BOT, self._wake_up_bot_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_ABOUT, self._about_handler))
        self.application.add_handler(CommandHandler(CALLBACK_DATA_LANGUAGE, self._language_handler))

        self.application.add_handler(CallbackQueryHandler(self._language_handler, pattern="^language_"))
        self.application.add_handler(CallbackQueryHandler(self._callback_query_handler))
        self.application.add_handler(CallbackQueryHandler(self._cooldown_button_handler, pattern="^cooldown_"))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_custom_cooldown_input))
        LOGGER.info("Command handlers registered.")

    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Start command received.")
        await context.bot.send_animation(chat_id=update.effective_chat.id, animation=WELCOME_GIF_URL)
        text = self._get_localized_text("start-message")
        buttons = [
            InlineKeyboardButton(self._get_localized_text("help_button"), callback_data=CALLBACK_DATA_HELP),
            InlineKeyboardButton(self._get_localized_text("settings_button"), callback_data=CALLBACK_DATA_SETTINGS),
            InlineKeyboardButton(self._get_localized_text("about_button"), callback_data=CALLBACK_DATA_ABOUT)
        ]
        reply_markup = InlineKeyboardMarkup([buttons])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    async def _help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Help command received.")
        text = self._get_localized_text("help-message")

        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.HTML)

    async def _settings_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Settings command received.")
        text = self._get_localized_text("settings-message")
        
        buttons = [
            [
                InlineKeyboardButton(self._get_localized_text("is_bot_paused_button"), callback_data=CALLBACK_DATA_IS_BOT_PAUSED),
                InlineKeyboardButton(self._get_localized_text("pause_bot_button"), callback_data=CALLBACK_DATA_PAUSE_BOT),
                InlineKeyboardButton(self._get_localized_text("wake_up_bot_button"), callback_data=CALLBACK_DATA_WAKE_UP_BOT)
            ],
            [InlineKeyboardButton(self._get_localized_text("language_button"), callback_data=CALLBACK_DATA_LANGUAGE)]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    async def _is_bot_paused_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("Checking if the bot is paused.")
        
        if self.scheduler._is_in_cooldown():
            message = self._get_localized_text("bot_is_paused_message")
        else:
            message = self._get_localized_text("bot_is_active_message")
        
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
    
    async def _wake_up_bot_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle 'Wake Up Bot' command."""
        chat_id = update.effective_chat.id
        self.scheduler.remove_cooldown()
        success_message = self._get_localized_text("bot_wake_up_message")
        await context.bot.send_message(chat_id=chat_id, text=success_message, parse_mode=ParseMode.HTML)

    async def _pause_bot_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the pause_bot command."""
        LOGGER.info("Pause bot command received.")
        
        buttons = [InlineKeyboardButton(f"{i} mins", callback_data=f"cooldown_{i}") for i in [10, 15, 30, 60]]
        buttons.append(InlineKeyboardButton(self._get_localized_text("pause_button_custom"), callback_data="cooldown_custom"))
        
        reply_markup = InlineKeyboardMarkup([buttons])
        text = self._get_localized_text("pause_bot_message")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    async def _cooldown_button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the cooldown button click."""
        query = update.callback_query
        callback_data = query.data
        
        if callback_data.startswith("cooldown_"):
            cooldown_minutes = int(callback_data.split("_")[1])
            await self._activate_cooldown(update, context, cooldown_minutes)
        elif callback_data == "cooldown_custom":
            await query.answer()
            await self._ask_for_custom_cooldown(update, context)

    async def _ask_for_custom_cooldown(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Prompt the user to input a custom cooldown time."""
        text = self._get_localized_text("enter_custom_cooldown_message")
        await update.effective_chat.send_message(text=text)
        await update.effective_chat.send_message(self._get_localized_text("enter_cooldown_minutes"))
    
    async def _activate_cooldown(self, update: Update, context: ContextTypes.DEFAULT_TYPE, cooldown_minutes: int) -> None:
        """Activate cooldown based on the selected or custom cooldown value."""
        LOGGER.info(f"Activating cooldown for {cooldown_minutes} minutes.")
        self.scheduler.activate_cooldown(cooldown_minutes)
        
        success_message = self._get_localized_text("cooldown_success_message").format(cooldown_minutes)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=success_message, parse_mode=ParseMode.HTML)
    
    async def handle_custom_cooldown_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Capture the custom cooldown input from the user."""
        try:
            custom_minutes = int(update.message.text)

            if custom_minutes <= 0:
                await update.message.reply_text(self._get_localized_text("enter_valid_integer"))
                return
            await self._activate_cooldown(update, context, custom_minutes)

        except ValueError:
            await update.message.reply_text(self._get_localized_text("invalid_input_number"))

    async def _about_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.info("About command received.")
        text = self._get_localized_text("about-message")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.HTML)
    
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
        buttons = [InlineKeyboardButton(lang, callback_data=f"language_{code}") for code, lang in LANGUAGE_OPTIONS.items()]
        reply_markup = InlineKeyboardMarkup([buttons])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self._get_localized_text("language-selection"),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def _handle_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle user's language selection."""
        query = update.callback_query
        selected_language = query.data.split("_")[1]

        LOGGER.info(f"User selected language: {selected_language}")
        chat_id = update.effective_chat.id

        new_env_vars = {"USER_LANGUAGE": selected_language}
        Utils.update_lambda_env_vars(self.lambda_arn, new_env_vars)

        await query.answer()
        text = self._get_localized_text("language-message").format(language=LANGUAGE_OPTIONS[selected_language])
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    
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
        elif query.data == CALLBACK_DATA_PAUSE_BOT:
            LOGGER.info("Register Account button clicked.")
            await self._pause_bot_handler(update, context)
        elif query.data == CALLBACK_DATA_IS_BOT_PAUSED:
            LOGGER.info("Check if bot is paused button clicked.")
            await self._check_bot_paused_handler(update, context)
        elif query.data == CALLBACK_DATA_WAKE_UP_BOT:
            LOGGER.info("Wake up bot button clicked.")
            await self._wake_up_bot_handler(update, context)
        elif query.data == "language_settings":
            LOGGER.info("Change language button clicked.")
            await self._language_handler(update, context)
        else:
            LOGGER.warning(f"Unhandled callback data: {query.data}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=self._get_localized_text("unhandled-action"), parse_mode=ParseMode.HTML)

    def _get_localized_text(self, message_key: str) -> str:
        """Retrieve localized text based on the user's selected language."""
        return Utils.localize(message_key, self.user_language, self.localizable_strings)

    async def _set_bot_commands(self):
        """Register bot commands for Telegram UI."""
        commands = [
            BotCommand("start", self._get_localized_text("command_start")),
            BotCommand("settings", self._get_localized_text("command_settings")),
            BotCommand("pause", self._get_localized_text("command_pause_bot")),
            BotCommand("wake-up", self._get_localized_text("command_wake_up_bot")),
            BotCommand("help", self._get_localized_text("command_help")),
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