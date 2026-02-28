"""Twitter/X parser for monitoring AML-related accounts."""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

import tweepy

from src.parsers.rss_parser import NewsItem

logger = logging.getLogger(__name__)


class TwitterParser:
    """Fetches tweets from monitored AML accounts via Twitter API v2."""

    def __init__(self, bearer_token: str):
        self.client = tweepy.Client(
            bearer_token=bearer_token,
            wait_on_rate_limit=True,
        )

    async def fetch_user_tweets(
        self, account: dict, since_minutes: int = 60
    ) -> list[NewsItem]:
        """Fetch recent tweets from a single account."""
        username = account["username"]
        category = account.get("category", "twitter")

        try:
            items = await asyncio.to_thread(
                self._fetch_tweets, username, category, since_minutes
            )
            return items
        except Exception as e:
            logger.error(f"Twitter fetch failed for @{username}: {e}")
            return []

    def _fetch_tweets(
        self, username: str, category: str, since_minutes: int
    ) -> list[NewsItem]:
        """Fetch tweets (runs in thread)."""
        # Get user ID
        user = self.client.get_user(username=username)
        if not user or not user.data:
            logger.warning(f"Twitter user @{username} not found")
            return []

        user_id = user.data.id

        # Fetch recent tweets
        response = self.client.get_users_tweets(
            id=user_id,
            max_results=10,
            tweet_fields=["created_at", "text", "entities", "public_metrics"],
            exclude=["retweets", "replies"],
        )

        if not response or not response.data:
            return []

        items = []
        for tweet in response.data:
            text = tweet.text or ""

            # Build tweet URL
            tweet_url = f"https://x.com/{username}/status/{tweet.id}"

            # Extract hashtags
            tags = []
            if tweet.entities and "hashtags" in tweet.entities:
                tags = [h["tag"] for h in tweet.entities["hashtags"]]

            published = tweet.created_at or datetime.now(timezone.utc)
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)

            items.append(
                NewsItem(
                    title=self._extract_title(text),
                    url=tweet_url,
                    content=text,
                    source=f"@{username}",
                    category=category,
                    published_at=published,
                    language="en",
                    tags=tags,
                    content_hash=hashlib.md5(
                        f"{tweet.id}".encode()
                    ).hexdigest(),
                )
            )

        logger.info(f"Fetched {len(items)} tweets from @{username}")
        return items

    @staticmethod
    def _extract_title(text: str) -> str:
        """Extract a short title from tweet text."""
        # Take first sentence or first 120 chars
        for sep in [". ", ".\n", "\n\n", "\n"]:
            pos = text.find(sep)
            if 10 < pos < 150:
                return text[:pos].strip()
        if len(text) > 120:
            # Cut at word boundary
            cut = text[:120].rfind(" ")
            if cut > 50:
                return text[:cut].strip() + "..."
        return text.strip()

    async def fetch_all_accounts(
        self, accounts: list[dict], since_minutes: int = 60
    ) -> list[NewsItem]:
        """Fetch tweets from all monitored accounts."""
        tasks = [
            self.fetch_user_tweets(acc, since_minutes) for acc in accounts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Twitter fetch error: {result}")
                continue
            all_items.extend(result)

        all_items.sort(key=lambda x: x.published_at, reverse=True)
        logger.info(f"Total tweets fetched: {len(all_items)}")
        return all_items
