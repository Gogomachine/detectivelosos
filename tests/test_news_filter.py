"""Tests for news filter."""

from datetime import datetime, timezone

from src.parsers.news_filter import NewsFilter
from src.parsers.rss_parser import NewsItem


def make_item(title: str, content: str = "", tags: list[str] | None = None) -> NewsItem:
    return NewsItem(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        content=content,
        source="Test Source",
        category="news",
        published_at=datetime.now(timezone.utc),
        tags=tags or [],
    )


class TestNewsFilter:
    def test_relevant_by_title(self):
        f = NewsFilter()
        item = make_item("New AML regulations announced by FATF")
        assert f.is_relevant(item)

    def test_relevant_by_content(self):
        f = NewsFilter()
        item = make_item("Breaking news", content="Money laundering scheme uncovered")
        assert f.is_relevant(item)

    def test_not_relevant(self):
        f = NewsFilter()
        item = make_item("Weather forecast for tomorrow", content="Sunny and warm")
        assert not f.is_relevant(item)

    def test_relevant_russian(self):
        f = NewsFilter()
        item = make_item("Новые санкции против отмывания денег")
        assert f.is_relevant(item)

    def test_relevance_score(self):
        f = NewsFilter()
        high = make_item("AML sanctions FATF", content="money laundering compliance")
        low = make_item("AML update", content="general information")
        assert f.calculate_relevance_score(high) > f.calculate_relevance_score(low)

    def test_deduplication(self):
        f = NewsFilter()
        item1 = make_item("AML news today")
        item2 = make_item("AML news today")  # Same title+url = same hash
        result = f.filter_and_rank([item1, item2])
        assert len(result) == 1

    def test_filter_and_rank(self):
        f = NewsFilter()
        items = [
            make_item("Weather today"),  # Not relevant
            make_item("FATF publishes new AML guidelines"),  # Relevant
            make_item("KYC compliance update for banks"),  # Relevant
        ]
        result = f.filter_and_rank(items)
        assert len(result) == 2
        assert all(f.is_relevant(item) for item in result)
