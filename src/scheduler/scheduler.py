"""
Scheduler for the AML Detective Agent.
Weekly content schedule (Moscow time):

  Monday:    09:00 Morning News | 13:00 Security Post | 19:00 Evening News + Expert Opinion
  Tuesday:   09:00 Morning News | 13:00 Hack Article  | 19:00 Evening News + Expert Opinion
  Wednesday: 09:00 Morning News |                      | 19:00 Evening News + Expert Opinion
  Thursday:  09:00 Morning News | 15:00 Random Article | 19:00 Evening News + Expert Opinion
  Friday:    09:00 Morning News |                      | 19:00 Evening News + Expert Opinion
  Saturday:  09:00 Morning News |                      | 19:00 Evening News + Expert Opinion
  Sunday:    09:00 Morning News | 18:00 Weekly Summary + Expert Opinion

News parsing: 08:45, 18:45 daily.
Deep dives and authored articles are created manually by admin via /ai command.
"""

import logging
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Topics for security posts (Mon 13:00)
SECURITY_POST_TOPICS = [
    "Как защитить криптокошелёк от взлома",
    "Что такое seed-фраза и почему её нельзя хранить в облаке",
    "Фишинг в крипте: как распознать поддельный сайт",
    "Двухфакторная аутентификация для крипто-аккаунтов",
    "Как проверить смарт-контракт перед взаимодействием",
    "Безопасность DeFi: на что обратить внимание",
    "Холодные vs горячие кошельки: что безопаснее",
    "Как распознать скам-токен до покупки",
    "Social engineering в крипте: типичные схемы",
    "Безопасность мостов: почему cross-chain самое уязвимое место",
    "Как работает аудит смарт-контрактов",
    "Approval в DeFi: скрытая угроза для кошелька",
    "MEV-боты: как они крадут у обычных пользователей",
    "Безопасность приватных ключей: лучшие практики",
    "Как проверить NFT на подлинность",
    "Dusting attacks: зачем отправляют микроплатежи",
    "Address poisoning: новая угроза",
    "Phishing кампании в крипте: от простого к сложному",
    "Как отличить honeypot-токен от легитимного",
    "Red flags при крипто-транзакциях: топ-5",
    "OWASP Smart Contract Top 10: главные уязвимости",
    "Flash loan attacks: как работают",
    "Безопасность приватных ключей: лучшие практики",
    "Не используй публичный Wi-Fi для крипто-транзакций",
]

# Topics for hack articles (Tue 13:00)
HACK_ARTICLE_TOPICS = [
    "Lazarus Group: как КНДР украла $1.5B у Bybit",
    "Ronin Bridge: анатомия кражи на $625M",
    "Nomad Bridge: как mob attack уничтожил $190M",
    "Tornado Cash: история самого известного миксера",
    "FTX: как Sam Bankman-Fried потерял $8B",
    "Terra/Luna: крах стейблкоина на $40B",
    "Mt. Gox: история первого большого крипто-хака",
    "The DAO hack: инцидент, разделивший Ethereum",
    "Wormhole bridge exploit: $320M за 30 минут",
    "Harmony Horizon bridge: атака Lazarus на $100M",
    "Анатомия peel chain: как $100M превращаются в пыль",
    "DeFi протоколы как инструмент отмывания: реальные схемы",
    "Как устроена сеть отмывания Lazarus Group",
    "Honeypot-контракты: разбор реального кода ловушки",
    "Rug pull анатомия: как создатели токенов обманывают",
    "Sandwich attacks: как MEV-боты грабят трейдеров",
    "Oracle manipulation: как обманывают ценовые оракулы",
    "Governance attacks: когда голосование становится оружием",
    "Garantex и 'эффект гидры': санкции не работают?",
    "Как ZachXBT стал главным крипто-детективом",
]

# Legacy aliases kept for imports that may reference them
AML_SERVICES_TOPICS = []
EXPERT_THOUGHTS_TOPICS = []
MINI_POST_TOPICS = SECURITY_POST_TOPICS
DEEP_DIVE_TOPICS = HACK_ARTICLE_TOPICS
GOODNIGHT_TIP_TOPICS = SECURITY_POST_TOPICS


