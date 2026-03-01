"""
Main AML Detective Agent orchestrator.
Coordinates all components: parsing, content generation, database, and publishing.

Daily schedule (Moscow time):
  09:00 - Morning News (max 7 articles, AML professional opinion)
  10:00 - Mini Post (security/AML educational)
  13:00 - Deep Dive (crypto networks, AML incidents analysis)
  15:00 - Afternoon News (max 7 articles, AML professional opinion)
  17:00 - Author's Post (free-form, personal)
  20:00 - Evening News (max 7 articles, daily summary, good night)
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp

from config.sources import RSS_FEEDS, SCRAPE_SOURCES
from src.content.generator import ContentGenerator
from src.database.db import Database
from src.parsers.news_filter import NewsFilter
from src.parsers.rss_parser import RSSParser
from src.parsers.web_scraper import WebScraper
from src.scheduler.scheduler import AgentScheduler
from src.telegram_bot.bot import BINANCE_REFERRAL_URL, TelegramPublisher, UserBot

logger = logging.getLogger(__name__)

MIN_DAILY_POSTS = 6


class CaseWalkerAgent:
    """
    The main AML Detective Agent.
    Orchestrates news monitoring, content creation, and channel management.
    """

    def __init__(self, admin_chat_ids: list[int] | None = None):
        self.db = Database()
        self.generator = ContentGenerator()
        self.publisher = TelegramPublisher()
        self.user_bot = UserBot(db=self.db, admin_chat_ids=admin_chat_ids or [])
        self.scheduler = AgentScheduler()
        self.news_filter = NewsFilter()
        self._http_session: aiohttp.ClientSession | None = None
        self._running = False

    async def start(self):
        """Initialize and start the agent."""
        logger.info("Кейс Уокер выходит на дело...")

        # Initialize components
        await self.db.connect()
        self._http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "CaseWalker AML Bot/1.0"},
        )

        # Configure scheduler callbacks
        self.scheduler.set_callbacks(
            on_parse_news=self.parse_all_news,
            on_morning_news=lambda: self.generate_and_publish_news_briefing("morning"),
            on_mini_post=self.generate_and_publish_mini_post,
            on_deep_dive=self.generate_and_publish_deep_dive,
            on_afternoon_news=lambda: self.generate_and_publish_news_briefing("afternoon"),
            on_author_post=self.generate_and_publish_author_post,
            on_evening_news=lambda: self.generate_and_publish_news_briefing("evening"),
            on_bot_reminder=self.publish_bot_reminder,
        )
        self.scheduler.setup()
        self.scheduler.start()

        # Configure user bot callbacks
        self.user_bot.db = self.db
        self.user_bot.set_callbacks(
            on_force_post=lambda: self.generate_and_publish_mini_post(
                "Red flags при крипто-транзакциях: топ-5"
            ),
            on_status=self.get_status,
            on_explain_term=self.explain_aml_term,
        )

        # Run initial news fetch
        await self.parse_all_news()

        self._running = True
        logger.info("Кейс Уокер на линии, дела ждут!")

    async def stop(self):
        """Gracefully stop the agent."""
        logger.info("Кейс Уокер уходит на перерыв...")
        self._running = False
        self.scheduler.stop()
        if self._http_session:
            await self._http_session.close()
        await self.db.close()
        logger.info("Кейс Уокер остановлен.")

    # --- Core Operations ---

    async def parse_all_news(self):
        """Fetch and process news from all sources."""
        logger.info("Начинаю парсинг новостей...")

        rss_parser = RSSParser(session=self._http_session)
        web_scraper = WebScraper(session=self._http_session)

        # Build fetch tasks (RSS + web)
        tasks = [
            rss_parser.fetch_all_feeds(RSS_FEEDS),
            web_scraper.scrape_all(SCRAPE_SOURCES),
        ]
        task_names = ["RSS", "Web"]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        all_items = []
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                logger.error(f"{name} parsing failed: {result}")
            else:
                all_items.extend(result)

        if not all_items:
            logger.warning("Нет новых новостей из источников")
            return 0

        # Filter for relevance (AML-native sources pass automatically)
        filtered = self.news_filter.filter_and_rank(all_items)

        if not filtered:
            logger.warning("После фильтрации не осталось релевантных статей")
            await self.db.set_state("last_parse", datetime.now(timezone.utc).isoformat())
            return 0

        # Save to database
        saved_count = 0
        duplicate_count = 0
        for item in filtered:
            score = self.news_filter.calculate_relevance_score(item)
            article_id = await self.db.save_article(
                content_hash=item.content_hash,
                title=item.title,
                url=item.url,
                content=item.content,
                source=item.source,
                category=item.category,
                language=item.language,
                relevance_score=score,
                published_at=item.published_at,
            )
            if article_id is not None:
                saved_count += 1
            else:
                duplicate_count += 1

        logger.info(
            f"Сохранено {saved_count} новых статей из {len(filtered)} релевантных "
            f"({duplicate_count} уже в базе, {len(all_items)} найдено всего)"
        )
        await self.db.set_state("last_parse", datetime.now(timezone.utc).isoformat())
        return saved_count

    # --- News Briefings (09:00, 15:00, 20:00) ---

    async def generate_and_publish_news_briefing(self, time_of_day: str):
        """Generate and publish a news briefing (morning/afternoon/evening)."""
        # Get fresh unposted articles (max 7)
        articles = await self.db.get_diverse_unposted_articles(count=7)

        if not articles:
            logger.info(f"Нет непопубликованных статей для {time_of_day} сводки")
            articles = []

        # For evening - build daily summary from today's posts
        daily_summary = ""
        if time_of_day == "evening":
            posts_today = await self.db.get_posts_today()
            if posts_today:
                summaries = []
                for p in posts_today:
                    ptype = p.get("post_type", "")
                    content = p.get("content", "")[:150]
                    summaries.append(f"[{ptype}] {content}...")
                daily_summary = "\n".join(summaries)

        # Generate briefing
        post_text = await self.generator.generate_news_briefing(
            news_items=articles,
            time_of_day=time_of_day,
            daily_summary=daily_summary,
        )

        # Add Binance referral to evening post (unobtrusive)
        if time_of_day == "evening":
            post_text += (
                f"\n\n🛡 Безопасная торговля начинается с надёжной биржи. "
                f"Кейс доверяет: {BINANCE_REFERRAL_URL}"
            )

        # Save to DB
        article_ids = ",".join(str(a["id"]) for a in articles)
        post_type = f"news_{time_of_day}"
        post_id = await self.db.save_post(
            post_type=post_type,
            content=post_text,
            article_ids=article_ids,
            status="draft",
        )

        # Publish to Telegram
        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            for article in articles:
                await self.db.mark_article_posted(article["id"], post_id)
            label = {"morning": "Утренняя", "afternoon": "Дневная", "evening": "Вечерняя"}
            logger.info(f"{label.get(time_of_day, '')} сводка опубликована ({len(articles)} новостей)")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Mini Post (10:00) ---

    async def generate_and_publish_mini_post(self, topic: str):
        """Generate and publish a mini educational post about security/AML."""
        # Get used topics to avoid repetition
        used_topics = await self.db.get_used_topics("mini_post")

        post_text = await self.generator.generate_mini_post(
            topic=topic,
            used_topics=used_topics,
        )

        post_id = await self.db.save_post(
            post_type="mini_post",
            content=post_text,
            status="draft",
        )

        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            await self.db.save_used_topic(topic, "mini_post")
            logger.info(f"Мини-пост опубликован: {topic[:50]}")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Deep Dive (13:00) ---

    async def generate_and_publish_deep_dive(self, topic: str):
        """Generate and publish a deep dive analysis post."""
        used_topics = await self.db.get_used_topics("deep_dive")

        post_text = await self.generator.generate_deep_dive(
            topic=topic,
            used_topics=used_topics,
        )

        post_id = await self.db.save_post(
            post_type="deep_dive",
            content=post_text,
            status="draft",
        )

        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            await self.db.save_used_topic(topic, "deep_dive")
            logger.info(f"Разбор опубликован: {topic[:50]}")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Author's Post (17:00) ---

    async def generate_and_publish_author_post(self):
        """Generate and publish a free-form author's post."""
        used_topics = await self.db.get_used_topics("author_post")

        post_text = await self.generator.generate_author_post(
            used_topics=used_topics,
        )

        post_id = await self.db.save_post(
            post_type="author_post",
            content=post_text,
            status="draft",
        )

        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            # Save first line as topic marker to avoid repetition
            first_line = post_text.split("\n")[0][:100]
            await self.db.save_used_topic(first_line, "author_post")
            logger.info("Авторский пост опубликован")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Bot Reminder (12:00) ---

    async def publish_bot_reminder(self, message: str):
        """Publish a daily bot reminder to the channel with a link to the bot."""
        # Add inline button to open the bot
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        bot = self.publisher.bot
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Открыть бота", url=f"https://t.me/{(await bot.get_me()).username}")],
        ])

        try:
            msg = await bot.send_message(
                chat_id=self.publisher.channel_id,
                text=message,
                reply_markup=keyboard,
            )
            logger.info(f"Напоминание о боте опубликовано, msg_id={msg.message_id}")
        except Exception as e:
            logger.error(f"Ошибка публикации напоминания о боте: {e}")

    # --- Legacy methods (kept for /post command and manual use) ---

    async def generate_and_publish_combined_post(self, tip_topic: str) -> str:
        """Generate and publish a combined post: 3 news + AML tip."""
        articles = await self.db.get_diverse_unposted_articles(count=3)

        if not articles:
            logger.info("Нет непопубликованных статей для комбинированного поста")
            return "Нет новых статей для публикации"

        post_text = await self.generator.generate_combined_post(
            articles=articles,
            tip_topic=tip_topic,
        )

        article_ids = ",".join(str(a["id"]) for a in articles)
        post_id = await self.db.save_post(
            post_type="combined",
            content=post_text,
            article_ids=article_ids,
            status="draft",
        )

        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            for article in articles:
                await self.db.mark_article_posted(article["id"], post_id)
            logger.info(f"Комбинированный пост опубликован ({len(articles)} новостей + совет)")
            return f"Опубликовано: {len(articles)} новостей + AML-совет"
        else:
            await self.db.update_post_status(post_id, "failed")
            return "Ошибка публикации комбинированного поста"

    async def generate_and_publish_post(self) -> str:
        """Generate and publish a post from the best unposted article."""
        articles = await self.db.get_unposted_articles(limit=1)
        if not articles:
            logger.info("Нет непопубликованных статей")
            return "Нет новых статей для публикации"

        article = articles[0]

        content = article["content"] or ""
        if len(content) < 200:
            content = await self.generator.enrich_article(
                article["title"], content
            )

        post_text = await self.generator.generate_news_post(
            title=article["title"],
            content=content,
            source=article["source"],
            category=article["category"],
            url=article.get("url", ""),
        )

        post_id = await self.db.save_post(
            post_type="news",
            content=post_text,
            article_ids=str(article["id"]),
            status="draft",
        )

        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            await self.db.mark_article_posted(article["id"], post_id)
            logger.info(f"Опубликован пост: {article['title'][:50]}")
            return f"Опубликовано: {article['title'][:50]}"
        else:
            await self.db.update_post_status(post_id, "failed")
            return f"Ошибка публикации: {article['title'][:50]}"

    async def generate_and_publish_digest(self, is_morning: bool = True):
        """Generate and publish a digest (morning or evening). Legacy method."""
        since = datetime.now(timezone.utc) - timedelta(hours=12)
        articles = await self.db.get_articles_since(since)

        if not articles:
            logger.info("Нет статей для дайджеста")
            articles = [{"title": "Тишина на фронтах AML", "source": "Case Walker"}]

        digest_text = await self.generator.generate_digest(
            news_items=articles[:10],
            is_morning=is_morning,
        )

        article_ids = ",".join(str(a.get("id", "")) for a in articles[:10])
        post_id = await self.db.save_post(
            post_type="digest_morning" if is_morning else "digest_evening",
            content=digest_text,
            article_ids=article_ids,
            status="draft",
        )

        message_id = await self.publisher.publish_post(digest_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            time_label = "Утренний" if is_morning else "Вечерний"
            logger.info(f"{time_label} дайджест опубликован")
        else:
            await self.db.update_post_status(post_id, "failed")

    async def generate_and_publish_fun_fact(self, topic: str):
        """Generate and publish a fun AML fact."""
        post_text = await self.generator.generate_fun_fact(topic)

        post_id = await self.db.save_post(
            post_type="fun_fact",
            content=post_text,
            status="draft",
        )

        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            logger.info(f"Fun fact опубликован: {topic[:50]}")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Utility ---

    async def check_daily_quota(self) -> int:
        """Check if minimum daily post count is met."""
        count = await self.db.get_post_count_today()
        needed = max(0, MIN_DAILY_POSTS - count)
        if needed > 0:
            logger.info(f"Опубликовано {count}/{MIN_DAILY_POSTS} постов. Нужно ещё {needed}")
        else:
            logger.info(f"Дневная квота выполнена: {count} постов")
        return needed

    async def explain_aml_term(self, term: str) -> str:
        """Explain an AML term using the encyclopedia knowledge base."""
        return await self.generator.explain_term(term)

    async def get_status(self) -> str:
        """Get agent status report."""
        posts_today = await self.db.get_post_count_today()
        articles_today = await self.db.get_article_count_today()
        last_parse = await self.db.get_state("last_parse", "никогда")
        next_runs = self.scheduler.get_next_runs()

        next_runs_text = "\n".join(
            f"  - {j['name']}: {j['next_run']}" for j in next_runs[:8]
        )

        return (
            f"Статус Кейса Уокера\n\n"
            f"Сегодня:\n"
            f"  - Постов: {posts_today}/{MIN_DAILY_POSTS}\n"
            f"  - Статей в базе: {articles_today}\n"
            f"  - Последний парсинг: {last_parse}\n\n"
            f"Расписание (МСК):\n"
            f"  09:00 - Утренние новости\n"
            f"  10:00 - Мини-пост\n"
            f"  13:00 - Разбор\n"
            f"  15:00 - Дневные новости\n"
            f"  17:00 - Авторский пост\n"
            f"  20:00 - Вечерние новости\n\n"
            f"Ближайшие задачи:\n{next_runs_text}"
        )

    async def run_forever(self):
        """Run the agent indefinitely."""
        await self.start()

        # Build and start user bot (polling)
        bot_app = self.user_bot.build()
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        logger.info("Telegram бот запущен (polling)")

        try:
            while self._running:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Получен сигнал остановки")
        finally:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
            await self.stop()
