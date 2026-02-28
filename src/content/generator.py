"""Content generator using Claude API for creating AML posts."""

import logging
from datetime import datetime, timezone

import anthropic

from config import ANTHROPIC_API_KEY
from config.prompts import (
    DIGEST_TEMPLATE,
    FUN_FACT_TEMPLATE,
    INVESTIGATION_TEMPLATE,
    NEWS_POST_TEMPLATE,
    SYSTEM_PROMPT,
    WEEKLY_ANALYTICS_TEMPLATE,
)
from config.sources import POST_CATEGORIES

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates AML content using Claude API."""

    def __init__(self, api_key: str | None = None):
        self.client = anthropic.AsyncAnthropic(api_key=api_key or ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def _generate(self, user_prompt: str, max_tokens: int = 2000) -> str:
        """Send a prompt to Claude and get the response."""
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def generate_news_post(
        self, title: str, content: str, source: str, category: str
    ) -> str:
        """Generate a Telegram post from a news article."""
        prompt = NEWS_POST_TEMPLATE.format(
            title=title,
            content=content[:3000],  # Limit content length
            source=source,
            category=category,
        )
        post = await self._generate(prompt)
        logger.info(f"Generated news post for: {title[:50]}")
        return post

    async def generate_digest(
        self, news_items: list[dict], is_morning: bool = True
    ) -> str:
        """Generate morning or evening digest."""
        time_of_day = "Утренний" if is_morning else "Вечерний"
        emoji = "☀️" if is_morning else "🌙"
        today = datetime.now(timezone.utc).strftime("%d.%m.%Y")

        news_list = "\n".join(
            f"- {item['title']} ({item['source']})" for item in news_items
        )

        prompt = DIGEST_TEMPLATE.format(
            time_of_day=time_of_day,
            emoji=emoji,
            period=today,
            news_list=news_list or "Нет новых новостей — тишина подозрительна... 🤔",
        )
        post = await self._generate(prompt, max_tokens=3000)
        logger.info(f"Generated {time_of_day.lower()} digest")
        return post

    async def generate_investigation(
        self, topic: str, facts: str, sources: str
    ) -> str:
        """Generate an investigative post."""
        prompt = INVESTIGATION_TEMPLATE.format(
            topic=topic, facts=facts, sources=sources
        )
        post = await self._generate(prompt, max_tokens=4000)
        logger.info(f"Generated investigation: {topic[:50]}")
        return post

    async def generate_fun_fact(self, topic: str) -> str:
        """Generate a fun AML fact post."""
        prompt = FUN_FACT_TEMPLATE.format(topic=topic)
        post = await self._generate(prompt, max_tokens=1500)
        logger.info(f"Generated fun fact: {topic[:50]}")
        return post

    async def generate_weekly_analytics(self, weekly_data: str) -> str:
        """Generate weekly analytics post."""
        prompt = WEEKLY_ANALYTICS_TEMPLATE.format(weekly_data=weekly_data)
        post = await self._generate(prompt, max_tokens=3000)
        logger.info("Generated weekly analytics")
        return post

    async def enrich_article(self, title: str, short_content: str) -> str:
        """Ask Claude to expand on a short article for better post generation."""
        prompt = f"""У меня есть краткая новость. Добавь контекст и анализ:

Заголовок: {title}
Краткое содержание: {short_content}

Дай развёрнутое описание:
1. О чём эта новость (2-3 предложения)
2. Контекст — почему это важно для AML
3. Какие последствия это может иметь

Пиши по-русски, кратко и по делу."""
        return await self._generate(prompt, max_tokens=1000)

    def get_category_emoji(self, category: str) -> str:
        """Get emoji for post category."""
        return POST_CATEGORIES.get(category, "📝")
