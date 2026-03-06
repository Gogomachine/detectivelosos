"""
Scheduler for the AML Detective Agent.
Weekly content schedule (Moscow time):

  Monday:    09:00 Morning News | 13:00 Security Post    | 17:00 Author Post     | 19:00 Evening News
  Tuesday:   09:00 Morning News | 13:00 Hack Article     | 17:00 Author Post     | 19:00 Evening News
  Wednesday: 09:00 Morning News | 13:00 AML Services     | 17:00 Author Post     | 19:00 Evening News
  Thursday:  09:00 Morning News |                         | 17:00 Random Article  | 19:00 Evening News
  Friday:    09:00 Morning News | 13:00 Hack Article     | 17:00 Author Post     | 19:00 Evening News
  Saturday:  09:00 Morning News |                         | 17:00 Expert Thoughts | 19:00 Evening News
  Sunday:    09:00 Morning News |                         | 18:00 Weekly Summary  |

News parsing: 08:45, 18:45 daily.
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

# Topics for hack articles (Tue/Fri 13:00)
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

# Topics for AML services review (Wed 13:00)
AML_SERVICES_TOPICS = [
    "Chainalysis Reactor: главный инструмент крипто-детектива",
    "Elliptic: как британцы анализируют блокчейн",
    "TRM Labs: конкурент Chainalysis из Сан-Франциско",
    "Arkham Intelligence: деанон блокчейна в реальном времени",
    "Crystal Blockchain (Bitfury): российские корни и глобальный охват",
    "Nansen: аналитика DeFi и smart money",
    "Dune Analytics: SQL-запросы к блокчейну для всех",
    "Etherscan: больше чем просто блок-эксплорер",
    "Revoke.cash: как отозвать опасные approvals",
    "Tornado Cash vs Railgun: приватность или отмывание?",
    "Сравнение AML-платформ: Chainalysis vs Elliptic vs TRM",
    "MistTrack: бесплатная альтернатива для расследований",
    "Scorechain: европейский AML-мониторинг",
    "CipherTrace (Mastercard): как банки проверяют крипту",
    "Merkle Science: AML из Сингапура",
    "Solidus Labs: мониторинг DeFi-манипуляций",
    "Как работает KYT (Know Your Transaction)",
    "Что такое VASP и какие обязанности по AML",
    "Travel Rule: как сервисы обмениваются данными",
    "AI в AML: как машинное обучение ловит преступников",
]

# Topics for expert thoughts (Sat 17:00)
EXPERT_THOUGHTS_TOPICS = [
    "Регуляция крипты: мировые тренды 2025-2026",
    "Privacy vs прозрачность: будущее блокчейна",
    "Централизация DeFi: миф о децентрализации",
    "Крипто-санкции: работают ли они на самом деле?",
    "AI в комплаенсе: замена людей или усиление?",
    "MiCA и европейская крипто-регуляция",
    "Stablecoin regulation: почему все хотят контроля",
    "CBDCs vs крипта: конкуренция или сосуществование?",
    "Cross-chain будущее: проблемы интероперабельности",
    "Deepfake fraud в крипте: новая угроза",
    "Web3 идентичность: как решить KYC без централизации",
    "Крипто-комплаенс в России: текущая ситуация",
    "NFT и отмывание денег: реальная угроза?",
    "DAO governance: демократия или плутократия?",
    "Квантовые компьютеры и безопасность блокчейна",
    "Метавселенные и финансовые преступления будущего",
]

# Legacy aliases for backward compatibility
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
        self._on_aml_services = None
        self._on_random_article = None
        self._on_author_post = None
        self._on_expert_thoughts = None
        self._on_weekly_summary = None

    def set_callbacks(
        self,
        on_parse_news=None,
        on_morning_news=None,
        on_evening_news=None,
        on_security_post=None,
        on_hack_article=None,
        on_aml_services=None,
        on_random_article=None,
        on_author_post=None,
        on_expert_thoughts=None,
        on_weekly_summary=None,
        **_kwargs,
    ):
        """Set callback functions for scheduled tasks."""
        self._on_parse_news = on_parse_news
        self._on_morning_news = on_morning_news
        self._on_evening_news = on_evening_news
        self._on_security_post = on_security_post
        self._on_hack_article = on_hack_article
        self._on_aml_services = on_aml_services
        self._on_random_article = on_random_article
        self._on_author_post = on_author_post
        self._on_expert_thoughts = on_expert_thoughts
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

        # === 13:00 slots (Mon/Tue/Wed/Fri) ===
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
        # Wednesday 13:00 - AML services review
        self.scheduler.add_job(
            self._run_aml_services,
            trigger=CronTrigger(day_of_week="wed", hour=13, minute=0),
            id="aml_services",
            name="Разбор AML-сервисов (Ср 13:00)",
            replace_existing=True,
        )
        # Friday 13:00 - Hack article
        self.scheduler.add_job(
            self._run_hack_article,
            trigger=CronTrigger(day_of_week="fri", hour=13, minute=0),
            id="hack_article_fri",
            name="Статья про взломы (Пт 13:00)",
            replace_existing=True,
        )

        # === 17:00 slots ===
        # Mon/Tue/Wed/Fri 17:00 - Author post
        self.scheduler.add_job(
            self._run_author_post,
            trigger=CronTrigger(day_of_week="mon,tue,wed,fri", hour=17, minute=0),
            id="author_post",
            name="Пост с размышлениями (17:00)",
            replace_existing=True,
        )
        # Thursday 17:00 - Random article from bot
        self.scheduler.add_job(
            self._run_random_article,
            trigger=CronTrigger(day_of_week="thu", hour=17, minute=0),
            id="random_article",
            name="Рандомная статья (Чт 17:00)",
            replace_existing=True,
        )
        # Saturday 17:00 - Expert thoughts
        self.scheduler.add_job(
            self._run_expert_thoughts,
            trigger=CronTrigger(day_of_week="sat", hour=17, minute=0),
            id="expert_thoughts",
            name="Экспертные мысли (Сб 17:00)",
            replace_existing=True,
        )

        # === 19:00 Evening News (Mon-Sat) ===
        self.scheduler.add_job(
            self._run_evening_news,
            trigger=CronTrigger(day_of_week="mon-sat", hour=19, minute=0),
            id="evening_news",
            name="Вечерние новости (19:00)",
            replace_existing=True,
        )

        # === Sunday 18:00 - Weekly Summary ===
        self.scheduler.add_job(
            self._run_weekly_summary,
            trigger=CronTrigger(day_of_week="sun", hour=18, minute=0),
            id="weekly_summary",
            name="Итоги недели (Вс 18:00)",
            replace_existing=True,
        )

        logger.info(
            "Расписание настроено (МСК):\n"
            "  Пн: 09:00 новости | 13:00 безопасность | 17:00 размышления | 19:00 вечерние\n"
            "  Вт: 09:00 новости | 13:00 взломы | 17:00 размышления | 19:00 вечерние\n"
            "  Ср: 09:00 новости | 13:00 AML-сервисы | 17:00 размышления | 19:00 вечерние\n"
            "  Чт: 09:00 новости | 17:00 рандомная статья | 19:00 вечерние\n"
            "  Пт: 09:00 новости | 13:00 взломы | 17:00 размышления | 19:00 вечерние\n"
            "  Сб: 09:00 новости | 17:00 экспертные мысли | 19:00 вечерние\n"
            "  Вс: 09:00 новости | 18:00 итоги недели"
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
        logger.info("Running evening news (19:00 MSK)")
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
        logger.info("Running hack article (13:00 MSK)")
        if self._on_hack_article:
            try:
                await self._on_hack_article()
            except Exception as e:
                logger.error(f"Hack article failed: {e}")

    async def _run_aml_services(self):
        logger.info("Running AML services review (Wed 13:00 MSK)")
        if self._on_aml_services:
            try:
                await self._on_aml_services()
            except Exception as e:
                logger.error(f"AML services review failed: {e}")

    async def _run_random_article(self):
        logger.info("Running random article post (Thu 17:00 MSK)")
        if self._on_random_article:
            try:
                await self._on_random_article()
            except Exception as e:
                logger.error(f"Random article failed: {e}")

    async def _run_author_post(self):
        logger.info("Running author post (17:00 MSK)")
        if self._on_author_post:
            try:
                await self._on_author_post()
            except Exception as e:
                logger.error(f"Author post failed: {e}")

    async def _run_expert_thoughts(self):
        logger.info("Running expert thoughts (Sat 17:00 MSK)")
        if self._on_expert_thoughts:
            try:
                await self._on_expert_thoughts()
            except Exception as e:
                logger.error(f"Expert thoughts failed: {e}")

    async def _run_weekly_summary(self):
        logger.info("Running weekly summary (Sun 18:00 MSK)")
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