class AgentScheduler:
    """Manages the weekly content schedule of the AML Detective Agent."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
        # Callbacks
        self._on_parse_news = None
        self._on_morning_news = None
        self._on_evening_news = None
        self._on_security_post = None
        self._on_hack_article = None
        self._on_random_article = None
        self._on_weekly_summary = None

    def set_callbacks(
        self,
        on_parse_news=None,
        on_morning_news=None,
        on_evening_news=None,
        on_security_post=None,
        on_hack_article=None,
        on_random_article=None,
        on_weekly_summary=None,
        **_kwargs,
    ):
        """Set callback functions for scheduled tasks."""
        self._on_parse_news = on_parse_news
        self._on_morning_news = on_morning_news
        self._on_evening_news = on_evening_news
        self._on_security_post = on_security_post
        self._on_hack_article = on_hack_article
        self._on_random_article = on_random_article
        self._on_weekly_summary = on_weekly_summary

    def setup(self):
        """Configure the scheduler with weekly jobs (times in Moscow timezone).

        Day of week: mon=0, tue=1, wed=2, thu=3, fri=4, sat=5, sun=6
        """

        # === News parsing (daily) ===
        self.scheduler.add_job(
            self._run_parse_news,
            trigger=CronTrigger(hour=8, minute=45),
            id="parse_morning",
            name="Парсинг перед утренней сводкой",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._run_parse_news,
            trigger=CronTrigger(hour=18, minute=45),
            id="parse_evening",
            name="Парсинг перед вечерней сводкой",
            replace_existing=True,
        )

        # === 09:00 Morning News (daily) ===
        self.scheduler.add_job(
            self._run_morning_news,
            trigger=CronTrigger(hour=9, minute=0),
            id="morning_news",
            name="Утренние новости (09:00)",
            replace_existing=True,
        )

        # === 13:00 slots ===
        # Monday 13:00 - Security post
        self.scheduler.add_job(
            self._run_security_post,
            trigger=CronTrigger(day_of_week="mon", hour=13, minute=0),
            id="security_post",
            name="Пост про безопасность (Пн 13:00)",
            replace_existing=True,
        )
        # Tuesday 13:00 - Hack article
        self.scheduler.add_job(
            self._run_hack_article,
            trigger=CronTrigger(day_of_week="tue", hour=13, minute=0),
            id="hack_article_tue",
            name="Статья про взломы (Вт 13:00)",
            replace_existing=True,
        )

        # === Thursday 15:00 - Random article ===
        self.scheduler.add_job(
            self._run_random_article,
            trigger=CronTrigger(day_of_week="thu", hour=15, minute=0),
            id="random_article",
            name="Рандомная статья (Чт 15:00)",
            replace_existing=True,
        )

        # === 19:00 Evening News + Expert Opinion (Mon-Sat) ===
        self.scheduler.add_job(
            self._run_evening_news,
            trigger=CronTrigger(day_of_week="mon-sat", hour=19, minute=0),
            id="evening_news",
            name="Вечерние новости + экспертное мнение (19:00)",
            replace_existing=True,
        )

        # === Sunday 18:00 - Weekly Summary + Expert Opinion ===
        self.scheduler.add_job(
            self._run_weekly_summary,
            trigger=CronTrigger(day_of_week="sun", hour=18, minute=0),
            id="weekly_summary",
            name="Итоги недели + экспертное мнение (Вс 18:00)",
            replace_existing=True,
        )

        logger.info(
            "Расписание настроено (МСК):\n"
            "  Пн: 09:00 новости | 13:00 безопасность | 19:00 вечерние + мнение\n"
            "  Вт: 09:00 новости | 13:00 взломы | 19:00 вечерние + мнение\n"
            "  Ср: 09:00 новости | 19:00 вечерние + мнение\n"
            "  Чт: 09:00 новости | 15:00 рандомная статья | 19:00 вечерние + мнение\n"
            "  Пт: 09:00 новости | 19:00 вечерние + мнение\n"
            "  Сб: 09:00 новости | 19:00 вечерние + мнение\n"
            "  Вс: 09:00 новости | 18:00 итоги недели + мнение"
        )

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started (timezone: Europe/Moscow)")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    # --- Task runners ---

    async def _run_parse_news(self):
        logger.info("Running scheduled news parse")
        if self._on_parse_news:
            try:
                await self._on_parse_news()
            except Exception as e:
                logger.error(f"News parsing failed: {e}")

    async def _run_morning_news(self):
        logger.info("Running morning news (09:00 MSK)")
        if self._on_morning_news:
            try:
                await self._on_morning_news()
            except Exception as e:
                logger.error(f"Morning news failed: {e}")

    async def _run_evening_news(self):
        logger.info("Running evening news + expert opinion (19:00 MSK)")
        if self._on_evening_news:
            try:
                await self._on_evening_news()
            except Exception as e:
                logger.error(f"Evening news failed: {e}")

    async def _run_security_post(self):
        logger.info("Running security post (Mon 13:00 MSK)")
        if self._on_security_post:
            try:
                await self._on_security_post()
            except Exception as e:
                logger.error(f"Security post failed: {e}")

    async def _run_hack_article(self):
        logger.info("Running hack article (Tue 13:00 MSK)")
        if self._on_hack_article:
            try:
                await self._on_hack_article()
            except Exception as e:
                logger.error(f"Hack article failed: {e}")

    async def _run_random_article(self):
        logger.info("Running random article post (Thu 15:00 MSK)")
        if self._on_random_article:
            try:
                await self._on_random_article()
            except Exception as e:
                logger.error(f"Random article failed: {e}")

    async def _run_weekly_summary(self):
        logger.info("Running weekly summary + expert opinion (Sun 18:00 MSK)")
        if self._on_weekly_summary:
            try:
                await self._on_weekly_summary()
            except Exception as e:
                logger.error(f"Weekly summary failed: {e}")

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
