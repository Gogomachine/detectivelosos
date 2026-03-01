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

CREATE TABLE IF NOT EXISTS investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    address TEXT NOT NULL,
    stars_paid INTEGER DEFAULT 0,
    telegram_payment_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    report TEXT
);

CREATE INDEX IF NOT EXISTS idx_investigations_user ON investigations(user_id);
CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status);

CREATE TABLE IF NOT EXISTS used_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    post_type TEXT NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_used_topics_type ON used_topics(post_type);

CREATE TABLE IF NOT EXISTS banned_users (
    user_id INTEGER PRIMARY KEY,
    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    banned_by INTEGER
);
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
        """Get articles that haven't been posted yet, preferring recent and diverse sources."""
        cursor = await self.db.execute(
            """SELECT * FROM articles
               WHERE is_posted = 0
               ORDER BY fetched_at DESC, relevance_score DESC
               LIMIT ?""",
            (limit * 5,),  # Fetch more to allow source diversity filtering
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_diverse_unposted_articles(self, count: int = 3) -> list[dict]:
        """Get unposted articles ensuring source diversity (max 1 per source)."""
        cursor = await self.db.execute(
            """SELECT * FROM articles
               WHERE is_posted = 0
               ORDER BY fetched_at DESC, relevance_score DESC
               LIMIT 50"""
        )
        rows = await cursor.fetchall()
        all_articles = [dict(row) for row in rows]

        # Pick articles from different sources
        selected = []
        seen_sources = set()
        for article in all_articles:
            source = article["source"]
            if source not in seen_sources:
                selected.append(article)
                seen_sources.add(source)
                if len(selected) >= count:
                    break

        # If not enough diverse sources, fill from remaining
        if len(selected) < count:
            for article in all_articles:
                if article not in selected:
                    selected.append(article)
                    if len(selected) >= count:
                        break

        return selected

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

    async def get_random_article(self) -> dict | None:
        """Get a random article from the database."""
        cursor = await self.db.execute(
            "SELECT * FROM articles ORDER BY RANDOM() LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # --- Investigations ---

    async def create_investigation(
        self,
        user_id: int,
        username: str,
        address: str,
        stars_paid: int = 0,
        telegram_payment_id: str = "",
    ) -> int:
        """Create a new investigation order."""
        cursor = await self.db.execute(
            """INSERT INTO investigations
               (user_id, username, address, stars_paid, telegram_payment_id)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, address, stars_paid, telegram_payment_id),
        )
        await self.db.commit()
        logger.info(f"Investigation #{cursor.lastrowid} created for user {user_id}")
        return cursor.lastrowid

    async def get_pending_investigations(self) -> list[dict]:
        """Get all pending investigation orders."""
        cursor = await self.db.execute(
            """SELECT * FROM investigations
               WHERE status = 'pending'
               ORDER BY created_at"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def update_investigation_status(
        self, investigation_id: int, status: str, report: str = ""
    ):
        """Update investigation status."""
        if report:
            await self.db.execute(
                """UPDATE investigations
                   SET status = ?, report = ?, completed_at = ?
                   WHERE id = ?""",
                (status, report, datetime.now(timezone.utc).isoformat(), investigation_id),
            )
        else:
            await self.db.execute(
                "UPDATE investigations SET status = ? WHERE id = ?",
                (status, investigation_id),
            )
        await self.db.commit()

    # --- Used Topics ---

    async def save_used_topic(self, topic: str, post_type: str):
        """Save a topic as used to avoid repetition."""
        await self.db.execute(
            "INSERT INTO used_topics (topic, post_type) VALUES (?, ?)",
            (topic, post_type),
        )
        await self.db.commit()

    async def get_used_topics(self, post_type: str, limit: int = 50) -> list[str]:
        """Get recently used topics for a post type."""
        cursor = await self.db.execute(
            """SELECT topic FROM used_topics
               WHERE post_type = ?
               ORDER BY used_at DESC
               LIMIT ?""",
            (post_type, limit),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    # --- Banned Users ---

    async def ban_user(self, user_id: int, banned_by: int = 0):
        """Ban a user from using the bot."""
        await self.db.execute(
            """INSERT OR IGNORE INTO banned_users (user_id, banned_at, banned_by)
               VALUES (?, ?, ?)""",
            (user_id, datetime.now(timezone.utc).isoformat(), banned_by),
        )
        await self.db.commit()
        logger.info(f"User {user_id} banned by {banned_by}")

    async def unban_user(self, user_id: int):
        """Unban a user."""
        await self.db.execute(
            "DELETE FROM banned_users WHERE user_id = ?", (user_id,)
        )
        await self.db.commit()
        logger.info(f"User {user_id} unbanned")

    async def is_user_banned(self, user_id: int) -> bool:
        """Check if a user is banned."""
        cursor = await self.db.execute(
            "SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,)
        )
        return await cursor.fetchone() is not None

    # --- Agent State ---

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
