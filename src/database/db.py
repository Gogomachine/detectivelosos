"""SQLite database for storing articles, posts, and agent state."""

import logging
import os
from datetime import datetime, timezone

import aiosqlite

from config import DATABASE_PATH

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    content TEXT,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    relevance_score INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_posted INTEGER DEFAULT 0,
    post_id INTEGER REFERENCES posts(id)
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_type TEXT NOT NULL,
    content TEXT NOT NULL,
    telegram_message_id INTEGER,
    article_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP,
    status TEXT DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS agent_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_articles_hash ON articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_articles_posted ON articles(is_posted);
CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
"""


class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DATABASE_PATH
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        """Initialize database connection and create tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()
        logger.info(f"Database connected: {self.db_path}")

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    # --- Articles ---

    async def article_exists(self, content_hash: str) -> bool:
        """Check if an article already exists by its content hash."""
        cursor = await self.db.execute(
            "SELECT 1 FROM articles WHERE content_hash = ?", (content_hash,)
        )
        return await cursor.fetchone() is not None

    async def save_article(
        self,
        content_hash: str,
        title: str,
        url: str,
        content: str,
        source: str,
        category: str,
        language: str = "en",
        relevance_score: int = 0,
        published_at: datetime | None = None,
    ) -> int | None:
        """Save an article to the database. Returns article ID or None if duplicate."""
        if await self.article_exists(content_hash):
            return None

        cursor = await self.db.execute(
            """INSERT INTO articles
               (content_hash, title, url, content, source, category, language,
                relevance_score, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                content_hash, title, url, content, source, category, language,
                relevance_score,
                (published_at or datetime.now(timezone.utc)).isoformat(),
            ),
        )
        await self.db.commit()
        logger.info(f"Saved article: {title[:60]}")
        return cursor.lastrowid

    async def get_unposted_articles(self, limit: int = 10) -> list[dict]:
        """Get articles that haven't been posted yet."""
        cursor = await self.db.execute(
            """SELECT * FROM articles
               WHERE is_posted = 0
               ORDER BY relevance_score DESC, fetched_at DESC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def mark_article_posted(self, article_id: int, post_id: int):
        """Mark an article as posted."""
        await self.db.execute(
            "UPDATE articles SET is_posted = 1, post_id = ? WHERE id = ?",
            (post_id, article_id),
        )
        await self.db.commit()

    async def get_articles_since(self, since: datetime) -> list[dict]:
        """Get all articles since a given datetime."""
        cursor = await self.db.execute(
            """SELECT * FROM articles
               WHERE fetched_at >= ?
               ORDER BY relevance_score DESC""",
            (since.isoformat(),),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_article_count_today(self) -> int:
        """Get number of articles fetched today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor = await self.db.execute(
            "SELECT COUNT(*) FROM articles WHERE DATE(fetched_at) = ?", (today,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    # --- Posts ---

    async def save_post(
        self,
        post_type: str,
        content: str,
        article_ids: str = "",
        status: str = "draft",
    ) -> int:
        """Save a post to the database."""
        cursor = await self.db.execute(
            """INSERT INTO posts (post_type, content, article_ids, status)
               VALUES (?, ?, ?, ?)""",
            (post_type, content, article_ids, status),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def update_post_status(
        self, post_id: int, status: str, telegram_message_id: int | None = None
    ):
        """Update post status after publishing."""
        if telegram_message_id:
            await self.db.execute(
                """UPDATE posts SET status = ?, telegram_message_id = ?, posted_at = ?
                   WHERE id = ?""",
                (status, telegram_message_id, datetime.now(timezone.utc).isoformat(), post_id),
            )
        else:
            await self.db.execute(
                "UPDATE posts SET status = ? WHERE id = ?", (status, post_id)
            )
        await self.db.commit()

    async def get_posts_today(self) -> list[dict]:
        """Get all posts created today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor = await self.db.execute(
            """SELECT * FROM posts
               WHERE DATE(created_at) = ? AND status = 'published'
               ORDER BY created_at""",
            (today,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_post_count_today(self) -> int:
        """Get number of posts published today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor = await self.db.execute(
            """SELECT COUNT(*) FROM posts
               WHERE DATE(created_at) = ? AND status = 'published'""",
            (today,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    # --- Agent State ---

    async def get_state(self, key: str, default: str = "") -> str:
        """Get agent state value."""
        cursor = await self.db.execute(
            "SELECT value FROM agent_state WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else default

    async def set_state(self, key: str, value: str):
        """Set agent state value."""
        await self.db.execute(
            """INSERT INTO agent_state (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?""",
            (key, value, datetime.now(timezone.utc).isoformat(),
             value, datetime.now(timezone.utc).isoformat()),
        )
        await self.db.commit()
