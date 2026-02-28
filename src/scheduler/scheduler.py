"""
Scheduler for the AML Detective Agent.
New content schedule (Moscow time):

  08:45 - Parse news
  09:00 - Morning News (max 7 articles, AML professional opinion)
  10:00 - Mini Post (security/AML educational, unique)
  13:00 - Deep Dive (crypto networks, AML incidents, security analysis)
  14:45 - Parse news
  15:00 - Afternoon News (max 7 articles, AML professional opinion)
  17:00 - Author's Post (free-form, personal, can be non-crypto)
  19:45 - Parse news
  20:00 - Evening News (max 7 articles, AML opinion, good night, daily summary)

Total: 6 posts/day, 3 news parses.
"""

import logging
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Topics for mini posts (10:00) - security and AML education
MINI_POST_TOPICS = [
    # Crypto security
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
    # AML education
    "Как распознать схему smurfing/structuring",
    "Что такое PEP и почему за ними следят",
    "Как работают подставные компании (shell companies)",
    "Trade-based money laundering: на что обратить внимание",
    "Что такое SAR и когда его подают",
    "Как работают криптомиксеры (Tornado Cash, YoMix)",
    "Что такое peel chain и как её распознать",
    "Chain hopping: как отмывают через кросс-чейн мосты",
    "Dusting attacks: зачем отправляют микроплатежи",
    "Что такое Travel Rule (FATF R.16) для крипто",
    "Privacy coins: почему Monero сложно отследить",
    "Как отличить honeypot-токен от легитимного",
    "Что такое rug pull и как защититься",
    "Nested exchanges: в чём опасность",
    "Как работает KYT (Know Your Transaction)",
    "Что такое VASP и какие обязанности по AML",
    "Red flags при крипто-транзакциях: топ-5",
    "Что показывает Chainalysis Reactor",
    "Elliptic GLASS: ML-модель для деанонимизации",
    "Как работает address clustering",
    "Зачем нужна сертификация CAMS",
    "Что такое hawala и почему это red flag",
    "Как Chainalysis кластеризует адреса",
    "OWASP Smart Contract Top 10: главные уязвимости",
    "Flash loan attacks: как работают",
]

# Topics for deep dives (13:00) - investigations and analysis
DEEP_DIVE_TOPICS = [
    # Case studies
    "Lazarus Group: как КНДР украла $1.5B у Bybit",
    "Ronin Bridge: анатомия кражи на $625M",
    "Nomad Bridge: как mob attack уничтожил $190M",
    "Garantex и 'эффект гидры': санкции не работают?",
    "Tornado Cash: история самого известного миксера",
    "Как ZachXBT стал главным крипто-детективом",
    "FTX: как Sam Bankman-Fried потерял $8B",
    "Terra/Luna: крах стейблкоина на $40B",
    "Mt. Gox: история первого большого крипто-хака",
    "The DAO hack: инцидент, разделивший Ethereum",
    "Wormhole bridge exploit: $320M за 30 минут",
    "Harmony Horizon bridge: атака Lazarus на $100M",
    # Network analysis
    "Как устроена сеть отмывания Lazarus Group",
    "Анатомия peel chain: как $100M превращаются в пыль",
    "DeFi протоколы как инструмент отмывания: реальные схемы",
    "Mixer vs DEX: куда идут грязные деньги в 2025",
    "Как санкции OFAC влияют на крипто-экосистему",
    "Криптобиржи без KYC: карта теневого рынка",
    "Stablecoin laundering: почему USDT в центре внимания",
    "Cross-chain laundering: как работают мосты для отмывания",
    "Privacy coins в 2025: Monero, Zcash, новые игроки",
    "AI в AML: как машинное обучение ловит преступников",
    # Technique deep dives
    "Как работает кластеризация адресов в блокчейн-аналитике",
    "Dusting attack: анатомия деанонимизации",
    "Flash loans: от DeFi инновации до инструмента хакеров",
    "Honeypot-контракты: разбор реального кода ловушки",
    "Rug pull анатомия: как создатели токенов обманывают",
    "Sandwich attacks: как MEV-боты грабят трейдеров",
    "Address poisoning: новая угроза 2025 года",
    "Phishing кампании в крипте: от простого к сложному",
    "Oracle manipulation: как обманывают ценовые оракулы",
    "Governance attacks: когда голосование становится оружием",
]


