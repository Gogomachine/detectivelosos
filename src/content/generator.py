"""Content generator using Claude API for creating AML posts."""

import logging
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import anthropic

from config import ANTHROPIC_API_KEY
from config.encyclopedia import AML_ENCYCLOPEDIA
from config.prompts import (
    AFTERNOON_NEWS_TEMPLATE,
    AML_SERVICES_TEMPLATE,
    AUTHOR_POST_TEMPLATE,
    COMBINED_POST_TEMPLATE,
    DEEP_DIVE_TEMPLATE,
    ENRICHMENT_TEMPLATE,
    EVENING_DIGEST_TEMPLATE,
    EVENING_NEWS_TEMPLATE,
    EXPERT_THOUGHTS_TEMPLATE,
    FUN_FACT_TEMPLATE,
    GOODNIGHT_POST_TEMPLATE,
    HACK_ARTICLE_TEMPLATE,
    MINI_POST_TEMPLATE,
    MORNING_DIGEST_TEMPLATE,
    MORNING_NEWS_TEMPLATE,
    INVESTIGATION_TEMPLATE,
    NEWS_POST_TEMPLATE,
    RANDOM_ARTICLE_TEMPLATE,
    STYLE_EXAMPLES,
    SYSTEM_PROMPT,
    WEEKLY_ANALYTICS_TEMPLATE,
    WEEKLY_SUMMARY_TEMPLATE,
)
from config.sources import POST_CATEGORIES

logger = logging.getLogger(__name__)

_MOSCOW_TZ = ZoneInfo("Europe/Moscow")
_WEEKDAYS_RU = [
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
]


def _today_with_weekday() -> str:
    """Return current date in Moscow timezone with Russian day name, e.g. 'понедельник, 09.03.2026'."""
    now = datetime.now(_MOSCOW_TZ)
    day_name = _WEEKDAYS_RU[now.weekday()]
    return f"{day_name}, {now.strftime('%d.%m.%Y')}"


# Sections of the encyclopedia that can be referenced for specific topics
ENCYCLOPEDIA_SECTIONS = {
    "mixers": "4. ANONYMIZATION TECHNIQUES\n\n4.1 Mixers & Tumblers",
    "chain_hopping": "4.2 Chain Hopping (Cross-Chain Laundering)",
    "peel_chains": "4.3 Peel Chains",
    "clustering": "5. DEANONYMIZATION & FORENSIC TECHNIQUES\n\n5.1 Address Clustering",
    "dusting": "5.2 Dusting Attacks",
    "smart_contracts": "6. SMART CONTRACT ANALYSIS",
    "defi_scams": "6.2 DeFi Scam Typology",
    "nested_exchanges": "7. NESTED EXCHANGES",
    "sanctions": "7.1 OFAC-Sanctioned Crypto Exchanges",
    "garantex": "7.2 Garantex Case Study: Hydra Effect",
    "bridges": "8.1 Bridge Exploits Comparison",
    "ronin": "8.2 Ronin Bridge (Axie Infinity) - $625M",
    "nomad": "8.3 Nomad Bridge - $190M",
    "lazarus": "8.4 Lazarus Group - Complete Attack Timeline",
    "red_flags": "9. RED FLAGS TAXONOMY",
    "obfuscation": "10. OBFUSCATION METHODS: COMPARATIVE ANALYSIS",
    "investigation": "11. INVESTIGATION METHODOLOGY",
    "statistics": "12. KEY STATISTICS & 2025-2026 TRENDS",
    "fatf": "1.2 FATF Standards",
    "vasp": "1.1 VASP Decision-Making Framework",
    "analytics": "3. BLOCKCHAIN ANALYTICS PLATFORMS",
    "certifications": "2. PROFESSIONAL CERTIFICATIONS",
}


