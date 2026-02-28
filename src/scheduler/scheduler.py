"""
Scheduler for the AML Detective Agent.
Fixed daily schedule:
  07:00 - Morning digest
  10:00 - Combined post (3 news + AML tip)
  13:00 - Combined post (3 news + AML tip)
  16:00 - Combined post (3 news + AML tip)
  19:00 - Evening digest + sweet dreams
News parsing runs before each post.
"""

import logging
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import MORNING_DIGEST_HOUR, EVENING_DIGEST_HOUR

logger = logging.getLogger(__name__)

# AML tip topics for the combined posts - enriched with encyclopedia knowledge
AML_TIP_TOPICS = [
    # Classic AML
    "Как распознать схему smurfing/structuring",
    "Что такое PEP и почему за ними следят",
    "Как работают подставные компании (shell companies)",
    "Trade-based money laundering: на что обратить внимание",
    "Hawala: как работает и почему это red flag",
    "Что такое SAR и когда его подают",
    # Crypto AML
    "Как работают криптомиксеры (Tornado Cash, YoMix)",
    "Что такое peel chain и как её распознать",
    "Chain hopping: как отмывают через кросс-чейн мосты",
    "Dusting attacks: зачем отправляют микроплатежи",
    "Как Chainalysis кластеризует адреса",
    "Что такое Travel Rule (FATF R.16) для крипто",
    "Privacy coins: почему Monero сложно отследить",
    "Flash loan attacks: как работают",
    "Как отличить honeypot-токен от легитимного",
    "Что такое rug pull и как защититься",
    "Nested exchanges: в чём опасность",
    "Как работает KYT (Know Your Transaction)",
    "Что такое VASP и какие обязанности по AML",
    "Red flags при крипто-транзакциях: топ-5",
    # Case studies as tips
    "Lazarus Group: как КНДР отмывает крипту",
    "Garantex и 'эффект гидры': санкции не останавливают",
    "Ronin Bridge: урок про social engineering",
    "Nomad Bridge: что такое mob attack",
    "Как ZachXBT расследует крипто-мошенничество",
    # Tools & methods
    "Что показывает Chainalysis Reactor",
    "Elliptic GLASS: ML-модель для деанонимизации",
    "Как работает address clustering",
    "OWASP Smart Contract Top 10: главные уязвимости",
    "Зачем нужна сертификация CAMS",
]

# Combined post hours (between morning and evening digests)
COMBINED_POST_HOURS = [10, 13, 16]


class AgentScheduler:
    """Manages the schedule of the AML Detective Agent."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self._on_parse_news = None
        self._on_combined_post = None
        self._on_morning_digest = None
        self._on_evening_digest = None

    def set_callbacks(
        self,
        on_parse_news=None,
        on_combined_post=None,
        on_morning_digest=None,
        on_evening_digest=None,
        **_kwargs,
    ):
        """Set callback functions for scheduled tasks."""
        self._on_parse_news = on_parse_news
        self._on_combined_post = on_combined_post
        self._on_morning_digest = on_morning_digest
        self._on_evening_digest = on_evening_digest

    def setup(self):
        """Configure the scheduler with all jobs."""
        # Parse news before morning digest (06:45)
        self.scheduler.add_job(
            self._run_parse_news,
            trigger=CronTrigger(hour=MORNING_DIGEST_HOUR - 1, minute=45),
            id="parse_before_morning",
            name="Parse before morning digest",
            replace_existing=True,
        )

        # 07:00 - Morning digest
        self.scheduler.add_job(
            self._run_morning_digest,
            trigger=CronTrigger(hour=MORNING_DIGEST_HOUR, minute=0),
            id="morning_digest",
            name="Morning Digest (07:00)",
            replace_existing=True,
        )

        # 10:00, 13:00, 16:00 - Combined posts (parse news 15 min before each)
        for hour in COMBINED_POST_HOURS:
            self.scheduler.add_job(
                self._run_parse_news,
                trigger=CronTrigger(hour=hour - 1, minute=45),
                id=f"parse_before_{hour}",
                name=f"Parse before {hour}:00 post",
                replace_existing=True,
            )
            self.scheduler.add_job(
                self._run_combined_post,
                trigger=CronTrigger(hour=hour, minute=0),
                id=f"combined_post_{hour}",
                name=f"Combined Post ({hour}:00)",
                replace_existing=True,
            )

        # Parse news before evening digest (18:45)
        self.scheduler.add_job(
            self._run_parse_news,
            trigger=CronTrigger(hour=EVENING_DIGEST_HOUR - 1, minute=45),
            id="parse_before_evening",
            name="Parse before evening digest",
            replace_existing=True,
        )

        # 19:00 - Evening digest
        self.scheduler.add_job(
            self._run_evening_digest,
            trigger=CronTrigger(hour=EVENING_DIGEST_HOUR, minute=0),
            id="evening_digest",
            name="Evening Digest (19:00)",
            replace_existing=True,
        )

        schedule_str = (
            f"07:00 утренний дайджест, "
            f"{', '.join(f'{h}:00' for h in COMBINED_POST_HOURS)} сводки, "
            f"19:00 вечерний дайджест"
        )
        logger.info(f"Расписание настроено: {schedule_str}")

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

    async def _run_combined_post(self):
        """Run combined post generation (3 news + AML tip)."""
        logger.info("Running combined post generation")
        if self._on_combined_post:
            try:
                tip_topic = random.choice(AML_TIP_TOPICS)
                await self._on_combined_post(tip_topic)
            except Exception as e:
                logger.error(f"Combined post failed: {e}")

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
