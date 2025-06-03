"""Enhanced ArXiv scraping functionality with async support and error handling."""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiohttp
import aiofiles
import feedparser

from models import ArxivArticle, Author, DownloadResult, ScrapingSession
from utils.storage import StorageManager
from utils.logger import logger
from config import config


class ArxivScraper:
    """Enhanced ArXiv scraper with async capabilities and robust error handling."""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage = storage_manager
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = asyncio.Semaphore(1)  # Ensure rate limiting
        
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={'User-Agent': 'ArXiv-Scraper/2.0 (Educational Purpose)'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def fetch_articles_from_category(self, category: str, start: int = 0, 
                                         max_results: int = 100) -> List[ArxivArticle]:
        """Fetch articles from a specific ArXiv category with retry logic."""
        
        for attempt in range(config.max_retries):
            try:
                async with self.rate_limiter:
                    await asyncio.sleep(config.rate_limit)  # Rate limiting
                    
                    params = {
                        'search_query': f'cat:{category}',
                        'sortBy': 'lastUpdatedDate',
                        'sortOrder': 'descending',
                        'start': start,
                        'max_results': max_results
                    }
                    
                    logger.debug(f"Fetching articles from {category} (start={start}, max={max_results})")
                    
                    async with self.session.get(config.api_base_url, params=params) as response:
                        response.raise_for_status()
                        content = await response.read()
                        
                        # Parse the Atom feed
                        feed = feedparser.parse(content)
                        articles = []
                        
                        for entry in feed.entries:
                            try:
                                article = self._parse_article_entry(entry)
                                articles.append(article)
                            except Exception as e:
                                logger.warning(f"Failed to parse article entry: {e}")
                                continue
                        
                        logger.info(f"Fetched {len(articles)} articles from {category}")
                        return articles
                        
            except Exception as e:
                if attempt < config.max_retries - 1:
                    wait_time = config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed for {category}: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch articles from {category} after {config.max_retries} attempts: {e}")
                    raise
    
    def _parse_article_entry(self, entry: Dict[str, Any]) -> ArxivArticle:
        """Parse a single article entry from the ArXiv feed."""
        
        # Extract ArXiv ID
        arxiv_id = entry.id.split('/')[-1]
        
        # Extract authors
        authors = []
        if hasattr(entry, 'authors'):
            for author_data in entry.authors:
                name = author_data.get('name', '')
                authors.append(Author(name=name))
        
        # Extract categories
        categories = []
        if hasattr(entry, 'tags'):
            categories = [tag.get('term', '') for tag in entry.tags]
        
        # Parse dates
        published_date = None
        updated_date = None
        
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published_date = datetime(*entry.published_parsed[:6])
        
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            updated_date = datetime(*entry.updated_parsed[:6])
        
        # Extract links
        link = entry.get('link', '')
        pdf_link = None
        source_link = None
        
        if hasattr(entry, 'links'):
            for link_data in entry.links:
                if link_data.get('type') == 'application/pdf':
                    pdf_link = link_data.get('href')
                elif link_data.get('title') == 'pdf':
                    pdf_link = link_data.get('href')
        
        # Generate source link
        if arxiv_id:
            source_link = f"{config.source_base_url}/{arxiv_id}"
        
        return ArxivArticle(
            arxiv_id=arxiv_id,
            title=entry.get('title', '').replace('\n', ' ').strip(),
            authors=authors,
            abstract=entry.get('summary', ''),
            categories=categories,
            primary_category=categories[0] if categories else None,
            published_date=published_date,
            updated_date=updated_date,
            doi=getattr(entry, 'arxiv_doi', None),
            journal_ref=getattr(entry, 'arxiv_journal_ref', None),
            link=link,
            pdf_link=pdf_link,
            source_link=source_link,
            comment=getattr(entry, 'arxiv_comment', None)
        )
    
    async def download_source(self, article: ArxivArticle, 
                            download_dir: str) -> DownloadResult:
        """Download the source files for an article with retry logic."""
        
        start_time = time.time()
        
        if not article.source_link:
            return DownloadResult(
                arxiv_id=article.arxiv_id,
                success=False,
                error_message="No source link available"
            )
        
        # Check if already downloaded
        if self.storage.is_downloaded(article.arxiv_id):
            return DownloadResult(
                arxiv_id=article.arxiv_id,
                success=False,
                error_message="Already downloaded"
            )
        
        for attempt in range(config.max_retries):
            try:
                async with self.rate_limiter:
                    await asyncio.sleep(config.rate_limit)  # Rate limiting
                    
                    download_path = Path(download_dir)
                    download_path.mkdir(parents=True, exist_ok=True)
                    
                    file_path = download_path / f"{article.arxiv_id}.tar.gz"
                    
                    async with self.session.get(article.source_link) as response:
                        response.raise_for_status()
                        
                        # Download file
                        async with aiofiles.open(file_path, 'wb') as file:
                            async for chunk in response.content.iter_chunked(8192):
                                await file.write(chunk)
                    
                    file_size = file_path.stat().st_size
                    download_time = time.time() - start_time
                    
                    result = DownloadResult(
                        arxiv_id=article.arxiv_id,
                        success=True,
                        file_path=str(file_path),
                        file_size=file_size,
                        download_time=download_time
                    )
                    
                    logger.success(f"Downloaded {article.arxiv_id} ({file_size} bytes)")
                    return result
                    
            except Exception as e:
                if attempt < config.max_retries - 1:
                    wait_time = config.retry_delay * (2 ** attempt)
                    logger.warning(f"Download attempt {attempt + 1} failed for {article.arxiv_id}: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"Download failed after {config.max_retries} attempts: {str(e)}"
                    logger.error(f"Failed to download {article.arxiv_id}: {error_msg}")
                    
                    return DownloadResult(
                        arxiv_id=article.arxiv_id,
                        success=False,
                        error_message=error_msg,
                        download_time=time.time() - start_time
                    )
    
    async def scrape_articles(self, categories: List[str], max_articles: int,
                            download_dir: str, session: ScrapingSession) -> List[ArxivArticle]:
        """Main scraping method that fetches and downloads articles."""
        
        all_articles = []
        downloaded_count = 0
        
        with logger.create_progress_bar("Scraping articles") as progress:
            task = progress.add_task("Processing categories", total=len(categories))
            
            for category in categories:
                if downloaded_count >= max_articles:
                    break
                
                try:
                    # Fetch articles from category
                    articles = await self.fetch_articles_from_category(
                        category=category,
                        max_results=min(100, max_articles - downloaded_count)
                    )
                    
                    session.articles_found += len(articles)
                    
                    # Process each article
                    for article in articles:
                        if downloaded_count >= max_articles:
                            break
                        
                        all_articles.append(article)
                        
                        # Display article info
                        logger.display_article(article.to_display_dict(), downloaded_count + 1)
                        
                        # Download source if not already downloaded
                        if not self.storage.is_downloaded(article.arxiv_id):
                            download_result = await self.download_source(article, download_dir)
                            await self.storage.save_download_result(download_result)
                            
                            if download_result.success:
                                downloaded_count += 1
                                session.articles_downloaded += 1
                            else:
                                session.articles_skipped += 1
                                if download_result.error_message != "Already downloaded":
                                    session.add_error(f"{article.arxiv_id}: {download_result.error_message}")
                        else:
                            session.articles_skipped += 1
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    error_msg = f"Failed to process category {category}: {e}"
                    logger.error(error_msg)
                    session.add_error(error_msg)
                    progress.update(task, advance=1)
                    continue
        
        return all_articles
