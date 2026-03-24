"""
Main AML Detective Agent orchestrator.
Coordinates all components: parsing, content generation, database, and publishing.

Weekly schedule (Moscow time):
  Mon: 09:00 News | 13:00 Security     | 19:00 Evening News + Expert Opinion
  Tue: 09:00 News | 13:00 Hack Article | 19:00 Evening News + Expert Opinion
  Wed: 09:00 News |                     | 19:00 Evening News + Expert Opinion
  Thu: 09:00 News | 15:00 Random Art    | 19:00 Evening News + Expert Opinion
  Fri: 09:00 News |                     | 19:00 Evening News + Expert Opinion
  Sat: 09:00 News |                     | 19:00 Evening News + Expert Opinion
  Sun: 09:00 News | 18:00 Weekly Summary + Expert Opinion

Deep dives and authored articles are created manually by admin via /ai command.
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone

import aiohttp

from config.sources import RSS_FEEDS, SCRAPE_SOURCES
from src.content.generator import ContentGenerator
from src.database.db import Database
from src.parsers.news_filter import NewsFilter
from src.parsers.rss_parser import RSSParser
from src.parsers.web_scraper import WebScraper
from src.scheduler.scheduler import (
    HACK_ARTICLE_TOPICS,
    SECURITY_POST_TOPICS,
    AgentScheduler,
)
from src.telegram_bot.bot import BINANCE_REFERRAL_URL, TelegramPublisher, UserBot

logger = logging.getLogger(__name__)

MIN_DAILY_POSTS = 3
NEWS_HEADER_IMAGE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "news_header.jpg",
)


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
            on_evening_news=lambda: self.generate_and_publish_news_briefing("evening"),
            on_security_post=self.generate_and_publish_security_post,
            on_hack_article=self.generate_and_publish_hack_article,
            on_random_article=self.generate_and_publish_random_article,
            on_weekly_summary=self.generate_and_publish_weekly_summary,
        )
        self.scheduler.setup()
        self.scheduler.start()

        # Configure user bot callbacks
        self.user_bot.db = self.db
        self.user_bot.set_callbacks(
            on_force_post=lambda: self.generate_and_publish_security_post(
                "Red flags при крипто-транзакциях: топ-5"
            ),
            on_status=self.get_status,
            on_explain_term=self.explain_aml_term,
            on_admin_chat=self.handle_admin_chat,
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

    # --- Topic Selection ---

    @staticmethod
    def _pick_unused_topic(all_topics: list[str], used_topics: list[str]) -> str:
        """Pick a random topic that hasn't been used yet.

        If all topics have been used, resets and picks from the full list.
        """
        available = [t for t in all_topics if t not in used_topics]
        if not available:
            # All topics exhausted — reset by picking from full list
            available = list(all_topics)
        return random.choice(available)

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

    # --- News Briefings (09:00, 19:00) ---

    async def generate_and_publish_news_briefing(self, time_of_day: str):
        """Generate and publish a news briefing (morning/evening)."""
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

        # Publish to Telegram (with news header image if available)
        if os.path.isfile(NEWS_HEADER_IMAGE):
            message_id = await self.publisher.publish_post_with_photo(
                post_text, NEWS_HEADER_IMAGE,
            )
        else:
            message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            for article in articles:
                await self.db.mark_article_posted(article["id"], post_id)
            label = {"morning": "Утренняя", "afternoon": "Дневная", "evening": "Вечерняя"}
            logger.info(f"{label.get(time_of_day, '')} сводка опубликована ({len(articles)} новостей)")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Security Post (Mon 13:00) ---

    async def generate_and_publish_security_post(self, topic: str | None = None):
        """Generate and publish a security/AML educational post."""
        used_topics = await self.db.get_used_topics("security_post")
        if topic is None:
            topic = self._pick_unused_topic(SECURITY_POST_TOPICS, used_topics)

        post_text = await self.generator.generate_mini_post(
            topic=topic, used_topics=used_topics,
        )

        post_id = await self.db.save_post(
            post_type="security_post", content=post_text, status="draft",
        )
        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            await self.db.save_used_topic(topic, "security_post")
            logger.info(f"Пост про безопасность опубликован: {topic[:50]}")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Hack Article (Tue/Fri 13:00) ---

    async def generate_and_publish_hack_article(self, topic: str | None = None):
        """Generate and publish an article about a crypto hack."""
        used_topics = await self.db.get_used_topics("hack_article")
        if topic is None:
            topic = self._pick_unused_topic(HACK_ARTICLE_TOPICS, used_topics)

        post_text = await self.generator.generate_hack_article(
            topic=topic, used_topics=used_topics,
        )

        post_id = await self.db.save_post(
            post_type="hack_article", content=post_text, status="draft",
        )
        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            await self.db.save_used_topic(topic, "hack_article")
            logger.info(f"Статья про взлом опубликована: {topic[:50]}")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Random Article (Thu 15:00) ---

    async def generate_and_publish_random_article(self):
        """Publish a random article from the database, rephrased as a channel post."""
        article = await self.db.get_random_article()
        if not article:
            logger.warning("Нет статей для рандомного поста")
            return

        post_text = await self.generator.generate_random_article_post(
            title=article.get("title", ""),
            content=article.get("content", ""),
            source=article.get("source", ""),
            url=article.get("url", ""),
        )

        post_id = await self.db.save_post(
            post_type="random_article",
            content=post_text,
            article_ids=str(article.get("id", "")),
            status="draft",
        )
        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            logger.info(f"Рандомная статья опубликована: {article.get('title', '')[:50]}")
        else:
            await self.db.update_post_status(post_id, "failed")

    # --- Weekly Summary (Sun 18:00) ---

    async def generate_and_publish_weekly_summary(self):
        """Generate and publish a weekly summary post on Sunday."""
        from datetime import timedelta

        # Get articles from the last 7 days
        since = datetime.now(timezone.utc) - timedelta(days=7)
        articles = await self.db.get_articles_since(since)

        news_list = "\n".join(
            f"- {a['title']} ({a['source']}) | {a.get('url', '')}"
            for a in (articles or [])[:20]
        )

        # Get posts from the last 7 days
        posts_week = await self.db.get_posts_since(since) if hasattr(self.db, 'get_posts_since') else []
        weekly_posts = ""
        if posts_week:
            summaries = []
            for p in posts_week:
                ptype = p.get("post_type", "")
                content = p.get("content", "")[:100]
                summaries.append(f"[{ptype}] {content}...")
            weekly_posts = "\n".join(summaries)

        post_text = await self.generator.generate_weekly_summary(
            news_list=news_list,
            weekly_posts=weekly_posts,
        )

        post_id = await self.db.save_post(
            post_type="weekly_summary", content=post_text, status="draft",
        )
        message_id = await self.publisher.publish_post(post_text)
        if message_id:
            await self.db.update_post_status(post_id, "published", message_id)
            logger.info("Итоги недели опубликованы")
        else:
            await self.db.update_post_status(post_id, "failed")

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

    async def handle_admin_chat(
        self,
        message: str,
        image_b64: str | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Handle admin AI chat message with custom knowledge context."""
        # Build custom knowledge context from DB
        custom_knowledge = ""
        if self.db:
            # Search for relevant entries first
            entries = await self.db.search_knowledge(message)
            if not entries:
                # Fall back to all recent entries (limited)
                entries = await self.db.get_all_knowledge()
                entries = entries[:10]
            if entries:
                parts = []
                for e in entries[:5]:
                    parts.append(f"[{e['topic']}]: {e['content']}")
                custom_knowledge = "\n\n".join(parts)

        return await self.generator.admin_chat(
            message=message,
            custom_knowledge=custom_knowledge,
            image_b64=image_b64,
            history=history,
        )

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
            f"  Пн: 09:00 новости | 13:00 безопасность | 19:00 вечерние + мнение\n"
            f"  Вт: 09:00 новости | 13:00 взломы | 19:00 вечерние + мнение\n"
            f"  Ср: 09:00 новости | 19:00 вечерние + мнение\n"
            f"  Чт: 09:00 новости | 15:00 рандомная статья | 19:00 вечерние + мнение\n"
            f"  Пт: 09:00 новости | 19:00 вечерние + мнение\n"
            f"  Сб: 09:00 новости | 19:00 вечерние + мнение\n"
            f"  Вс: 09:00 новости | 18:00 итоги недели + мнение\n\n"
            f"Глубокие разборы и статьи - через /ai в ручном режиме.\n\n"
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
