"""Web scraper for AML news sources without RSS feeds."""

import hashlib
import logging
from datetime import datetime, timezone

import aiohttp
from bs4 import BeautifulSoup

from src.parsers.rss_parser import NewsItem

logger = logging.getLogger(__name__)


class WebScraper:
    """Scrapes web pages for AML-related content."""

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

    async def scrape_page(self, source_config: dict) -> list[NewsItem]:
        """Scrape a single web page for news articles."""
        url = source_config["url"]
        source = source_config["name"]
        selector = source_config.get("selector", "article")
        category = source_config.get("category", "news")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Scrape {source} returned status {response.status}")
                    return []
                html = await response.text()
        except Exception as e:
            logger.error(f"Failed to scrape {source}: {e}")
            return []

        return self._extract_articles(html, selector, source, category, url)

    def _extract_articles(
        self, html: str, selector: str, source: str, category: str, base_url: str
    ) -> list[NewsItem]:
        """Extract article data from HTML."""
        soup = BeautifulSoup(html, "lxml")
        articles = soup.select(selector)
        items = []

        for article in articles[:10]:
            # Find title
            title_el = article.find(["h1", "h2", "h3", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            # Find link
            link_el = article.find("a", href=True)
            link = ""
            if link_el:
                href = link_el["href"]
                if href.startswith("http"):
                    link = href
                elif href.startswith("/"):
                    from urllib.parse import urljoin
                    link = urljoin(base_url, href)

            if not link:
                link = base_url

            # Find description
            desc_el = article.find(["p", "div", "span"], class_=lambda c: c and (
                "desc" in str(c).lower() or "summary" in str(c).lower()
                or "excerpt" in str(c).lower()
            ))
            content = desc_el.get_text(strip=True) if desc_el else ""

            items.append(
                NewsItem(
                    title=title,
                    url=link,
                    content=content,
                    source=source,
                    category=category,
                    published_at=datetime.now(timezone.utc),
                    content_hash=hashlib.md5(f"{title}{link}".encode()).hexdigest(),
                )
            )

        logger.info(f"Scraped {len(items)} articles from {source}")
        return items

    async def scrape_all(self, sources: list[dict]) -> list[NewsItem]:
        """Scrape all configured web sources."""
        import asyncio

        tasks = [self.scrape_page(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scrape error: {result}")
                continue
            all_items.extend(result)

        return all_items
