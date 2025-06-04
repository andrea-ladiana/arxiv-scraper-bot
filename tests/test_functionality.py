"""Functional tests for the enhanced ArXiv scraper."""

from pathlib import Path

import pytest

from arxiv_scraper.core.models import ArxivArticle, FileFormat
from arxiv_scraper.core.scraping import ArxivScraper
from arxiv_scraper.core.storage import StorageManager
from arxiv_scraper.utils.logger import logger
from arxiv_scraper.utils.cache import Cache


def _has_network(host: str = "export.arxiv.org", port: int = 80) -> bool:
    """Return True if the given host is reachable."""
    import socket

    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except OSError:
        return False


@pytest.mark.asyncio
async def test_search_articles():
    """Search for a small set of articles."""
    if not _has_network():
        pytest.skip("network unavailable")
    logger.info("Testing article search...")
    async with ArxivScraper() as scraper:
        articles = await scraper.search_articles(
            query="quantum computing",
            max_results=5,
        )

        logger.info(f"Found {len(articles)} articles.")
        for i, article in enumerate(articles, 1):
            logger.info(f"{i}. {article.title} ({article.arxiv_id})")

        assert len(articles) > 0


@pytest.mark.asyncio
async def test_fetch_article_by_id():
    """Fetch a single article by its identifier."""
    if not _has_network():
        pytest.skip("network unavailable")
    logger.info("\nTesting article fetch by ID...")
    async with ArxivScraper() as scraper:
        article = await scraper.fetch_article_by_id("2208.00733")

        assert article is not None
        logger.info(f"Successfully fetched article: {article.title}")


@pytest.mark.asyncio
async def test_storage_manager():
    """Ensure download results are stored and loaded correctly."""
    logger.info("\nTesting storage manager...")

    test_dir = Path("./test_storage")
    test_dir.mkdir(exist_ok=True)

    try:
        storage = StorageManager(Path(test_dir) / "test_downloads.jsonl")

        from arxiv_scraper.core.models import DownloadResult

        result = DownloadResult(
            arxiv_id="test123",
            success=True,
            file_path=str(test_dir / "test123.pdf"),
            file_size=1024,
            file_format=FileFormat.PDF,
        )

        await storage.save_download_result(result)

        await storage.load_downloaded_ids()

        assert storage.is_downloaded("test123")

        stats = storage.get_stats()
        logger.info(f"Storage stats: {stats['total_records']} records")
    finally:
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cache():
    """Verify cache set/get and clear operations."""
    logger.info("\nTesting cache functionality...")
    cache_dir = Path("./test_cache")
    cache_dir.mkdir(exist_ok=True)

    try:
        cache = Cache(cache_dir, ttl_days=1)

        test_key = "test_key"
        test_value = {"name": "Test Data", "value": 42}

        success = await cache.set(test_key, test_value)
        assert success

        retrieved = await cache.get(test_key)
        assert retrieved == test_value

        stats = cache.get_stats()
        logger.info(f"Cache stats: {stats['total_entries']} entries")

        count = await cache.clear()
        logger.info(f"Cleared {count} cache entries")
        assert count >= 1
    finally:
        import shutil

        if cache_dir.exists():
            shutil.rmtree(cache_dir)


