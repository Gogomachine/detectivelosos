"""RSS feed parser for AML news sources."""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import aiohttp
import feedparser

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Parsed news item."""

    title: str
    url: str
    content: str
    source: str
    category: str
    published_at: datetime
    language: str = "en"
    content_hash: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.md5(
                f"{self.title}{self.url}".encode()
            ).hexdigest()


class RSSParser:
    """Asynchronous RSS feed parser."""

    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._session = session
        self._own_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "CaseWalker AML Bot/1.0"},
            )
        return self._session

    async def close(self):
        if self._own_session and self._session:
            await self._session.close()
            self._session = None

    async def fetch_feed(self, feed_config: dict) -> list[NewsItem]:
        """Fetch and parse a single RSS feed."""
        url = feed_config["url"]
        source = feed_config["name"]
        category = feed_config.get("category", "news")
        language = feed_config.get("language", "en")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Feed {source} returned status {response.status}")
                    return []
                text = await response.text()
        except Exception as e:
            logger.error(f"Failed to fetch feed {source}: {e}")
            return []

        return await asyncio.to_thread(
            self._parse_feed, text, source, category, language
        )

    def _parse_feed(
        self, text: str, source: str, category: str, language: str
    ) -> list[NewsItem]:
        """Parse RSS feed content (runs in thread to avoid blocking)."""
        feed = feedparser.parse(text)
        items = []

        for entry in feed.entries[:20]:  # Limit to 20 most recent
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            # Extract content
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            elif hasattr(entry, "summary"):
                content = entry.summary or ""
            elif hasattr(entry, "description"):
                content = entry.description or ""

            # Parse published date
            published = datetime.now(timezone.utc)
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

            # Extract tags
            tags = []
            if hasattr(entry, "tags"):
                tags = [t.get("term", "") for t in entry.tags if t.get("term")]

            items.append(
                NewsItem(
                    title=title,
                    url=link,
                    content=content,
                    source=source,
                    category=category,
                    published_at=published,
                    language=language,
                    tags=tags,
                )
            )

        logger.info(f"Parsed {len(items)} items from {source}")
        return items

    async def fetch_all_feeds(self, feeds: list[dict]) -> list[NewsItem]:
        """Fetch all configured RSS feeds concurrently."""
        tasks = [self.fetch_feed(feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Feed fetch error: {result}")
                continue
            all_items.extend(result)

        # Sort by publication date, newest first
        all_items.sort(key=lambda x: x.published_at, reverse=True)
        logger.info(f"Total items fetched: {len(all_items)}")
        return all_items
