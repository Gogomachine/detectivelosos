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

# Investigation tiers (price in Telegram Stars)
INVESTIGATION_TIERS = {
    "basic": {"name": "Базовое", "price": 1000, "emoji": "🔍", "deadline": "24 часа",
              "desc": "Проверка адреса, основные связи, AML-скоринг"},
    "deep": {"name": "Глубокое", "price": 3000, "emoji": "🔬", "deadline": "24 часа",
             "desc": "Полный граф транзакций, цепочки переводов, связи с миксерами"},
    "urgent": {"name": "Срочное", "price": 5000, "emoji": "⚡", "deadline": "2 часа",
               "desc": "Приоритетная проверка + полный граф + рекомендации"},
}

# Binance referral link
BINANCE_REFERRAL_URL = "https://tinyurl.com/CaseWalker1"

# AML report description (what the user gets for Stars)
AML_REPORT_DESCRIPTION = (
    "📄 Что входит в AML-отчёт:\n\n"
    "• Адрес кошелька и сеть (Ethereum, Solana, Bitcoin и др.)\n"
    "• Риск скор (0–100) с визуальным индикатором\n"
    "• Финансовая сводка: баланс, принято, отправлено, кол-во транзакций\n"
    "• Первая и последняя активность по адресу\n"
    "• Анализ рисков Incoming: категории (Sanction list, Hack, Exchange, "
    "Gambling и др.) с процентами и суммами в USD\n"
    "• Анализ рисков Outgoing: категории (Sanction list, Hack, Mixing "
    "service, Suspicious и др.) с процентами и суммами в USD\n"
    "• Список токенов на кошельке с балансами\n"
    "• Экспертный обзор от Case Walker Bot с выводами и рекомендациями\n"
    "• Статус OFAC санкций (при наличии)\n\n"
    "Отчёт оформлен в фирменном стиле Case Walker Investigation."
)

# Conversation states
WAITING_ADDRESS = 1

