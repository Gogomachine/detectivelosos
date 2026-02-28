"""
Main AML Detective Agent orchestrator.
Coordinates all components: parsing, content generation, database, and publishing.
"""

import asyncio
import json
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
from src.telegram_bot.bot import TelegramPublisher, UserBot

logger = logging.getLogger(__name__)

MIN_DAILY_POSTS = 5


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
        logger.info("🕵️ Кейс Уокер выходит на дело...")

        # Initialize components
        await self.db.connect()
        self._http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "CaseWalker AML Bot/1.0"},
        )

        # Configure scheduler callbacks
        self.scheduler.set_callbacks(
            on_parse_news=self.parse_all_news,
            on_combined_post=self.generate_and_publish_combined_post,
            on_morning_digest=lambda: self.generate_and_publish_digest(is_morning=True),
            on_evening_digest=lambda: self.generate_and_publish_digest(is_morning=False),
        )
        self.scheduler.setup()
        self.scheduler.start()

        # Configure user bot callbacks
        self.user_bot.db = self.db
        self.user_bot.set_callbacks(
            on_force_post=lambda: self.generate_and_publish_combined_post("Red flags при крипто-транзакциях: топ-5"),
            on_status=self.get_status,
            on_explain_term=self.explain_aml_term,
        )

        # Run initial news fetch
        await self.parse_all_news()

        self._running = True
        logger.info("✅ Кейс Уокер на линии, дела ждут!")

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

    async def generate_and_publish_combined_post(self, tip_topic: str) -> str:
        """Generate and publish a combined post: 3 news + AML tip."""
        # Get up to 3 unposted articles from different sources
        articles = await self.db.get_diverse_unposted_articles(count=3)

        if not articles:
            logger.info("Нет непопубликованных статей для комбинированного поста")
            return "Нет новых статей для публикации"

        # Generate combined post
        post_text = await self.generator.generate_combined_post(
            articles=articles,
            tip_topic=tip_topic,
        )

        # Save to DB
        article_ids = ",".join(str(a["id"]) for a in articles)
        post_id = await self.db.save_post(
            post_type="combined",
            content=post_text,
            article_ids=article_ids,
            status="draft",
        )

        # Publish to Telegram
        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            # Mark all articles as posted
            for article in articles:
                await self.db.mark_article_posted(article["id"], post_id)
            titles = ", ".join(a["title"][:30] for a in articles)
            logger.info(f"Комбинированный пост опубликован ({len(articles)} новостей + совет)")
            return f"✅ Опубликовано: {len(articles)} новостей + AML-совет"
        else:
            await self.db.update_post_status(post_id, "failed")
            return f"❌ Ошибка публикации комбинированного поста"

    async def generate_and_publish_post(self) -> str:
        """Generate and publish a post from the best unposted article."""
        articles = await self.db.get_unposted_articles(limit=1)
        if not articles:
            logger.info("Нет непопубликованных статей")
            return "Нет новых статей для публикации"

        article = articles[0]

        # If content is too short, enrich it
        content = article["content"] or ""
        if len(content) < 200:
            content = await self.generator.enrich_article(
                article["title"], content
            )

        # Generate post
        post_text = await self.generator.generate_news_post(
            title=article["title"],
            content=content,
            source=article["source"],
            category=article["category"],
            url=article.get("url", ""),
        )

        # Save to DB
        post_id = await self.db.save_post(
            post_type="news",
            content=post_text,
            article_ids=str(article["id"]),
            status="draft",
        )

        # Publish to Telegram
        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            await self.db.mark_article_posted(article["id"], post_id)
            logger.info(f"Опубликован пост: {article['title'][:50]}")
            return f"✅ Опубликовано: {article['title'][:50]}"
        else:
            await self.db.update_post_status(post_id, "failed")
            return f"❌ Ошибка публикации: {article['title'][:50]}"

    async def generate_and_publish_digest(self, is_morning: bool = True):
        """Generate and publish a digest (morning or evening)."""
        # Get articles from the relevant period
        if is_morning:
            # Evening articles (previous day 19:00 to today 07:00)
            since = datetime.now(timezone.utc) - timedelta(hours=12)
        else:
            # Daytime articles (today 07:00 to 19:00)
            since = datetime.now(timezone.utc) - timedelta(hours=12)

        articles = await self.db.get_articles_since(since)

        if not articles:
            logger.info("Нет статей для дайджеста")
            articles = [{"title": "Тишина на фронтах AML", "source": "Case Walker"}]

        # Generate digest
        digest_text = await self.generator.generate_digest(
            news_items=articles[:10],  # Top 10 for digest
            is_morning=is_morning,
        )

        # Save and publish
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

    async def check_daily_quota(self) -> int:
        """Check if minimum daily post count is met. Returns posts still needed."""
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
            f"  • {j['name']}: {j['next_run']}" for j in next_runs[:5]
        )

        return (
            f"🕵️ Статус Кейса Уокера\n\n"
            f"📊 Сегодня:\n"
            f"  • Постов: {posts_today}/{MIN_DAILY_POSTS}\n"
            f"  • Статей в базе: {articles_today}\n"
            f"  • Последний парсинг: {last_parse}\n\n"
            f"⏰ Ближайшие задачи:\n{next_runs_text}"
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