def _extract_section(section_marker: str) -> str:
    """Extract a section from the encyclopedia by its heading marker."""
    start = AML_ENCYCLOPEDIA.find(section_marker)
    if start == -1:
        return ""

    # Determine the section level from the marker (e.g., "4." = level 1, "4.1" = level 2)
    import re
    marker_match = re.match(r"^(\d+(?:\.\d+)?)", section_marker)
    if not marker_match:
        # No numbered heading - just grab ~2000 chars
        return AML_ENCYCLOPEDIA[start:start + 2000].strip()

    marker_num = marker_match.group(1)
    marker_parts = marker_num.split(".")
    marker_level = len(marker_parts)
    marker_major = int(marker_parts[0])

    rest = AML_ENCYCLOPEDIA[start:]
    lines = rest.split("\n")
    section_lines = [lines[0]]

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            section_lines.append(line)
            continue

        # Check if this line is a section header
        heading_match = re.match(r"^(\d+(?:\.\d+)?)\s", stripped)
        if heading_match:
            heading_num = heading_match.group(1)
            heading_parts = heading_num.split(".")
            heading_level = len(heading_parts)
            heading_major = int(heading_parts[0])

            # Stop at same-level or higher-level section that's different from current
            if heading_level <= marker_level and heading_num != marker_num:
                break
            # Also stop at next major section
            if heading_major > marker_major and heading_level == 1:
                break

        section_lines.append(line)

    return "\n".join(section_lines).strip()


def _get_relevant_context(topic: str) -> str:
    """Get relevant encyclopedia sections based on topic keywords."""
    topic_lower = topic.lower()
    relevant_sections = []

    keyword_map = {
        "mixers": ["миксер", "mixer", "tumbler", "tornado", "coinjoin", "wasabi", "sinbad", "blender"],
        "chain_hopping": ["chain hop", "cross-chain", "мост", "bridge", "thorchain", "chainflip"],
        "peel_chains": ["peel chain", "smurfing", "structuring", "структурирован"],
        "clustering": ["кластериз", "cluster", "деанон", "deanon", "heuristic"],
        "dusting": ["dusting", "dust attack", "пылев"],
        "smart_contracts": ["smart contract", "смарт-контракт", "уязвимост", "vulnerability", "owasp"],
        "defi_scams": ["honeypot", "rug pull", "скам", "scam", "defi"],
        "nested_exchanges": ["nested", "вложенн", "обменник"],
        "sanctions": ["санкци", "sanction", "ofac", "sdn", "suex", "chatex"],
        "garantex": ["garantex", "гарантекс", "grinex", "гринекс", "гидра"],
        "bridges": ["bridge", "мост", "wormhole", "nomad", "bnb bridge", "harmony"],
        "ronin": ["ronin", "axie", "ронин"],
        "nomad": ["nomad", "номад", "gurevich", "гуревич", "mob attack"],
        "lazarus": ["lazarus", "лазарус", "кндр", "dprk", "north korea", "bybit"],
        "red_flags": ["red flag", "красн", "подозрител", "suspicious"],
        "obfuscation": ["обфуска", "obfuscat", "отмыван", "laundering method"],
        "investigation": ["расследован", "investigat", "zachxbt", "tracing", "forensic"],
        "statistics": ["статистик", "statistic", "тренд", "trend", "2025", "2026"],
        "fatf": ["fatf", "фатф", "travel rule"],
        "vasp": ["vasp", "kyc", "kyb", "cdd", "edd", "комплаенс", "compliance framework"],
        "analytics": ["chainalysis", "elliptic", "trm labs", "nansen", "arkham", "аналитик"],
        "certifications": ["cams", "ccas", "cfcs", "сертифик", "certif"],
    }

    for section_key, keywords in keyword_map.items():
        for kw in keywords:
            if kw in topic_lower:
                section_text = _extract_section(ENCYCLOPEDIA_SECTIONS[section_key])
                if section_text and section_text not in relevant_sections:
                    relevant_sections.append(section_text)
                break

    if not relevant_sections:
        return ""

    # Limit to 2 most relevant sections to avoid token overflow
    context = "\n\n---\n\n".join(relevant_sections[:2])
    return f"Дополнительный контекст из AML-энциклопедии:\n\n{context}"


