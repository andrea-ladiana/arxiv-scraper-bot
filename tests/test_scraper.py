"""Unit tests for the ArXiv scraper."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from models import ArxivArticle, Author, DownloadResult, ScrapingSession
from utils.scraping import ArxivScraper
from utils.storage import StorageManager
from utils.utils import ValidationUtils, FileUtils, CategoryUtils
from config import ScraperConfig


class TestModels:
    """Test data models."""
    
    def test_arxiv_article_creation(self):
        """Test ArxivArticle model creation."""
        article = ArxivArticle(
            arxiv_id="2301.12345",
            title="Test Article",
            authors=[Author(name="John Doe")],
            categories=["math.AG", "math.AT"]
        )
        
        assert article.arxiv_id == "2301.12345"
        assert article.title == "Test Article"
        assert len(article.authors) == 1
        assert article.authors[0].name == "John Doe"
        assert "math.AG" in article.categories
    
    def test_arxiv_id_validation(self):
        """Test ArXiv ID validation."""
        # Valid ID
        article = ArxivArticle(
            arxiv_id="https://arxiv.org/abs/2301.12345",
            title="Test",
            authors=[]
        )
        assert article.arxiv_id == "2301.12345"
        
        # Invalid ID should raise error
        with pytest.raises(ValueError):
            ArxivArticle(arxiv_id="", title="Test", authors=[])
    
    def test_download_result(self):
        """Test DownloadResult model."""
        result = DownloadResult(
            arxiv_id="2301.12345",
            success=True,
            file_path="/path/to/file.tar.gz",
            file_size=1024000
        )
        
        assert result.success
        assert "2301.12345" in str(result)
        assert "1024000 bytes" in str(result)
    
    def test_scraping_session(self):
        """Test ScrapingSession model."""
        session = ScrapingSession(
            session_id="test-123",
            target_categories=["math.AG"],
            target_count=10
        )
        
        session.articles_found = 8
        session.articles_downloaded = 6
        session.articles_skipped = 2
        session.finish()
        
        assert session.success_rate == 75.0
        assert session.duration is not None


class TestValidationUtils:
    """Test validation utilities."""
    
    def test_validate_arxiv_id(self):
        """Test ArXiv ID validation."""
        validator = ValidationUtils()
        
        assert validator.validate_arxiv_id("2301.12345")
        assert validator.validate_arxiv_id("math-ph/0123456")
        assert not validator.validate_arxiv_id("")
        assert not validator.validate_arxiv_id("invalid")
    
    def test_validate_category(self):
        """Test category validation."""
        validator = ValidationUtils()
        
        assert validator.validate_category("math.AG")
        assert validator.validate_category("cs.AI")
        assert not validator.validate_category("math")
        assert not validator.validate_category("")
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        validator = ValidationUtils()
        
        result = validator.sanitize_filename("file<name>with:invalid*chars")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert "*" not in result


class TestCategoryUtils:
    """Test category utilities."""
    
    def test_get_category_description(self):
        """Test getting category descriptions."""
        utils = CategoryUtils()
        
        desc = utils.get_category_description("math.AG")
        assert desc == "Algebraic Geometry"
        
        desc = utils.get_category_description("unknown.cat")
        assert desc == "unknown.cat"
    
    def test_get_field_from_category(self):
        """Test extracting field from category."""
        utils = CategoryUtils()
        
        assert utils.get_field_from_category("math.AG") == "math"
        assert utils.get_field_from_category("cs.AI") == "cs"
        assert utils.get_field_from_category("physics") == "physics"
    
    def test_group_categories_by_field(self):
        """Test grouping categories by field."""
        utils = CategoryUtils()
        categories = ["math.AG", "math.AT", "cs.AI", "cs.LG"]
        
        grouped = utils.group_categories_by_field(categories)
        
        assert "math" in grouped
        assert "cs" in grouped
        assert len(grouped["math"]) == 2
        assert len(grouped["cs"]) == 2


class TestStorageManager:
    """Test storage manager."""
    
    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage manager."""
        jsonl_path = tmp_path / "test_downloads.jsonl"
        return StorageManager(str(jsonl_path))
    
    @pytest.mark.asyncio
    async def test_save_and_load(self, temp_storage):
        """Test saving and loading download results."""
        # Save a result
        result = DownloadResult(
            arxiv_id="2301.12345",
            success=True,
            file_path="/test/path.tar.gz",
            file_size=1024
        )
        
        await temp_storage.save_download_result(result)
        
        # Check that it's in memory
        assert "2301.12345" in temp_storage.downloaded_ids
        
        # Create new storage manager and load
        new_storage = StorageManager(temp_storage.jsonl_path)
        await new_storage.load_downloaded_ids()
        
        assert "2301.12345" in new_storage.downloaded_ids
    
    def test_is_downloaded(self, temp_storage):
        """Test checking if article is downloaded."""
        temp_storage.downloaded_ids.add("2301.12345")
        
        assert temp_storage.is_downloaded("2301.12345")
        assert not temp_storage.is_downloaded("2301.67890")


class TestConfig:
    """Test configuration."""
    
    def test_config_creation(self):
        """Test configuration model creation."""
        config = ScraperConfig()
        
        assert config.total_articles > 0
        assert config.batch_size > 0
        assert len(config.math_categories) > 0
        assert config.api_base_url.startswith("http")
    
    def test_get_categories_by_field(self):
        """Test getting categories by field."""
        config = ScraperConfig()
        
        math_cats = config.get_categories_by_field("math")
        assert len(math_cats) > 0
        assert all(cat.startswith("math.") for cat in math_cats)
        
        cs_cats = config.get_categories_by_field("cs")
        assert len(cs_cats) > 0
        assert all(cat.startswith("cs.") for cat in cs_cats)


# Integration tests would go here
class TestIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_fetch_single_article(self):
        """Test fetching a single article (integration test)."""
        # This would test the actual ArXiv API
        # Mark as slow test that might not run in CI
        pass


if __name__ == "__main__":
    pytest.main([__file__])