def _split_text(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split text into parts respecting a character limit."""
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_pos = text.rfind("\n\n", 0, limit)
        if split_pos == -1:
            split_pos = text.rfind("\n", 0, limit)
        if split_pos == -1:
            split_pos = limit
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    return parts


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
        self._bot_username: str | None = None

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(token=self.bot_token)
        return self._bot

    async def _get_bot_keyboard(self) -> InlineKeyboardMarkup:
        """Get inline keyboard with bot link button."""
        if self._bot_username is None:
            me = await self.bot.get_me()
            self._bot_username = me.username
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Бот Кейса", url=f"https://t.me/{self._bot_username}")],
        ])

    async def publish_post(self, text: str) -> int | None:
        """Publish a post to the Telegram channel with bot link button."""
        try:
            keyboard = await self._get_bot_keyboard()
            parts = self._split_message(text)
            message_id = None

            for i, part in enumerate(parts):
                # Add bot button only to the last part
                reply_markup = keyboard if i == len(parts) - 1 else None
                message = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=part,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_markup=reply_markup,
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
        self._on_admin_chat = None

    def set_callbacks(
        self, on_force_post=None, on_status=None, on_explain_term=None,
        on_admin_chat=None,
    ):
        """Set callback functions for admin commands."""
        self._on_force_post = on_force_post
        self._on_status = on_status
        self._on_admin_chat = on_admin_chat
        self._on_explain_term = on_explain_term

    def _is_admin(self, user_id: int) -> bool:
        if not self.admin_chat_ids:
            return True
        return user_id in self.admin_chat_ids

    async def _check_banned(self, update: Update) -> bool:
        """Check if user is banned. Returns True if banned (and sends message)."""
        user = update.effective_user
        if not user or not self.db:
            return False
        if self._is_admin(user.id):
            return False
        if await self.db.is_user_banned(user.id):
            text = (
                "🚫 Ваш аккаунт заблокирован.\n\n"
                "Вы не можете использовать бота. "
                "Ожидайте разбана или сообщения от администратора."
            )
            if update.callback_query:
                await update.callback_query.answer(text, show_alert=True)
            elif update.message:
                await update.message.reply_text(text)
            return True
        return False

    # --- Main menu ---

    def _main_keyboard(self) -> InlineKeyboardMarkup:
        """Build the main menu keyboard."""
        buttons = [
            [InlineKeyboardButton(
                "🔍 Заказать расследование",
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
            [
                InlineKeyboardButton(
                    "✉️ Связаться",
                    callback_data="contact",
                ),
                InlineKeyboardButton(
                    "☕ Поддержать Кейса",
                    callback_data="donate",
                ),
            ],
            [InlineKeyboardButton(
                "🛡 Кейс доверяет: Binance",
                url=BINANCE_REFERRAL_URL,
            )],
            [InlineKeyboardButton(
                "🏢 Бюро",
                url=f"https://t.me/{TELEGRAM_CHANNEL_ID.lstrip('@')}",
            )],
        ]
        return InlineKeyboardMarkup(buttons)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start - show main menu."""
        if await self._check_banned(update):
            return
        await update.message.reply_text(
            "🕵️ Привет! Я Кейс Уокер - крипто-детектив и AML-журналист.\n\n"
            "Хожу по делам, раскапываю схемы отмывания "
            "и рассказываю об этом простым языком.\n\n"
            "📅 Расписание канала (МСК):\n"
            "09:00 - Утренняя сводка новостей\n"
            "10:00 - Пост про безопасность / AML\n"
            "13:00 - Разбор кейса или расследование\n"
            "15:00 - Дневная сводка новостей\n"
            "17:00 - Авторский пост\n"
            "20:00 - Вечерняя сводка + итоги дня\n\n"
            "🤖 Что умеет этот бот:\n"
            "🔍 Заказать расследование адреса\n"
            "📚 AML-словарь с объяснениями\n"
            "📰 Случайная статья из базы\n"
            "✉️ Написать детективу лично\n\n"
            "☕ Если нравится то, что я делаю - "
            "можешь поддержать проект через Telegram Stars! "
            "Каждая звезда помогает копать глубже.",
            reply_markup=self._main_keyboard(),
        )

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu - show main menu again."""
        if await self._check_banned(update):
            return
        await update.message.reply_text(
            "🕵️ Главное меню Кейса Уокера:",
            reply_markup=self._main_keyboard(),
        )

    # --- Random article ---

    async def callback_random_article(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle 'Хочу статью' button press."""
        if await self._check_banned(update):
            return
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
        if await self._check_banned(update):
            return
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
        if await self._check_banned(update):
            return
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
        if await self._check_banned(update):
            return
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
        if await self._check_banned(update):
            return
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
                    [
                        InlineKeyboardButton(
                            "🚫 Забанить",
                            callback_data=f"ban_{user.id}",
                        ),
                        InlineKeyboardButton(
                            "✅ Разбанить",
                            callback_data=f"unban_{user.id}",
                        ),
                    ],
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
        """Handle 'Заказать расследование' - show tier selection."""
        if await self._check_banned(update):
            return
        query = update.callback_query
        await query.answer()

        text = (
            "🔍 Заказать расследование\n\n"
            "Кейс Уокер лично проведёт проверку по указанному адресу "
            "(кошелёк, компания, контрагент).\n\n"
            f"{AML_REPORT_DESCRIPTION}\n\n"
            "Выбери тариф:\n\n"
        )
        for tier_id, tier in INVESTIGATION_TIERS.items():
            text += (
                f"{tier['emoji']} {tier['name']} - {tier['price']} ⭐\n"
                f"   {tier['desc']}\n"
                f"   Срок: {tier['deadline']}\n\n"
            )

        buttons = [
            [InlineKeyboardButton(
                f"{t['emoji']} {t['name']} ({t['price']} ⭐)",
                callback_data=f"tier_{tid}",
            )]
            for tid, t in INVESTIGATION_TIERS.items()
        ]
        buttons.append([
            InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
        ])

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def callback_select_tier(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle tier selection - ask for address."""
        if await self._check_banned(update):
            return
        query = update.callback_query
        await query.answer()

        tier_id = query.data.replace("tier_", "")
        tier = INVESTIGATION_TIERS.get(tier_id)
        if not tier:
            await query.edit_message_text("Неизвестный тариф",
                                          reply_markup=self._main_keyboard())
            return

        context.user_data["investigation_tier"] = tier_id
        context.user_data["awaiting_address"] = True

        await query.edit_message_text(
            f"{tier['emoji']} {tier['name']} расследование ({tier['price']} ⭐)\n\n"
            f"{tier['desc']}\n"
            f"Срок: {tier['deadline']}\n\n"
            f"Отправь мне адрес для проверки (текстовым сообщением):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад к тарифам", callback_data="investigate")],
            ]),
        )

    async def handle_photo_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle photo messages (admin reply with photo)."""
        if not context.user_data.get("reply_to_user_id"):
            return
        if not self._is_admin(update.effective_user.id):
            return
        await self.handle_admin_reply(update, context)

    async def handle_text_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Route incoming text messages to the correct handler."""
        # 0. Check ban (skip for admin actions)
        if not self._is_admin(update.effective_user.id):
            if await self._check_banned(update):
                return

        # 1. Admin reply to user
        if context.user_data.get("reply_to_user_id"):
            await self.handle_admin_reply(update, context)
            return

        # 2. Admin AI chat mode
        if await self.handle_admin_ai_message(update, context):
            return

        # 3. Contact message from user
        if context.user_data.get("awaiting_contact_message"):
            await self.handle_contact_message(update, context)
            return

        # 4. Investigation address
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

        # Get tier price
        tier_id = context.user_data.get("investigation_tier", "basic")
        tier = INVESTIGATION_TIERS.get(tier_id, INVESTIGATION_TIERS["basic"])

        # Send Stars invoice
        await update.message.reply_invoice(
            title=f"{tier['emoji']} {tier['name']} расследование",
            description=f"Проверка адреса: {address[:80]}\n{tier['desc']}",
            payload=f"investigate_{tier_id}_{update.effective_user.id}_{address[:80]}",
            currency="XTR",
            prices=[LabeledPrice(tier["name"], tier["price"])],
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
        """Handle successful Stars payment - investigation or donation."""
        payment = update.message.successful_payment
        user = update.effective_user
        payload = payment.invoice_payload or ""

        # --- Donation ---
        if payload.startswith("donate_"):
            await update.message.reply_text(
                f"🕵️ Спасибо за поддержку! {payment.total_amount} ⭐ получены.\n\n"
                "Кейс Уокер ценит каждого, кто помогает бороться "
                "с грязными деньгами. Твоя поддержка - мотивация "
                "копать ещё глубже!",
                reply_markup=self._main_keyboard(),
            )
            logger.info(
                f"Donation received: {payment.total_amount} Stars "
                f"from @{user.username or user.id}"
            )
            return

        # --- Investigation ---
        address = context.user_data.get("investigation_address", "")
        tier_id = context.user_data.get("investigation_tier", "basic")
        tier = INVESTIGATION_TIERS.get(tier_id, INVESTIGATION_TIERS["basic"])

        if not address:
            # Try to extract from payload: investigate_tier_userid_address
            parts = payload.split("_", 3)
            if len(parts) >= 4:
                address = parts[3]
                tier_id = parts[1]
                tier = INVESTIGATION_TIERS.get(tier_id, INVESTIGATION_TIERS["basic"])

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
            f"Тариф: {tier['emoji']} {tier['name']}\n"
            f"Адрес: {address}\n"
            f"Оплачено: {payment.total_amount} ⭐\n"
            f"Срок: {tier['deadline']}\n\n"
            f"Кейс Уокер берётся за дело. "
            f"Отчёт придёт прямо сюда!",
            reply_markup=self._main_keyboard(),
        )

        # Notify admins about new order
        for admin_id in self.admin_chat_ids:
            try:
                bot = Bot(token=self.bot_token)
                admin_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "💬 Ответить",
                        callback_data=f"reply_{user.id}",
                    )],
                    [
                        InlineKeyboardButton(
                            "🚫 Забанить",
                            callback_data=f"ban_{user.id}",
                        ),
                        InlineKeyboardButton(
                            "✅ Разбанить",
                            callback_data=f"unban_{user.id}",
                        ),
                    ],
                ])
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🚨 Новый заказ расследования #{order_id}\n\n"
                        f"Тариф: {tier['emoji']} {tier['name']}\n"
                        f"Пользователь: @{user.username or user.id}\n"
                        f"Адрес: {address}\n"
                        f"Оплата: {payment.total_amount} ⭐\n"
                        f"Срок: {tier['deadline']}"
                    ),
                    reply_markup=admin_keyboard,
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        context.user_data.pop("investigation_address", None)
        context.user_data.pop("investigation_tier", None)

    # --- Donate ---

    async def callback_donate(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle 'Поддержать Кейса' button - show donation options."""
        if await self._check_banned(update):
            return
        query = update.callback_query
        await query.answer()

        buttons = [
            [InlineKeyboardButton(
                f"☕ {amount} ⭐",
                callback_data=f"donate_{amount}",
            ) for amount in [50, 100, 500]],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")],
        ]

        await query.edit_message_text(
            "☕ Поддержать Кейса Уокера\n\n"
            "Кейс работает на результат: парсит новости, "
            "разбирает кейсы, следит за санкциями.\n\n"
            "Если тебе полезен канал - можешь угостить "
            "детектива кофе. Любая сумма - мотивация!",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def callback_donate_amount(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle donation amount selection - send Stars invoice."""
        if await self._check_banned(update):
            return
        query = update.callback_query
        await query.answer()

        amount = int(query.data.replace("donate_", ""))

        await query.message.reply_invoice(
            title="Поддержка Кейса Уокера",
            description=f"Донат {amount} ⭐ на развитие канала и бота",
            payload=f"donate_{query.from_user.id}",
            currency="XTR",
            prices=[LabeledPrice("Поддержка", amount)],
        )

    # --- Admin ban/unban ---

    async def callback_ban_user(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle admin 'Ban' button."""
        query = update.callback_query
        if not self._is_admin(query.from_user.id):
            await query.answer("Только для админов")
            return

        target_user_id = int(query.data.replace("ban_", ""))

        if self.db:
            await self.db.ban_user(target_user_id, banned_by=query.from_user.id)

        await query.answer(f"Пользователь {target_user_id} забанен")
        await query.message.reply_text(
            f"🚫 Пользователь {target_user_id} забанен.\n"
            f"Он больше не может использовать бота."
        )

    async def callback_unban_user(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle admin 'Unban' button."""
        query = update.callback_query
        if not self._is_admin(query.from_user.id):
            await query.answer("Только для админов")
            return

        target_user_id = int(query.data.replace("unban_", ""))

        if self.db:
            await self.db.unban_user(target_user_id)

        await query.answer(f"Пользователь {target_user_id} разбанен")
        await query.message.reply_text(
            f"✅ Пользователь {target_user_id} разбанен.\n"
            f"Теперь он снова может использовать бота."
        )

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
            f"Следующее твоё сообщение (текст или фото) будет отправлено ему от имени бота.",
        )

    async def handle_admin_reply(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle admin's reply (text or photo) and send it to the user."""
        target_user_id = context.user_data.get("reply_to_user_id")
        if not target_user_id:
            return False
        if not self._is_admin(update.effective_user.id):
            return False

        context.user_data.pop("reply_to_user_id", None)

        reply_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "✉️ Написать ещё",
                callback_data="contact",
            )],
        ])

        try:
            bot = Bot(token=self.bot_token)

            # Check if the message contains a photo
            if update.message.photo:
                photo = update.message.photo[-1]  # highest resolution
                caption = update.message.caption or ""
                caption_text = (
                    f"🕵️ Ответ от Кейса Уокера:\n\n{caption}" if caption
                    else "🕵️ Ответ от Кейса Уокера:"
                )
                await bot.send_photo(
                    chat_id=target_user_id,
                    photo=photo.file_id,
                    caption=caption_text,
                    reply_markup=reply_keyboard,
                )
            else:
                reply_text = (update.message.text or "").strip()
                await bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        f"🕵️ Ответ от Кейса Уокера:\n\n"
                        f"{reply_text}"
                    ),
                    reply_markup=reply_keyboard,
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

    async def cmd_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai command - enter AI chat mode (admin only)."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        context.user_data["admin_ai_chat"] = True
        await update.message.reply_text(
            "🤖 Режим AI-чата активирован.\n\n"
            "Теперь ты можешь писать мне любые сообщения - "
            "я отвечу как Кейс Уокер с учётом базы знаний и энциклопедии.\n\n"
            "Примеры:\n"
            "- Проанализируй и сделай краткую новость по этой ссылке: ...\n"
            "- Напиши пост про Lazarus Group\n"
            "- Что ты знаешь про chain hopping?\n\n"
            "Команды:\n"
            "/remember Тема | Текст - добавить в базу знаний\n"
            "/kb - посмотреть базу знаний\n"
            "/kbdel 123 - удалить запись из базы\n"
            "/stop - выйти из режима AI-чата",
        )

    async def cmd_stop_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command - exit AI chat mode (admin only)."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        context.user_data.pop("admin_ai_chat", None)
        await update.message.reply_text(
            "🔒 Режим AI-чата отключён. Я снова в обычном режиме.",
        )

    async def cmd_remember(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remember command - add entry to knowledge base (admin only).

        Format: /remember Тема | Содержание
        """
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        if not self.db:
            await update.message.reply_text("БД не подключена")
            return

        text = (update.message.text or "").replace("/remember", "", 1).strip()
        if "|" not in text:
            await update.message.reply_text(
                "Формат: /remember Тема | Содержание\n\n"
                "Пример:\n/remember Lazarus 2025 | В марте 2025 Lazarus Group "
                "отмыла $1.4B через Thorchain после взлома Bybit.",
            )
            return

        topic, content = text.split("|", 1)
        topic = topic.strip()
        content = content.strip()

        if not topic or not content:
            await update.message.reply_text("Тема и содержание не могут быть пустыми.")
            return

        kb_id = await self.db.add_knowledge(
            topic=topic,
            content=content,
            added_by=update.effective_user.id,
        )
        await update.message.reply_text(
            f"✅ Добавлено в базу знаний (#{kb_id}):\n\n"
            f"Тема: {topic}\n"
            f"Содержание: {content[:200]}{'...' if len(content) > 200 else ''}",
        )

    async def cmd_kb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /kb command - list knowledge base entries (admin only)."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        if not self.db:
            await update.message.reply_text("БД не подключена")
            return

        entries = await self.db.get_all_knowledge()
        if not entries:
            await update.message.reply_text(
                "📚 База знаний пуста.\n\n"
                "Добавь запись:\n/remember Тема | Содержание",
            )
            return

        text = "📚 База знаний:\n\n"
        for e in entries[:30]:
            content_preview = e["content"][:80]
            text += (
                f"#{e['id']} | {e['topic']}\n"
                f"   {content_preview}{'...' if len(e['content']) > 80 else ''}\n\n"
            )
        if len(entries) > 30:
            text += f"... и ещё {len(entries) - 30} записей"

        await update.message.reply_text(text)

    async def cmd_kbdel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /kbdel command - delete knowledge base entry (admin only)."""
        if not update.effective_user or not self._is_admin(update.effective_user.id):
            return
        if not self.db:
            await update.message.reply_text("БД не подключена")
            return

        text = (update.message.text or "").replace("/kbdel", "", 1).strip()
        if not text.isdigit():
            await update.message.reply_text("Формат: /kbdel 123")
            return

        kb_id = int(text)
        await self.db.delete_knowledge(kb_id)
        await update.message.reply_text(f"🗑 Запись #{kb_id} удалена из базы знаний.")

    async def handle_admin_ai_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Handle admin message in AI chat mode. Returns True if handled."""
        if not context.user_data.get("admin_ai_chat"):
            return False
        if not self._is_admin(update.effective_user.id):
            return False
        if not self._on_admin_chat:
            await update.message.reply_text(
                "AI-чат не подключён. Перезапусти бота."
            )
            return True

        message = (update.message.text or "").strip()
        if not message:
            return True

        await update.message.reply_text("🔄 Думаю...")

        try:
            response = await self._on_admin_chat(message)
            # Split long responses
            parts = _split_text(response, MAX_MESSAGE_LENGTH)
            for part in parts:
                await update.message.reply_text(part)
        except Exception as e:
            logger.error(f"Admin AI chat error: {e}")
            await update.message.reply_text(f"Ошибка: {e}")

        return True

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
            CallbackQueryHandler(self.callback_select_tier, pattern="^tier_")
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
            CallbackQueryHandler(self.callback_donate, pattern="^donate$")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_donate_amount, pattern="^donate_")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_back_to_menu, pattern="^back_to_menu$")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_reply_to_user, pattern="^reply_")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_ban_user, pattern="^ban_")
        )
        self.app.add_handler(
            CallbackQueryHandler(self.callback_unban_user, pattern="^unban_")
        )

        # Payment handlers
        self.app.add_handler(PreCheckoutQueryHandler(self.pre_checkout_handler))
        self.app.add_handler(
            MessageHandler(
                filters.SUCCESSFUL_PAYMENT, self.successful_payment_handler
            )
        )

        # Photo handler (admin reply with photo)
        self.app.add_handler(
            MessageHandler(filters.PHOTO, self.handle_photo_message)
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
        self.app.add_handler(CommandHandler("ai", self.cmd_ai))
        self.app.add_handler(CommandHandler("stop", self.cmd_stop_ai))
        self.app.add_handler(CommandHandler("remember", self.cmd_remember))
        self.app.add_handler(CommandHandler("kb", self.cmd_kb))
        self.app.add_handler(CommandHandler("kbdel", self.cmd_kbdel))

        return self.app