class ContentGenerator:
    """Generates AML content using Claude API."""

    def __init__(self, api_key: str | None = None):
        self.client = anthropic.AsyncAnthropic(api_key=api_key or ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Remove bold markdown (**) from generated text."""
        return text.replace("**", "")

    async def _generate(self, user_prompt: str, max_tokens: int = 2000) -> str:
        """Send a prompt to Claude and get the response."""
        try:
            full_system = SYSTEM_PROMPT + "\n\n" + STYLE_EXAMPLES
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=full_system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return self._clean_markdown(message.content[0].text)
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def _generate_with_image(
        self,
        user_prompt: str,
        image_b64: str,
        extra_context: str = "",
        max_tokens: int = 2000,
    ) -> str:
        """Send a prompt with an image to Claude (vision) and get the response."""
        try:
            system = SYSTEM_PROMPT + "\n\n" + STYLE_EXAMPLES
            if extra_context:
                system = f"{system}\n\n{extra_context}"
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": user_prompt,
                            },
                        ],
                    }
                ],
            )
            return self._clean_markdown(message.content[0].text)
        except Exception as e:
            logger.error(f"Claude Vision API error: {e}")
            raise

    async def _generate_with_context(
        self, user_prompt: str, extra_context: str, max_tokens: int = 2000
    ) -> str:
        """Send a prompt with additional encyclopedia context."""
        try:
            system = SYSTEM_PROMPT + "\n\n" + STYLE_EXAMPLES
            if extra_context:
                system = f"{system}\n\n{extra_context}"
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return self._clean_markdown(message.content[0].text)
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def generate_news_post(
        self, title: str, content: str, source: str, category: str, url: str = ""
    ) -> str:
        """Generate a Telegram post from a news article."""
        prompt = NEWS_POST_TEMPLATE.format(
            title=title,
            content=content[:3000],
            source=source,
            category=category,
            url=url or "не указан",
        )
        # Get relevant encyclopedia context based on article content
        context = _get_relevant_context(f"{title} {content[:500]}")
        post = await self._generate_with_context(prompt, context)
        logger.info(f"Generated news post for: {title[:50]}")
        return post

    async def generate_combined_post(
        self, articles: list[dict], tip_topic: str
    ) -> str:
        """Generate combined post: 3 news summaries + AML tip."""
        news_list = ""
        for i, article in enumerate(articles[:3], 1):
            title = article.get("title", "")
            source = article.get("source", "")
            url = article.get("url", "")
            content = article.get("content", "")[:300]
            news_list += f"{i}. [{source}] {title}\n   {content}\n   URL: {url}\n\n"

        prompt = COMBINED_POST_TEMPLATE.format(
            news_list=news_list or "Нет свежих новостей - тишина подозрительна...",
            tip_topic=tip_topic,
        )
        # Gather context from all articles + tip topic
        all_text = " ".join(a.get("title", "") for a in articles[:3]) + " " + tip_topic
        context = _get_relevant_context(all_text)
        post = await self._generate_with_context(prompt, context, max_tokens=3000)
        logger.info(f"Generated combined post with {len(articles)} news + tip: {tip_topic[:40]}")
        return post

    async def generate_digest(
        self, news_items: list[dict], is_morning: bool = True
    ) -> str:
        """Generate morning or evening digest."""
        today = _today_with_weekday()

        news_list = "\n".join(
            f"- {item['title']} ({item['source']}) | {item.get('url', '')}"
            for item in news_items
        )

        template = MORNING_DIGEST_TEMPLATE if is_morning else EVENING_DIGEST_TEMPLATE
        prompt = template.format(
            period=today,
            news_list=news_list or "Нет новых новостей - тишина подозрительна... 🤔",
        )
        post = await self._generate(prompt, max_tokens=3000)
        time_label = "утренний" if is_morning else "вечерний"
        logger.info(f"Generated {time_label} digest")
        return post

    async def generate_investigation(
        self, topic: str, facts: str, sources: str
    ) -> str:
        """Generate an investigative post with deep encyclopedia knowledge."""
        prompt = INVESTIGATION_TEMPLATE.format(
            topic=topic, facts=facts, sources=sources
        )
        # Always provide relevant context for investigations
        context = _get_relevant_context(topic)
        post = await self._generate_with_context(prompt, context, max_tokens=4000)
        logger.info(f"Generated investigation: {topic[:50]}")
        return post

    async def generate_fun_fact(self, topic: str) -> str:
        """Generate a fun AML fact post using encyclopedia knowledge."""
        # Get relevant encyclopedia context for the topic
        encyclopedia_context = _get_relevant_context(topic)
        if encyclopedia_context:
            context_text = f"Используй эту информацию из AML-энциклопедии:\n\n{encyclopedia_context}"
        else:
            context_text = "Используй свои экспертные знания из AML-энциклопедии."

        prompt = FUN_FACT_TEMPLATE.format(
            topic=topic,
            encyclopedia_context=context_text,
        )
        post = await self._generate(prompt, max_tokens=1500)
        logger.info(f"Generated fun fact: {topic[:50]}")
        return post

    async def generate_weekly_analytics(self, weekly_data: str) -> str:
        """Generate weekly analytics post with trend context."""
        prompt = WEEKLY_ANALYTICS_TEMPLATE.format(weekly_data=weekly_data)
        # Add statistics context
        context = _get_relevant_context("статистика тренды 2025")
        post = await self._generate_with_context(prompt, context, max_tokens=3000)
        logger.info("Generated weekly analytics")
        return post

    async def enrich_article(self, title: str, short_content: str) -> str:
        """Ask Claude to expand on a short article with encyclopedia knowledge."""
        prompt = ENRICHMENT_TEMPLATE.format(
            title=title,
            short_content=short_content,
        )
        context = _get_relevant_context(f"{title} {short_content}")
        return await self._generate_with_context(prompt, context, max_tokens=1000)

    async def explain_term(self, term: str) -> str:
        """Explain an AML/crypto term using encyclopedia knowledge."""
        context = _get_relevant_context(term)
        prompt = f"""Объясни термин или концепцию из мира AML/крипто-комплаенса:

Термин: {term}

Формат:
1. Краткое определение (1-2 предложения)
2. Как это работает на практике
3. Почему это важно для AML
4. Реальный пример использования (если есть)

Пиши как Кейс Уокер - живо, понятно, с деталями.
Без Markdown-разметки, без ** и без длинных тире."""
        return await self._generate_with_context(prompt, context, max_tokens=1500)

    async def generate_news_briefing(
        self,
        news_items: list[dict],
        time_of_day: str = "morning",
        daily_summary: str = "",
    ) -> str:
        """Generate a news briefing (morning/afternoon/evening) with max 7 articles."""
        today = _today_with_weekday()

        news_list = "\n".join(
            f"- {item['title']} ({item['source']}) | {item.get('url', '')}"
            for item in news_items[:7]
        )

        if time_of_day == "morning":
            prompt = MORNING_NEWS_TEMPLATE.format(
                date=today,
                news_list=news_list or "Ночь прошла тихо - ни одной новости. Подозрительно...",
            )
        elif time_of_day == "afternoon":
            prompt = AFTERNOON_NEWS_TEMPLATE.format(
                date=today,
                news_list=news_list or "Тихий день - пока ничего нового. Кейс на чеку...",
            )
        else:
            prompt = EVENING_NEWS_TEMPLATE.format(
                date=today,
                news_list=news_list or "Вечер без новостей. Редкое затишье...",
                daily_summary=daily_summary or "Сегодня был насыщенный день.",
            )

        # Get context from article contents
        all_text = " ".join(item.get("title", "") for item in news_items[:7])
        context = _get_relevant_context(all_text)
        post = await self._generate_with_context(prompt, context, max_tokens=3000)
        logger.info(f"Generated {time_of_day} news briefing ({len(news_items)} articles)")
        return post

    async def generate_mini_post(
        self, topic: str, used_topics: list[str] | None = None
    ) -> str:
        """Generate a short educational post about security or AML."""
        encyclopedia_context = _get_relevant_context(topic)
        if encyclopedia_context:
            context_text = f"Используй эту информацию из AML-энциклопедии:\n\n{encyclopedia_context}"
        else:
            context_text = "Используй свои экспертные знания из AML-энциклопедии."

        used_str = "\n".join(f"- {t}" for t in (used_topics or [])[-20:]) or "Пока не было."

        prompt = MINI_POST_TEMPLATE.format(
            topic=topic,
            encyclopedia_context=context_text,
            used_topics=used_str,
        )
        post = await self._generate(prompt, max_tokens=1500)
        logger.info(f"Generated mini post: {topic[:50]}")
        return post

    async def generate_deep_dive(
        self, topic: str, used_topics: list[str] | None = None
    ) -> str:
        """Generate an in-depth analysis post about crypto/AML topic."""
        encyclopedia_context = _get_relevant_context(topic)
        if encyclopedia_context:
            context_text = f"Используй эту информацию из AML-энциклопедии:\n\n{encyclopedia_context}"
        else:
            context_text = "Используй свои экспертные знания из AML-энциклопедии."

        used_str = "\n".join(f"- {t}" for t in (used_topics or [])[-20:]) or "Пока не было."

        prompt = DEEP_DIVE_TEMPLATE.format(
            topic=topic,
            encyclopedia_context=context_text,
            used_topics=used_str,
        )
        context = _get_relevant_context(topic)
        post = await self._generate_with_context(prompt, context, max_tokens=4000)
        logger.info(f"Generated deep dive: {topic[:50]}")
        return post

    async def generate_author_post(
        self, used_topics: list[str] | None = None
    ) -> str:
        """Generate a free-form author's post - personal thoughts, jokes, reflections."""
        today = _today_with_weekday()
        used_str = "\n".join(f"- {t}" for t in (used_topics or [])[-20:]) or "Пока не было."

        prompt = AUTHOR_POST_TEMPLATE.format(
            date=today,
            used_topics=used_str,
        )
        post = await self._generate(prompt, max_tokens=1500)
        logger.info("Generated author post")
        return post

    async def generate_goodnight_post(
        self, tip_topic: str, used_topics: list[str] | None = None
    ) -> str:
        """Generate a goodnight post with sweet dreams wish and mini security tip."""
        today = _today_with_weekday()
        used_str = "\n".join(f"- {t}" for t in (used_topics or [])[-20:]) or "Пока не было."

        prompt = GOODNIGHT_POST_TEMPLATE.format(
            date=today,
            tip_topic=tip_topic,
            used_topics=used_str,
        )
        post = await self._generate(prompt, max_tokens=1000)
        logger.info(f"Generated goodnight post: {tip_topic[:50]}")
        return post

    async def generate_hack_article(
        self, topic: str, used_topics: list[str] | None = None
    ) -> str:
        """Generate an article about a crypto hack/theft."""
        encyclopedia_context = _get_relevant_context(topic)
        if encyclopedia_context:
            context_text = f"Используй эту информацию из AML-энциклопедии:\n\n{encyclopedia_context}"
        else:
            context_text = "Используй свои экспертные знания из AML-энциклопедии."

        used_str = "\n".join(f"- {t}" for t in (used_topics or [])[-20:]) or "Пока не было."

        prompt = HACK_ARTICLE_TEMPLATE.format(
            topic=topic,
            encyclopedia_context=context_text,
            used_topics=used_str,
        )
        context = _get_relevant_context(topic)
        post = await self._generate_with_context(prompt, context, max_tokens=4000)
        logger.info(f"Generated hack article: {topic[:50]}")
        return post

    async def generate_aml_services_post(
        self, topic: str, used_topics: list[str] | None = None
    ) -> str:
        """Generate a review post about an AML service/tool."""
        encyclopedia_context = _get_relevant_context(topic)
        if encyclopedia_context:
            context_text = f"Используй эту информацию из AML-энциклопедии:\n\n{encyclopedia_context}"
        else:
            context_text = "Используй свои экспертные знания из AML-энциклопедии."

        used_str = "\n".join(f"- {t}" for t in (used_topics or [])[-20:]) or "Пока не было."

        prompt = AML_SERVICES_TEMPLATE.format(
            topic=topic,
            encyclopedia_context=context_text,
            used_topics=used_str,
        )
        context = _get_relevant_context(topic)
        post = await self._generate_with_context(prompt, context, max_tokens=2500)
        logger.info(f"Generated AML services post: {topic[:50]}")
        return post

    async def generate_expert_thoughts(
        self, topic: str, used_topics: list[str] | None = None
    ) -> str:
        """Generate an expert opinion/thoughts post."""
        today = _today_with_weekday()
        encyclopedia_context = _get_relevant_context(topic)
        if encyclopedia_context:
            context_text = f"Используй эту информацию из AML-энциклопедии:\n\n{encyclopedia_context}"
        else:
            context_text = "Используй свои экспертные знания из AML-энциклопедии."

        used_str = "\n".join(f"- {t}" for t in (used_topics or [])[-20:]) or "Пока не было."

        prompt = EXPERT_THOUGHTS_TEMPLATE.format(
            topic=topic,
            encyclopedia_context=context_text,
            used_topics=used_str,
            date=today,
        )
        context = _get_relevant_context(topic)
        post = await self._generate_with_context(prompt, context, max_tokens=2000)
        logger.info(f"Generated expert thoughts: {topic[:50]}")
        return post

    async def generate_random_article_post(
        self, title: str, content: str, source: str, url: str
    ) -> str:
        """Generate a post from a random article in the database."""
        prompt = RANDOM_ARTICLE_TEMPLATE.format(
            title=title,
            content=content[:3000],
            source=source,
            url=url or "не указан",
        )
        context = _get_relevant_context(f"{title} {content[:500]}")
        post = await self._generate_with_context(prompt, context)
        logger.info(f"Generated random article post: {title[:50]}")
        return post

    async def generate_weekly_summary(
        self, news_list: str, weekly_posts: str
    ) -> str:
        """Generate a weekly summary post for Sunday."""
        today = _today_with_weekday()
        prompt = WEEKLY_SUMMARY_TEMPLATE.format(
            date=today,
            news_list=news_list or "Тихая неделя - мало новостей.",
            weekly_posts=weekly_posts or "Нет данных о постах за неделю.",
        )
        context = _get_relevant_context("тренды AML крипто 2025 2026")
        post = await self._generate_with_context(prompt, context, max_tokens=3000)
        logger.info("Generated weekly summary")
        return post

    async def admin_chat(
        self,
        message: str,
        custom_knowledge: str = "",
        image_b64: str | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Process an admin message (free-form chat with AI agent).

        The admin can ask anything: analyze a link, generate content,
        answer a question using the knowledge base and encyclopedia.
        Supports image analysis when image_b64 is provided.
        Maintains conversation history for multi-turn dialogue.
        """
        context_parts = []

        # Add encyclopedia context based on message keywords
        encyclopedia_context = _get_relevant_context(message)
        if encyclopedia_context:
            context_parts.append(encyclopedia_context)

        # Add custom knowledge from DB
        if custom_knowledge:
            context_parts.append(
                f"Дополнительные знания из базы (добавлены админом):\n\n{custom_knowledge}"
            )

        extra = "\n\n---\n\n".join(context_parts) if context_parts else ""

        system = SYSTEM_PROMPT + "\n\n" + STYLE_EXAMPLES
        system += (
            "\n\nТы общаешься с админом бота. Отвечай как Кейс Уокер - "
            "экспертно, живо и по делу. Используй знания из энциклопедии и базы знаний.\n\n"
            "Если админ просит проанализировать ссылку - разбери тему, дай выводы.\n"
            "Если просит сделать новость/пост - сгенерируй в формате канала.\n"
            "Если отправлено изображение - опиши что на нём, проанализируй контент.\n"
            "Если спрашивает - отвечай развёрнуто."
        )
        if extra:
            system = f"{system}\n\n{extra}"

        # Build messages with conversation history
        messages = []
        if history:
            messages.extend(history)

        # Build current user message
        if image_b64:
            user_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_b64,
                    },
                },
                {"type": "text", "text": message},
            ]
        else:
            user_content = message

        messages.append({"role": "user", "content": user_content})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                system=system,
                messages=messages,
            )
            return self._clean_markdown(response.content[0].text)
        except Exception as e:
            logger.error(f"Admin chat API error: {e}")
            raise

    def get_category_emoji(self, category: str) -> str:
        """Get emoji for post category."""
        return POST_CATEGORIES.get(category, "📝")
