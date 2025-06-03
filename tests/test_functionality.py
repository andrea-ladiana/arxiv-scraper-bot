"""
Test script for ArXiv Enhanced Scraper.

This script tests the main functionality of the scraper.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to sys.path for imports
sys.path.append(str(Path(__file__).parent.parent))

from arxiv_scraper.core.models import ArxivArticle, FileFormat
from arxiv_scraper.core.scraping import ArxivScraper
from arxiv_scraper.core.storage import StorageManager
from arxiv_scraper.utils.logger import logger
from arxiv_scraper.utils.cache import Cache


async def test_search_articles():
    """Test searching for articles."""
    logger.info("Testing article search...")
    async with ArxivScraper() as scraper:
        # Search for articles on quantum computing
        articles = await scraper.search_articles(
            query="quantum computing", 
            max_results=5
        )
        
        logger.info(f"Found {len(articles)} articles.")
        for i, article in enumerate(articles, 1):
            logger.info(f"{i}. {article.title} ({article.arxiv_id})")
            
        return len(articles) > 0


async def test_fetch_article_by_id():
    """Test fetching a specific article by ID."""
    logger.info("\nTesting article fetch by ID...")
    async with ArxivScraper() as scraper:
        # Fetch a specific article (quantum computing paper)
        # Make sure to use a complete and valid ArXiv ID
        article = await scraper.fetch_article_by_id("2208.00733")
        
        if article:
            logger.info(f"Successfully fetched article: {article.title}")
            logger.info(f"Authors: {', '.join([author.name for author in article.authors])}")
            logger.info(f"Categories: {', '.join(article.categories)}")
            logger.info(f"Abstract: {article.abstract[:150]}...")
            return True
        else:
            logger.error("Failed to fetch article by ID")
            return False


async def test_storage_manager():
    """Test the storage manager functionality."""
    logger.info("\nTesting storage manager...")
    # Create a temporary test directory
    test_dir = Path("./test_storage")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Create a test storage manager
        storage = StorageManager(Path(test_dir) / "test_downloads.jsonl")
        
        # Create a mock download result
        from arxiv_scraper.core.models import DownloadResult
        result = DownloadResult(
            arxiv_id="test123",
            success=True,
            file_path=str(test_dir / "test123.pdf"),
            file_size=1024,
            file_format=FileFormat.PDF
        )
        
        # Save the result
        await storage.save_download_result(result)
        
        # Load the downloaded IDs
        await storage.load_downloaded_ids()
        
        # Check if our ID is in the downloaded set
        if storage.is_downloaded("test123"):
            logger.info("Storage manager successfully saved and loaded download result")
        else:
            logger.error("Storage manager failed to save or load download result")
            return False
          # Get stats
        stats = storage.get_stats()
        logger.info(f"Storage stats: {stats['total_records']} records")
        
        return True
    finally:
        # Clean up test files
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)


async def test_cache():
    """Test the caching functionality."""
    logger.info("\nTesting cache functionality...")
    # Create a temporary cache directory
    cache_dir = Path("./test_cache")
    cache_dir.mkdir(exist_ok=True)
    
    try:
        # Create a cache instance
        cache = Cache(cache_dir, ttl_days=1)
        
        # Store a value
        test_key = "test_key"
        test_value = {"name": "Test Data", "value": 42}
        
        success = await cache.set(test_key, test_value)
        if not success:
            logger.error("Failed to set cache value")
            return False
            
        # Retrieve the value
        retrieved = await cache.get(test_key)
        
        if retrieved == test_value:
            logger.info("Cache successfully stored and retrieved value")
        else:
            logger.error(f"Cache retrieval failed. Expected {test_value}, got {retrieved}")
            return False
            
        # Get cache stats
        stats = cache.get_stats()
        logger.info(f"Cache stats: {stats['total_entries']} entries")
        
        # Clear cache
        count = await cache.clear()
        logger.info(f"Cleared {count} cache entries")
        
        return True
    finally:
        # Clean up test files
        import shutil
        if cache_dir.exists():
            shutil.rmtree(cache_dir)


async def run_tests():
    """Run all the tests."""
    logger.display_banner("ArXiv Enhanced Scraper - Functional Tests", "Testing the main components")
    
    tests = [
        test_search_articles,
        test_fetch_article_by_id,
        test_storage_manager,
        test_cache,
    ]
    
    results = []
    
    for test in tests:
        try:
            result = await test()
            results.append((test.__name__, result))
        except Exception as e:
            logger.error(f"Test {test.__name__} failed with exception: {e}")
            results.append((test.__name__, False))
    
    # Report results
    logger.info("\n--- Test Results ---")
    all_passed = True
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        status_style = "bold green" if result else "bold red"
        logger.console.print(f"{name}: [{status_style}]{status}[/]")
        if not result:
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    print("Starting tests...")
    try:
        success = asyncio.run(run_tests())
        print(f"Tests completed with result: {success}")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error running tests: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
