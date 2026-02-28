"""Filters and deduplicates parsed news items for AML relevance."""

import logging
import re

from config.sources import AML_KEYWORDS
from src.parsers.rss_parser import NewsItem

logger = logging.getLogger(__name__)


class NewsFilter:
    """Filters news items for AML relevance and deduplicates."""

    def __init__(self, keywords: list[str] | None = None):
        self._keywords = keywords or AML_KEYWORDS
        # Pre-compile pattern for efficiency
        escaped = [re.escape(kw) for kw in self._keywords]
        self._pattern = re.compile("|".join(escaped), re.IGNORECASE)

    def is_relevant(self, item: NewsItem) -> bool:
        """Check if a news item is AML-relevant."""
        text = f"{item.title} {item.content} {' '.join(item.tags)}".lower()
        return bool(self._pattern.search(text))

    def calculate_relevance_score(self, item: NewsItem) -> int:
        """Calculate a relevance score based on keyword matches."""
        text = f"{item.title} {item.content} {' '.join(item.tags)}".lower()
        matches = self._pattern.findall(text)
        # Title matches count double
        title_matches = self._pattern.findall(item.title.lower())
        return len(matches) + len(title_matches)

    def filter_and_rank(
        self,
        items: list[NewsItem],
        seen_hashes: set[str] | None = None,
    ) -> list[NewsItem]:
        """Filter for relevance, deduplicate, and rank by score."""
        seen = seen_hashes or set()
        filtered = []

        for item in items:
            # Skip duplicates
            if item.content_hash in seen:
                continue
            seen.add(item.content_hash)

            # Check relevance
            if not self.is_relevant(item):
                continue

            filtered.append(item)

        # Sort by relevance score (descending)
        filtered.sort(key=lambda x: self.calculate_relevance_score(x), reverse=True)

        logger.info(
            f"Filtered {len(items)} items down to {len(filtered)} relevant items"
        )
        return filtered
