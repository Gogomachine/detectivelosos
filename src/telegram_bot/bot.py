"""Telegram bot for managing the AML detective channel."""

import logging

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

logger = logging.getLogger(__name__)

# Maximum Telegram message length
MAX_MESSAGE_LENGTH = 4096


class TelegramPublisher:
    """Publishes content to the Telegram channel."""

    def __init__(
        self,
        bot_token: str | None = None,
        channel_id: str | None = None,
    ):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.channel_id = channel_id or TELEGRAM_CHANNEL_ID
        self._bot: Bot | None = None

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(token=self.bot_token)
        return self._bot

    async def publish_post(self, text: str) -> int | None:
        """
        Publish a post to the Telegram channel.
        Returns the message ID or None on failure.
        """
        try:
            # Split long messages
            parts = self._split_message(text)
            message_id = None

            for part in parts:
                message = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=part,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )
                if message_id is None:
                    message_id = message.message_id

            logger.info(f"Published post to {self.channel_id}, msg_id={message_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to publish post: {e}")
            # Retry without HTML parsing if it was a formatting error
            try:
                message = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=text[:MAX_MESSAGE_LENGTH],
                )
                return message.message_id
            except Exception as e2:
                logger.error(f"Retry also failed: {e2}")
                return None

    def _split_message(self, text: str) -> list[str]:
        """Split a long message into parts respecting Telegram limits."""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        parts = []
        while text:
            if len(text) <= MAX_MESSAGE_LENGTH:
                parts.append(text)
                break

            # Try to split at paragraph boundary
            split_pos = text.rfind("\n\n", 0, MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = MAX_MESSAGE_LENGTH

            parts.append(text[:split_pos])
            text = text[split_pos:].lstrip()

        return parts

    async def publish_with_markdown(self, text: str) -> int | None:
        """Publish using Markdown parse mode (Telegram's MarkdownV2)."""
        try:
            escaped = self._escape_markdown_v2(text)
            message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=escaped[:MAX_MESSAGE_LENGTH],
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return message.message_id
        except Exception as e:
            logger.warning(f"MarkdownV2 failed, falling back to plain: {e}")
            return await self.publish_post(text)

    @staticmethod
    def _escape_markdown_v2(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2."""
        special_chars = r"_[]()~`>#+-=|{}.!"
        result = []
        i = 0
        while i < len(text):
            # Preserve bold markers
            if text[i:i+2] == "**":
                result.append("**")
                i += 2
                continue
            if text[i] in special_chars:
                result.append(f"\\{text[i]}")
            else:
                result.append(text[i])
            i += 1
        return "".join(result)


class AdminBot:
    """Admin bot for controlling the agent via Telegram commands."""

    def __init__(
        self,
        bot_token: str | None = None,
        admin_chat_ids: list[int] | None = None,
    ):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.admin_chat_ids = admin_chat_ids or []
        self.app: Application | None = None
        self._on_force_post = None
        self._on_status = None

    def set_callbacks(self, on_force_post=None, on_status=None):
        """Set callback functions for admin commands."""
        self._on_force_post = on_force_post
        self._on_status = on_status

    def _is_admin(self, user_id: int) -> bool:
        """Check if user is an authorized admin."""
        if not self.admin_chat_ids:
            return True  # No restrictions if no admins configured
        return user_id in self.admin_chat_ids

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        await update.message.reply_text(
            "🕵️ Кейс Уокер на связи!\n\n"
            "Команды:\n"
            "/status — статус агента\n"
            "/post — принудительно опубликовать пост\n"
            "/digest — сгенерировать дайджест\n"
            "/stats — статистика канала"
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        if self._on_status:
            status = await self._on_status()
            await update.message.reply_text(status)
        else:
            await update.message.reply_text("Агент работает ✅")

    async def cmd_force_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /post command to force publish next post."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        if self._on_force_post:
            await update.message.reply_text("⏳ Генерирую пост...")
            result = await self._on_force_post()
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("Функция не подключена")

    def build(self) -> Application:
        """Build the bot application."""
        self.app = Application.builder().token(self.bot_token).build()
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("post", self.cmd_force_post))
        return self.app