class AgentScheduler:
    """Manages the 6-post daily schedule of the AML Detective Agent."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
        self._on_parse_news = None
        self._on_morning_news = None
        self._on_mini_post = None
        self._on_deep_dive = None
        self._on_afternoon_news = None
        self._on_author_post = None
        self._on_evening_news = None

    def set_callbacks(
        self,
        on_parse_news=None,
        on_morning_news=None,
        on_mini_post=None,
        on_deep_dive=None,
        on_afternoon_news=None,
        on_author_post=None,
        on_evening_news=None,
        **_kwargs,
    ):
        """Set callback functions for scheduled tasks."""
        self._on_parse_news = on_parse_news
        self._on_morning_news = on_morning_news
        self._on_mini_post = on_mini_post
        self._on_deep_dive = on_deep_dive
        self._on_afternoon_news = on_afternoon_news
        self._on_author_post = on_author_post
        self._on_evening_news = on_evening_news

    def setup(self):
        """Configure the scheduler with all jobs (times in Moscow timezone)."""

        # --- 08:45 Parse news before morning ---
        self.scheduler.add_job(
            self._run_parse_news,
            trigger=CronTrigger(hour=8, minute=45),
            id="parse_before_morning",
            name="Парсинг перед утренней сводкой",
            replace_existing=True,
        )

        # --- 09:00 Morning News ---
        self.scheduler.add_job(
            self._run_morning_news,
            trigger=CronTrigger(hour=9, minute=0),
            id="morning_news",
            name="Утренняя сводка (09:00)",
            replace_existing=True,
        )

        # --- 10:00 Mini Post ---
        self.scheduler.add_job(
            self._run_mini_post,
            trigger=CronTrigger(hour=10, minute=0),
            id="mini_post",
            name="Мини-пост безопасность/AML (10:00)",
            replace_existing=True,
        )

        # --- 13:00 Deep Dive ---
        self.scheduler.add_job(
            self._run_deep_dive,
            trigger=CronTrigger(hour=13, minute=0),
            id="deep_dive",
            name="Разбор (13:00)",
            replace_existing=True,
        )

        # --- 14:45 Parse news before afternoon ---
        self.scheduler.add_job(
            self._run_parse_news,
            trigger=CronTrigger(hour=14, minute=45),
            id="parse_before_afternoon",
            name="Парсинг перед дневной сводкой",
            replace_existing=True,
        )

        # --- 15:00 Afternoon News ---
        self.scheduler.add_job(
            self._run_afternoon_news,
            trigger=CronTrigger(hour=15, minute=0),
            id="afternoon_news",
            name="Дневная сводка (15:00)",
            replace_existing=True,
        )

        # --- 17:00 Author's Post ---
        self.scheduler.add_job(
            self._run_author_post,
            trigger=CronTrigger(hour=17, minute=0),
            id="author_post",
            name="Авторский пост (17:00)",
            replace_existing=True,
        )

        # --- 19:45 Parse news before evening ---
        self.scheduler.add_job(
            self._run_parse_news,
            trigger=CronTrigger(hour=19, minute=45),
            id="parse_before_evening",
            name="Парсинг перед вечерней сводкой",
            replace_existing=True,
        )

        # --- 20:00 Evening News ---
        self.scheduler.add_job(
            self._run_evening_news,
            trigger=CronTrigger(hour=20, minute=0),
            id="evening_news",
            name="Вечерняя сводка (20:00)",
            replace_existing=True,
        )

        logger.info(
            "Расписание настроено (МСК): "
            "09:00 утренние новости, 10:00 мини-пост, 13:00 разбор, "
            "15:00 дневные новости, 17:00 авторский, 20:00 вечерние новости"
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
        """Run news parsing task."""
        logger.info("Running scheduled news parse")
        if self._on_parse_news:
            try:
                await self._on_parse_news()
            except Exception as e:
                logger.error(f"News parsing failed: {e}")

    async def _run_morning_news(self):
        """Run morning news briefing."""
        logger.info("Running morning news briefing (09:00 MSK)")
        if self._on_morning_news:
            try:
                await self._on_morning_news()
            except Exception as e:
                logger.error(f"Morning news failed: {e}")

    async def _run_mini_post(self):
        """Run mini post generation (security/AML)."""
        logger.info("Running mini post generation (10:00 MSK)")
        if self._on_mini_post:
            try:
                topic = random.choice(MINI_POST_TOPICS)
                await self._on_mini_post(topic)
            except Exception as e:
                logger.error(f"Mini post failed: {e}")

    async def _run_deep_dive(self):
        """Run deep dive analysis generation."""
        logger.info("Running deep dive generation (13:00 MSK)")
        if self._on_deep_dive:
            try:
                topic = random.choice(DEEP_DIVE_TOPICS)
                await self._on_deep_dive(topic)
            except Exception as e:
                logger.error(f"Deep dive failed: {e}")

    async def _run_afternoon_news(self):
        """Run afternoon news briefing."""
        logger.info("Running afternoon news briefing (15:00 MSK)")
        if self._on_afternoon_news:
            try:
                await self._on_afternoon_news()
            except Exception as e:
                logger.error(f"Afternoon news failed: {e}")

    async def _run_author_post(self):
        """Run author's free-form post."""
        logger.info("Running author post generation (17:00 MSK)")
        if self._on_author_post:
            try:
                await self._on_author_post()
            except Exception as e:
                logger.error(f"Author post failed: {e}")

    async def _run_evening_news(self):
        """Run evening news briefing."""
        logger.info("Running evening news briefing (20:00 MSK)")
        if self._on_evening_news:
            try:
                await self._on_evening_news()
            except Exception as e:
                logger.error(f"Evening news failed: {e}")

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
