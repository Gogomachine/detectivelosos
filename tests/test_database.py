"""Tests for database module."""

import os
import tempfile

import pytest
import pytest_asyncio

from src.database.db import Database


@pytest_asyncio.fixture
async def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    database = Database(db_path=db_path)
    await database.connect()
    yield database
    await database.close()
    os.unlink(db_path)


@pytest.mark.asyncio
async def test_save_and_check_article(db):
    article_id = await db.save_article(
        content_hash="abc123",
        title="Test AML Article",
        url="https://example.com/test",
        content="Some content about money laundering",
        source="Test Source",
        category="news",
    )
    assert article_id is not None
    assert await db.article_exists("abc123")


@pytest.mark.asyncio
async def test_no_duplicate_articles(db):
    await db.save_article(
        content_hash="dup123",
        title="Duplicate",
        url="https://example.com/dup",
        content="Content",
        source="Source",
        category="news",
    )
    result = await db.save_article(
        content_hash="dup123",
        title="Duplicate Again",
        url="https://example.com/dup2",
        content="Content 2",
        source="Source 2",
        category="news",
    )
    assert result is None


@pytest.mark.asyncio
async def test_unposted_articles(db):
    await db.save_article(
        content_hash="unposted1",
        title="Unposted Article",
        url="https://example.com/unposted",
        content="AML content",
        source="Source",
        category="news",
        relevance_score=5,
    )
    articles = await db.get_unposted_articles()
    assert len(articles) == 1
    assert articles[0]["title"] == "Unposted Article"


@pytest.mark.asyncio
async def test_save_and_update_post(db):
    post_id = await db.save_post(
        post_type="news",
        content="Test post content",
        article_ids="1",
        status="draft",
    )
    assert post_id is not None

    await db.update_post_status(post_id, "published", telegram_message_id=42)


@pytest.mark.asyncio
async def test_agent_state(db):
    await db.set_state("test_key", "test_value")
    value = await db.get_state("test_key")
    assert value == "test_value"

    # Default for missing key
    missing = await db.get_state("missing", "default")
    assert missing == "default"
