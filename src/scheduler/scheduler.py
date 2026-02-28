"""
Scheduler for the AML Detective Agent.
Manages news parsing, content generation, and posting schedule.
Ensures minimum 5 posts per day with morning and evening digests.
"""

import logging
import random
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import MORNING_DIGEST_HOUR, EVENING_DIGEST_HOUR, PARSE_INTERVAL_MINUTES

logger = logging.getLogger(__name__)

# Fun AML facts topics for filler posts
FUN_FACT_TOPICS = [
    "Самые абсурдные способы отмывания денег в истории",
    "Как криптовалюты изменили мир AML",
    "Рекордные штрафы банкам за нарушение AML",
    "Как работает система SWIFT и почему она важна для AML",
    "Самые известные схемы отмывания через недвижимость",
    "Как FinTech компании борются с финансовыми преступлениями",
    "История создания FATF и его влияние на мировую экономику",
    "Отмывание денег через предметы искусства",
    "Как казино используются для отмывания",
    "Роль криптомиксеров в отмывании денег",
    "Самые знаменитые информаторы в истории финансовых преступлений",
    "Как работают подставные компании (shell companies)",
    "Trade-based money laundering: как торговля прикрывает отмывание",
    "Золото и драгоценные камни: классика отмывания",
    "Как искусственный интеллект помогает ловить отмывщиков",
    "Hawala: древняя система переводов на службе преступности",
    "Самые дорогие расследования по отмыванию денег",
    "Как отмывают деньги через футбольные клубы",
    "PEP: почему политики под особым наблюдением",
    "Отмывание через NFT: новый тренд",
]


class AgentScheduler:
    """Manages the schedule of the AML Detective Agent."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self._on_parse_news = None
        self._on_generate_post = None
        self._on_morning_digest = None
        self._on_evening_digest = None
        self._on_fun_fact = None
        self._on_check_quota = None

    def set_callbacks(
        self,
        on_parse_news=None,
        on_generate_post=None,
        on_morning_digest=None,
        on_evening_digest=None,
        on_fun_fact=None,
        on_check_quota=None,
    ):
        """Set callback functions for scheduled tasks."""
        self._on_parse_news = on_parse_news
        self._on_generate_post = on_generate_post
        self._on_morning_digest = on_morning_digest
        self._on_evening_digest = on_evening_digest
        self._on_fun_fact = on_fun_fact
        self._on_check_quota = on_check_quota

    def setup(self):
        """Configure the scheduler with all jobs."""
        # 1. Parse news every N minutes
        self.scheduler.add_job(
            self._run_parse_news,
            trigger=IntervalTrigger(minutes=PARSE_INTERVAL_MINUTES),
            id="parse_news",
            name="Parse AML News",
            replace_existing=True,
        )

        # 2. Morning digest
        self.scheduler.add_job(
            self._run_morning_digest,
            trigger=CronTrigger(hour=MORNING_DIGEST_HOUR, minute=0),
            id="morning_digest",
            name="Morning Digest",
            replace_existing=True,
        )

        # 3. Evening digest
        self.scheduler.add_job(
            self._run_evening_digest,
            trigger=CronTrigger(hour=EVENING_DIGEST_HOUR, minute=0),
            id="evening_digest",
            name="Evening Digest",
            replace_existing=True,
        )

        # 4. Regular news posts throughout the day (10:00, 13:00, 16:00 UTC)
        for hour in [10, 13, 16]:
            self.scheduler.add_job(
                self._run_generate_post,
                trigger=CronTrigger(hour=hour, minute=random.randint(0, 30)),
                id=f"news_post_{hour}",
                name=f"News Post at {hour}:00",
                replace_existing=True,
            )

        # 5. Fun fact / filler post (if daily quota not met)
        self.scheduler.add_job(
            self._run_check_and_fill,
            trigger=CronTrigger(hour=18, minute=0),
            id="check_quota",
            name="Check Daily Post Quota",
            replace_existing=True,
        )

        logger.info("Scheduler configured with all jobs")

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    async def _run_parse_news(self):
        """Run news parsing task."""
        logger.info("Running scheduled news parse")
        if self._on_parse_news:
            try:
                await self._on_parse_news()
            except Exception as e:
                logger.error(f"News parsing failed: {e}")

    async def _run_morning_digest(self):
        """Run morning digest generation."""
        logger.info("Running morning digest")
        if self._on_morning_digest:
            try:
                await self._on_morning_digest()
            except Exception as e:
                logger.error(f"Morning digest failed: {e}")

    async def _run_evening_digest(self):
        """Run evening digest generation."""
        logger.info("Running evening digest")
        if self._on_evening_digest:
            try:
                await self._on_evening_digest()
            except Exception as e:
                logger.error(f"Evening digest failed: {e}")

    async def _run_generate_post(self):
        """Run post generation from unposted articles."""
        logger.info("Running scheduled post generation")
        if self._on_generate_post:
            try:
                await self._on_generate_post()
            except Exception as e:
                logger.error(f"Post generation failed: {e}")

    async def _run_check_and_fill(self):
        """Check daily post count and generate filler if needed."""
        logger.info("Checking daily post quota")
        if self._on_check_quota:
            try:
                posts_needed = await self._on_check_quota()
                if posts_needed > 0 and self._on_fun_fact:
                    for _ in range(min(posts_needed, 3)):
                        topic = random.choice(FUN_FACT_TOPICS)
                        await self._on_fun_fact(topic)
            except Exception as e:
                logger.error(f"Quota check failed: {e}")

    def get_next_runs(self) -> list[dict]:
        """Get info about upcoming scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else "N/A",
            })
        return jobs
