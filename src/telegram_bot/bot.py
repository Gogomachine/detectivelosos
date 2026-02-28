"""Telegram bot for managing the AML detective channel."""

import logging
import random
import re

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096
INVESTIGATION_PRICE_STARS = 1000

# Conversation states
WAITING_ADDRESS = 1

# AML Dictionary topics for quick lookup
AML_DICTIONARY_TOPICS = [
    ("Миксеры и тамблеры", "mixers"),
    ("Chain Hopping", "chain_hopping"),
    ("Peel Chains", "peel_chains"),
    ("Кластеризация адресов", "clustering"),
    ("Dusting-атаки", "dusting"),
    ("DeFi-скамы", "defi_scams"),
    ("Санкции OFAC", "sanctions"),
    ("Lazarus Group", "lazarus"),
    ("Red Flags", "red_flags"),
    ("FATF и Travel Rule", "fatf"),
    ("Блокчейн-аналитика", "analytics"),
    ("VASP Framework", "vasp"),
]


def _clean_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not text:
        return ""
    from bs4 import BeautifulSoup
    clean = BeautifulSoup(text, "lxml").get_text(separator=" ")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


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
        """Publish a post to the Telegram channel."""
        try:
            parts = self._split_message(text)
            message_id = None

            for part in parts:
                message = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=part,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                if message_id is None:
                    message_id = message.message_id

            logger.info(f"Published post to {self.channel_id}, msg_id={message_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to publish post: {e}")
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

            split_pos = text.rfind("\n\n", 0, MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = MAX_MESSAGE_LENGTH

            parts.append(text[:split_pos])
            text = text[split_pos:].lstrip()

        return parts


class UserBot:
    """
    Public-facing bot with user commands:
    - /start - main menu with buttons
    - "Заказать расследование" - pay 1000 Stars, send address, get report in 24h
    - "Хочу статью" - random article from DB
    - "Словарь AML" - browse AML encyclopedia topics
    """

    def __init__(
        self,
        bot_token: str | None = None,
        db=None,
        admin_chat_ids: list[int] | None = None,
    ):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.db = db
        self.admin_chat_ids = admin_chat_ids or []
        self.app: Application | None = None
        self._on_force_post = None
        self._on_status = None
        self._on_explain_term = None

    def set_callbacks(self, on_force_post=None, on_status=None, on_explain_term=None):
        """Set callback functions for admin commands."""
        self._on_force_post = on_force_post
        self._on_status = on_status
        self._on_explain_term = on_explain_term

    def _is_admin(self, user_id: int) -> bool:
        if not self.admin_chat_ids:
            return True
        return user_id in self.admin_chat_ids

    # --- Main menu ---

    def _main_keyboard(self) -> InlineKeyboardMarkup:
        """Build the main menu keyboard."""
        buttons = [
            [InlineKeyboardButton(
                "🔍 Заказать расследование (1000 ⭐)",
                callback_data="investigate",
            )],
            [InlineKeyboardButton(
                "📰 Хочу статью",
                callback_data="random_article",
            )],
            [InlineKeyboardButton(
                "📚 Словарь AML",
                callback_data="aml_dictionary",
            )],
            [InlineKeyboardButton(
                "✉️ Связаться со мной",
                callback_data="contact",
            )],
        ]
        return InlineKeyboardMarkup(buttons)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start - show main menu."""
        await update.message.reply_text(
            "🕵️ Кейс Уокер на связи!\n\n"
            "Я - АМЛ-детектив. Хожу по делам, раскапываю схемы "
            "и пишу про отмывание денег.\n\n"
            "Что тебя интересует?",
            reply_markup=self._main_keyboard(),
        )

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu - show main menu again."""
        await update.message.reply_text(
            "🕵️ Главное меню Кейса Уокера:",
            reply_markup=self._main_keyboard(),
        )

    # --- Random article ---

    async def callback_random_article(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle 'Хочу статью' button press."""
        query = update.callback_query
        await query.answer()

        if not self.db:
            await query.edit_message_text("База данных не подключена")
            return

        article = await self.db.get_random_article()
        if not article:
            await query.edit_message_text(
                "🕵️ В базе пока нет статей. Зайди позже - Кейс Уокер уже на деле!",
                reply_markup=self._main_keyboard(),
            )
            return

        title = _clean_html(article["title"])
        source = article["source"]
        url = article.get("url", "")
        content = _clean_html(article.get("content", ""))

        # Build the article message
        text = f"📰 {title}\n\n"
        if content:
            preview = content[:800]
            if len(content) > 800:
                preview += "..."
            text += f"{preview}\n\n"
        text += f"Источник: {source}\n"
        if url:
            text += f"Читать полностью: {url}\n"

        # Add "another article" and "back" buttons
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Ещё статью", callback_data="random_article")],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")],
        ])

        await query.edit_message_text(text, reply_markup=keyboard)

    async def callback_back_to_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle back to menu button."""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "🕵️ Главное меню Кейса Уокера:",
            reply_markup=self._main_keyboard(),
        )

    # --- AML Dictionary ---

    async def callback_aml_dictionary(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle 'Словарь AML' button - show topic list."""
        query = update.callback_query
        await query.answer()

        buttons = []
        for i in range(0, len(AML_DICTIONARY_TOPICS), 2):
            row = []
            for j in range(i, min(i + 2, len(AML_DICTIONARY_TOPICS))):
                name, key = AML_DICTIONARY_TOPICS[j]
                row.append(InlineKeyboardButton(
                    name, callback_data=f"dict_{key}"
                ))
            buttons.append(row)
        buttons.append([
            InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")
        ])

        await query.edit_message_text(
            "📚 Словарь AML от Кейса Уокера\n\n"
            "Выбери тему - я расскажу что знаю:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def callback_dict_topic(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle dictionary topic selection."""
        query = update.callback_query
        await query.answer("Готовлю материал...")

        topic_key = query.data.replace("dict_", "")

        # Find topic name
        topic_name = topic_key
        for name, key in AML_DICTIONARY_TOPICS:
            if key == topic_key:
                topic_name = name
                break

        # Get explanation from the generator via callback
        if self._on_explain_term:
            try:
                explanation = await self._on_explain_term(topic_name)
            except Exception as e:
                logger.error(f"Failed to generate explanation: {e}")
                explanation = self._get_static_explanation(topic_key)
        else:
            explanation = self._get_static_explanation(topic_key)

        # Truncate if too long
        if len(explanation) > 3500:
            explanation = explanation[:3500] + "..."

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Другие темы", callback_data="aml_dictionary")],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")],
        ])

        await query.edit_message_text(
            f"📚 {topic_name}\n\n{explanation}",
            reply_markup=keyboard,
        )

    def _get_static_explanation(self, topic_key: str) -> str:
        """Fallback static explanations from encyclopedia."""
        from config.encyclopedia import AML_ENCYCLOPEDIA
        from src.content.generator import _extract_section, ENCYCLOPEDIA_SECTIONS

        marker = ENCYCLOPEDIA_SECTIONS.get(topic_key, "")
        if marker:
            section = _extract_section(marker)
            if section:
                # Trim to reasonable length for Telegram
                if len(section) > 3000:
                    section = section[:3000] + "..."
                return section

        return "Информация по этой теме скоро появится. Кейс Уокер уже на деле! 🕵️"

    # --- Contact / Message to admin ---

    async def callback_contact(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle 'Связаться со мной' button - ask user for a message."""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "✉️ Связаться с Кейсом Уокером\n\n"
            "Напиши своё сообщение - я обязательно прочитаю и отвечу.\n\n"
            "Можешь задать вопрос, предложить тему для расследования, "
            "оставить отзыв или просто поздороваться.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Отмена", callback_data="back_to_menu")],
            ]),
        )

        context.user_data["awaiting_contact_message"] = True

    async def handle_contact_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle user's contact message and forward it to admin(s)."""
        if not context.user_data.get("awaiting_contact_message"):
            return False

        context.user_data["awaiting_contact_message"] = False
        user = update.effective_user
        message_text = update.message.text.strip()

        if not message_text:
            await update.message.reply_text(
                "Пустое сообщение. Попробуй ещё раз.",
                reply_markup=self._main_keyboard(),
            )
            return True

        # Forward to admin(s)
        forwarded = False
        for admin_id in self.admin_chat_ids:
            try:
                bot = Bot(token=self.bot_token)
                reply_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "💬 Ответить",
                        callback_data=f"reply_{user.id}",
                    )],
                ])
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"✉️ Новое сообщение от пользователя\n\n"
                        f"От: @{user.username or 'нет юзернейма'} "
                        f"(ID: {user.id})\n"
                        f"Имя: {user.full_name}\n\n"
                        f"Сообщение:\n{message_text}"
                    ),
                    reply_markup=reply_keyboard,
                )
                forwarded = True
            except Exception as e:
                logger.error(f"Failed to forward message to admin {admin_id}: {e}")

        if forwarded:
            await update.message.reply_text(
                "✅ Сообщение отправлено!\n\n"
                "Кейс Уокер получил твоё письмо и ответит "
                "как только разберётся с текущими делами. 🕵️",
                reply_markup=self._main_keyboard(),
            )
        else:
            await update.message.reply_text(
                "К сожалению, не удалось отправить сообщение. "
                "Попробуй позже.",
                reply_markup=self._main_keyboard(),
            )

        return True

    # --- Investigation order (Telegram Stars payment) ---

    async def callback_investigate(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle 'Заказать расследование' button - explain and ask for address."""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "🔍 Заказать расследование\n\n"
            "Кейс Уокер лично проведёт проверку по указанному адресу "
            "(кошелёк, компания, контрагент).\n\n"
            "Стоимость: 1000 ⭐ (Telegram Stars)\n"
            "Срок: до 24 часов\n"
            "Результат: подробный отчёт в личном сообщении\n\n"
            "Отправь мне адрес для проверки (текстовым сообщением):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Отмена", callback_data="back_to_menu")],
            ]),
        )

        context.user_data["awaiting_address"] = True

    async def handle_text_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Route incoming text messages to the correct handler."""
        # 1. Admin reply to user
        if context.user_data.get("reply_to_user_id"):
            await self.handle_admin_reply(update, context)
            return

        # 2. Contact message from user
        if context.user_data.get("awaiting_contact_message"):
            await self.handle_contact_message(update, context)
            return

        # 3. Investigation address
        if not context.user_data.get("awaiting_address"):
            return

        address = update.message.text.strip()
        if not address or len(address) < 3:
            await update.message.reply_text(
                "Адрес слишком короткий. Отправь корректный адрес для проверки."
            )
            return

        context.user_data["awaiting_address"] = False
        context.user_data["investigation_address"] = address

        # Send Stars invoice
        await update.message.reply_invoice(
            title="Расследование от Кейса Уокера",
            description=f"Проверка адреса: {address[:100]}",
            payload=f"investigate_{update.effective_user.id}_{address[:100]}",
            currency="XTR",  # Telegram Stars currency code
            prices=[LabeledPrice("Расследование", INVESTIGATION_PRICE_STARS)],
        )

    async def pre_checkout_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle pre-checkout query - approve the payment."""
        query = update.pre_checkout_query
        await query.answer(ok=True)

    async def successful_payment_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle successful Stars payment - create investigation order."""
        payment = update.message.successful_payment
        user = update.effective_user
        address = context.user_data.get("investigation_address", "")

        if not address:
            # Try to extract from payload
            payload = payment.invoice_payload or ""
            parts = payload.split("_", 2)
            if len(parts) >= 3:
                address = parts[2]

        # Save to database
        if self.db:
            order_id = await self.db.create_investigation(
                user_id=user.id,
                username=user.username or str(user.id),
                address=address,
                stars_paid=payment.total_amount,
                telegram_payment_id=payment.telegram_payment_charge_id or "",
            )
        else:
            order_id = 0

        await update.message.reply_text(
            f"🕵️ Расследование #{order_id} принято!\n\n"
            f"Адрес: {address}\n"
            f"Оплачено: {payment.total_amount} ⭐\n\n"
            f"Кейс Уокер берётся за дело. "
            f"Отчёт будет готов в течение 24 часов.\n\n"
            f"Следи за обновлениями!",
            reply_markup=self._main_keyboard(),
        )

        # Notify admins about new order
        for admin_id in self.admin_chat_ids:
            try:
                bot = Bot(token=self.bot_token)
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🚨 Новый заказ расследования #{order_id}\n\n"
                        f"Пользователь: @{user.username or user.id}\n"
                        f"Адрес: {address}\n"
                        f"Оплата: {payment.total_amount} ⭐\n"
                        f"Срок: 24 часа"
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        context.user_data.pop("investigation_address", None)

    # --- Admin reply to user ---

    async def callback_reply_to_user(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle admin 'Reply' button - ask admin to type a reply."""
        query = update.callback_query
        if not self._is_admin(query.from_user.id):
            await query.answer("Только для админов")
            return

        await query.answer()

        # Extract user_id from callback_data "reply_123456"
        target_user_id = int(query.data.replace("reply_", ""))
        context.user_data["reply_to_user_id"] = target_user_id

        await query.message.reply_text(
            f"💬 Напиши ответ для пользователя (ID: {target_user_id}).\n"
            f"Следующее твоё сообщение будет отправлено ему от имени бота.",
        )

    async def handle_admin_reply(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle admin's reply text and send it to the user."""
        target_user_id = context.user_data.get("reply_to_user_id")
        if not target_user_id:
            return False
        if not self._is_admin(update.effective_user.id):
            return False

        context.user_data.pop("reply_to_user_id", None)
        reply_text = update.message.text.strip()

        try:
            bot = Bot(token=self.bot_token)
            await bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"🕵️ Ответ от Кейса Уокера:\n\n"
                    f"{reply_text}"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "✉️ Написать ещё",
                        callback_data="contact",
                    )],
                ]),
            )
            await update.message.reply_text(
                f"✅ Ответ отправлен пользователю {target_user_id}"
            )
        except Exception as e:
            logger.error(f"Failed to send reply to user {target_user_id}: {e}")
            await update.message.reply_text(
                f"Не удалось отправить ответ: {e}"
            )

        return True

    # --- Admin commands ---

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command (admin only)."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        if self._on_status:
            status = await self._on_status()
            await update.message.reply_text(status)
        else:
            await update.message.reply_text("Агент работает")

    async def cmd_force_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /post command (admin only)."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        if self._on_force_post:
            await update.message.reply_text("Генерирую пост...")
            result = await self._on_force_post()
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("Функция не подключена")

    async def cmd_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /orders command - list pending investigations (admin only)."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        if not self.db:
            await update.message.reply_text("БД не подключена")
            return

        orders = await self.db.get_pending_investigations()
        if not orders:
            await update.message.reply_text("Нет активных заказов")
            return

        text = "🔍 Активные расследования:\n\n"
        for o in orders:
            text += (
                f"#{o['id']} | @{o['username']} | {o['address'][:40]}\n"
                f"   Оплата: {o['stars_paid']} ⭐ | {o['created_at']}\n\n"
            )

        await update.message.reply_text(text)

    # --- Build application ---

    def build(self) -> Application:
        """Build the bot application with all handlers."""
        self.app = Application.builder().token(self.bot_token).build()

        # Public commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))

        # Inline button callbacks
        self.app.add_handler(
            CallbackQueryHandler(self.callback_investigate, pattern="^investigate$")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_random_article, pattern="^random_article$")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_aml_dictionary, pattern="^aml_dictionary$")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_dict_topic, pattern="^dict_")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_contact, pattern="^contact$")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_back_to_menu, pattern="^back_to_menu$")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_reply_to_user, pattern="^reply_")
        )

        # Payment handlers
        self.app.add_handler(PreCheckoutQueryHandler(self.pre_checkout_handler))
        self.app.add_handler(
            MessageHandler(
                filters.SUCCESSFUL_PAYMENT, self.successful_payment_handler
            )
        )

        # Text message handler (for address input, contact messages, admin replies)
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, self.handle_text_message
            )
        )

        # Admin commands
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("post", self.cmd_force_post))
        self.app.add_handler(CommandHandler("orders", self.cmd_orders))

        return self.app
