"""Filters and deduplicates parsed news items for AML relevance."""

import logging
import re

from config.sources import AML_KEYWORDS
from src.parsers.rss_parser import NewsItem

logger = logging.getLogger(__name__)

# Sources that are inherently AML-relevant and don't need keyword filtering
AML_NATIVE_SOURCES = {
    "FATF",
    "ACAMS MoneyLaundering.com",
    "OCCRP",
    "FinCEN",
    "Compliance Week",
    "OFAC Sanctions",
    "EU AML Authority",
    "Chainalysis Blog",
    "Elliptic Blog",
    "Basel AML Index",
    "TRM Labs Insights",
    "Cointelegraph Investigations",
    "Rekt News",
    "Rekt News RU",
    "PeckShield Blog",
    "PeckShield",
}


class NewsFilter:
    """Filters news items for AML relevance and deduplicates."""

    def __init__(self, keywords: list[str] | None = None):
        self._keywords = keywords or AML_KEYWORDS
        # Pre-compile pattern for efficiency
        escaped = [re.escape(kw) for kw in self._keywords]
        self._pattern = re.compile("|".join(escaped), re.IGNORECASE)

    def is_relevant(self, item: NewsItem) -> bool:
        """Check if a news item is AML-relevant.

        Items from known AML sources are always relevant.
        Items from general sources need keyword matches.
        """
        if item.source in AML_NATIVE_SOURCES:
            return True
        text = f"{item.title} {item.content} {' '.join(item.tags)}".lower()
        return bool(self._pattern.search(text))

    def calculate_relevance_score(self, item: NewsItem) -> int:
        """Calculate a relevance score based on keyword matches."""
        text = f"{item.title} {item.content} {' '.join(item.tags)}".lower()
        matches = self._pattern.findall(text)
        # Title matches count double
        title_matches = self._pattern.findall(item.title.lower())
        score = len(matches) + len(title_matches)
        # Boost if article has actual content (not just a title/link)
        if item.content and len(item.content) > 100:
            score += 2
        return score

    def filter_and_rank(
        self,
        items: list[NewsItem],
        seen_hashes: set[str] | None = None,
    ) -> list[NewsItem]:
        """Filter for relevance, deduplicate, and rank by score."""
        seen = seen_hashes or set()
        filtered = []
        skipped_dupes = 0
        skipped_irrelevant = 0

        for item in items:
            # Skip duplicates
            if item.content_hash in seen:
                skipped_dupes += 1
                continue
            seen.add(item.content_hash)

            # Check relevance
            if not self.is_relevant(item):
                skipped_irrelevant += 1
                continue

            filtered.append(item)

        # Sort by relevance score (descending)
        filtered.sort(key=lambda x: self.calculate_relevance_score(x), reverse=True)

        logger.info(
            f"Фильтрация: {len(items)} всего -> {len(filtered)} релевантных "
            f"(пропущено: {skipped_dupes} дублей, {skipped_irrelevant} нерелевантных)"
        )
        return filtered
