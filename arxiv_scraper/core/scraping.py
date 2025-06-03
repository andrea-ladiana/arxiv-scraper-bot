"""
Enhanced ArXiv scraping functionality with async support and comprehensive error handling.

This module provides the core scraping functionality for the ArXiv scraper,
including article fetching, parsing, and downloading with robust error handling
and rate limiting.
"""

import asyncio
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set, Union
import aiohttp
import aiofiles
import feedparser
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from rich.progress import Progress, TaskID

from arxiv_scraper.core.models import ArxivArticle, Author, DownloadResult, ScrapingSession, FileFormat
from arxiv_scraper.core.config import config
from arxiv_scraper.utils.logger import logger
from arxiv_scraper.utils.cache import Cache


class ArxivScraper:
    """Enhanced ArXiv scraper with async capabilities and robust error handling."""
    
    def __init__(self):
        """Initialize the scraper with configuration and caching."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = asyncio.Semaphore(config.api.max_connections)
        self.cache = Cache(config.download.cache_dir) if config.enable_caching else None
        self.fetched_ids: Set[str] = set()  # Track IDs to avoid duplicates
        self.progress: Optional[Progress] = None
        self.download_task: Optional[TaskID] = None
        
    async def __aenter__(self) -> "ArxivScraper":
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=config.api.timeout)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={'User-Agent': config.api.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def fetch_articles_from_category(
        self, 
        category: str, 
        start: int = 0, 
        max_results: int = 100
    ) -> List[ArxivArticle]:
        """Fetch articles from a specific ArXiv category with retry logic."""
        
        # Check cache first if enabled
        cache_key = f"category_{category}_start{start}_max{max_results}"
        
        if self.cache and config.enable_caching:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Using cached results for {category} (start={start}, max={max_results})")
                return cached_result
        
        async with self.rate_limiter:
            await asyncio.sleep(config.api.rate_limit)  # Rate limiting
            
            params = {
                'search_query': f'cat:{category}',
                'sortBy': 'lastUpdatedDate',
                'sortOrder': 'descending',
                'start': start,
                'max_results': max_results
            }
            
            logger.debug(f"Fetching articles from {category} (start={start}, max={max_results})")
            
            if not self.session:
                raise RuntimeError("HTTP session not initialized")
            
            async with self.session.get(config.api.api_base_url, params=params) as response:
                response.raise_for_status()
                content = await response.read()
                
                # Parse the Atom feed
                feed = feedparser.parse(content)
                articles = []
                
                for entry in feed.entries:
                    try:
                        article = self._parse_article_entry(entry)
                        
                        # Skip duplicates
                        if article.arxiv_id not in self.fetched_ids:
                            articles.append(article)
                            self.fetched_ids.add(article.arxiv_id)
                    except Exception as e:
                        logger.warning(f"Failed to parse article entry: {e}")
                        continue
                
                logger.info(f"Fetched {len(articles)} articles from {category}")
                
                # Cache the result if caching is enabled
                if self.cache and config.enable_caching:
                    await self.cache.set(cache_key, articles)
                
                return articles
                
    def _parse_article_entry(self, entry: Dict[str, Any]) -> ArxivArticle:
        """Parse a single article entry from the ArXiv feed."""
        
        # Extract ArXiv ID
        arxiv_id = entry.id.split('/')[-1]
        
        # Extract authors
        authors = []
        if hasattr(entry, 'authors'):
            for author_data in entry.authors:
                name = author_data.get('name', '')
                # Try to get affiliation if any
                affiliation = None
                if hasattr(entry, 'arxiv_affiliation') and entry.arxiv_affiliation:
                    affiliation = entry.arxiv_affiliation
                
                authors.append(Author(name=name, affiliation=affiliation))
        
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
            source_link = f"{config.api.source_base_url}/{arxiv_id}"
            
            # Generate PDF link if not found
            if not pdf_link:
                pdf_link = f"{config.api.pdf_base_url}/{arxiv_id}.pdf"
        
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
    
    async def download_article(
        self, 
        article: ArxivArticle,
        download_dir: Path,
        format: FileFormat = FileFormat.SOURCE,
        downloaded_ids: Optional[Set[str]] = None
    ) -> DownloadResult:
        """Download an article with the specified format."""
        start_time = time.time()
        
        # Check if already downloaded
        if downloaded_ids and article.arxiv_id in downloaded_ids:
            return DownloadResult(
                arxiv_id=article.arxiv_id,
                success=False,
                error_message="Already downloaded",
                file_format=format
            )
        
        # Get the appropriate URL based on format
        if format == FileFormat.PDF:
            url = article.pdf_link
            if not url:
                return DownloadResult(
                    arxiv_id=article.arxiv_id,
                    success=False,
                    error_message="No PDF link available",
                    file_format=format
                )
        elif format == FileFormat.SOURCE:
            url = article.source_link
            if not url:
                return DownloadResult(
                    arxiv_id=article.arxiv_id,
                    success=False,
                    error_message="No source link available",
                    file_format=format
                )
        else:
            return DownloadResult(
                arxiv_id=article.arxiv_id,
                success=False,
                error_message=f"Unsupported download format: {format}",
                file_format=format
            )
        
        try:
            download_path = Path(download_dir)
            download_path.mkdir(parents=True, exist_ok=True)
            
            filename = article.get_download_filename(format)
            file_path = download_path / filename
            
            # Create a download task in the progress bar if available
            if self.progress and self.download_task:
                task_id = self.progress.add_task(f"Downloading {filename}", total=1)
            else:
                task_id = None
            
            async with self.rate_limiter:
                await asyncio.sleep(config.api.rate_limit)  # Rate limiting
                
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded_size = 0
                    
                    if self.progress and task_id:
                        # Update with the actual file size if available
                        if total_size > 0:
                            self.progress.update(task_id, total=total_size)
                    
                    # Download file
                    async with aiofiles.open(file_path, 'wb') as file:
                        async for chunk in response.content.iter_chunked(8192):
                            await file.write(chunk)
                            downloaded_size += len(chunk)
                            if self.progress and task_id and total_size > 0:
                                self.progress.update(task_id, completed=downloaded_size)
            
            # Calculate checksum
            file_md5 = await self._calculate_file_hash(file_path)
            
            file_size = file_path.stat().st_size
            download_time = time.time() - start_time
            
            # Complete the task
            if self.progress and task_id:
                self.progress.update(task_id, completed=total_size if total_size > 0 else 1)
                self.progress.remove_task(task_id)
            
            metadata = {
                'format': format.value,
                'md5': file_md5,
                'size_bytes': file_size,
                'download_time_sec': download_time,
            }
            
            result = DownloadResult(
                arxiv_id=article.arxiv_id,
                success=True,
                file_path=file_path,
                file_size=file_size,
                file_format=format,
                download_time=download_time,
                metadata=metadata
            )
            
            logger.success(f"Downloaded {article.arxiv_id} [{format.value}] ({file_size} bytes)")
            
            # Update overall progress
            if self.progress and self.download_task:
                self.progress.update(self.download_task, advance=1)
                
            return result
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(f"Failed to download {article.arxiv_id}: {error_msg}")
            
            # Update progress with error
            if self.progress and task_id:
                self.progress.remove_task(task_id)
            
            if self.progress and self.download_task:
                self.progress.update(self.download_task, advance=1)
                
            return DownloadResult(
                arxiv_id=article.arxiv_id,
                success=False,
                error_message=error_msg,
                file_format=format,
                download_time=time.time() - start_time
            )
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash for a file asynchronously."""
        hash_obj = hashlib.md5()
        
        async with aiofiles.open(file_path, 'rb') as file:
            while chunk := await file.read(8192):
                hash_obj.update(chunk)
                
        return hash_obj.hexdigest()
    
    async def scrape_articles(
        self,
        categories: List[str],
        max_articles: int,
        download_dir: Path,
        session: ScrapingSession,
        downloaded_ids: Optional[Set[str]] = None,
        progress: Optional[Progress] = None
    ) -> List[ArxivArticle]:
        """Main scraping method that fetches and downloads articles."""
        
        all_articles = []
        downloaded_count = 0
        self.progress = progress
        
        # Create a task for overall download progress
        if progress:
            task_description = f"Downloading {max_articles} articles"
            self.download_task = progress.add_task(task_description, total=max_articles)
        
        # Store the set of downloaded IDs
        if downloaded_ids is None:
            downloaded_ids = set()
        
        # Set up download semaphore for concurrency control
        download_semaphore = asyncio.Semaphore(config.download.max_concurrent_downloads)
        
        # Process each category
        for category in categories:
            if downloaded_count >= max_articles:
                break
            
            try:
                # Calculate how many articles to fetch
                articles_needed = max_articles - downloaded_count
                
                # Fetch articles from category
                articles = await self.fetch_articles_from_category(
                    category=category,
                    max_results=min(100, articles_needed)
                )
                
                session.articles_found += len(articles)
                all_articles.extend(articles)
                
                # Process each article
                download_tasks = []
                for article in articles[:articles_needed]:
                    # Prepare download formats based on session configuration
                    formats = list(session.download_formats)
                    
                    for format in formats:
                        if article.arxiv_id in downloaded_ids:
                            session.articles_skipped += 1
                            continue
                        
                        download_tasks.append(self._download_with_semaphore(
                            semaphore=download_semaphore,
                            article=article,
                            download_dir=download_dir,
                            format=format,
                            downloaded_ids=downloaded_ids,
                            session=session
                        ))
                
                # Run downloads concurrently
                if download_tasks:
                    results = await asyncio.gather(*download_tasks, return_exceptions=True)
                    
                    # Process results
                    for result in results:
                        if isinstance(result, Exception):
                            session.add_error(f"Download exception: {str(result)}")
                        elif isinstance(result, DownloadResult):
                            if result.success:
                                downloaded_count += 1
                                downloaded_ids.add(result.arxiv_id)
                
                # Check if we've reached the target
                if downloaded_count >= max_articles:
                    break
                    
            except Exception as e:
                error_msg = f"Failed to process category {category}: {e}"
                logger.error(error_msg)
                session.add_error(error_msg)
                continue
                
        return all_articles
    
    async def _download_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        article: ArxivArticle,
        download_dir: Path,
        format: FileFormat,
        downloaded_ids: Set[str],
        session: ScrapingSession
    ) -> DownloadResult:
        """Download an article with a semaphore for concurrency control."""
        async with semaphore:
            result = await self.download_article(
                article=article,
                download_dir=download_dir,
                format=format,
                downloaded_ids=downloaded_ids
            )
            
            if result.success:
                session.articles_downloaded += 1
            else:
                if result.error_message != "Already downloaded":
                    session.articles_skipped += 1
                    session.add_error(f"{article.arxiv_id}: {result.error_message}")
                
            return result
            
    async def fetch_article_by_id(self, arxiv_id: str) -> Optional[ArxivArticle]:
        """Fetch a single article by its ArXiv ID."""
        # Clean the ID
        arxiv_id = arxiv_id.strip()
        if '/' in arxiv_id:
            arxiv_id = arxiv_id.split('/')[-1]
            
        # Check cache first
        cache_key = f"article_{arxiv_id}"
        if self.cache and config.enable_caching:
            cached_article = await self.cache.get(cache_key)
            if cached_article:
                logger.debug(f"Using cached article data for {arxiv_id}")
                return cached_article
                
        # Fetch from API
        try:
            async with self.rate_limiter:
                await asyncio.sleep(config.api.rate_limit)
                
                params = {
                    'id_list': arxiv_id,
                    'max_results': 1
                }
                
                if not self.session:
                    raise RuntimeError("HTTP session not initialized")
                
                async with self.session.get(config.api.api_base_url, params=params) as response:
                    response.raise_for_status()
                    content = await response.read()
                    
                    feed = feedparser.parse(content)
                    
                    if not feed.entries:
                        logger.warning(f"No article found with ID: {arxiv_id}")
                        return None
                        
                    article = self._parse_article_entry(feed.entries[0])
                    
                    # Cache the result
                    if self.cache and config.enable_caching:
                        await self.cache.set(cache_key, article)
                    
                    return article
                    
        except Exception as e:
            logger.error(f"Error fetching article {arxiv_id}: {e}")
            return None
            
    async def search_articles(
        self, 
        query: str, 
        max_results: int = 50,
        categories: Optional[List[str]] = None
    ) -> List[ArxivArticle]:
        """Search for articles matching the query."""
        try:
            # Construct search query
            search_query = f"all:{query}"
            if categories:
                category_filter = " OR ".join([f"cat:{cat}" for cat in categories])
                search_query = f"({search_query}) AND ({category_filter})"
            
            cache_key = f"search_{hashlib.md5(search_query.encode()).hexdigest()}_max{max_results}"
            
            # Check cache first
            if self.cache and config.enable_caching:
                cached_results = await self.cache.get(cache_key)
                if cached_results:
                    logger.debug(f"Using cached search results for query: {query}")
                    return cached_results
            
            # Fetch from API
            async with self.rate_limiter:
                await asyncio.sleep(config.api.rate_limit)
                
                params = {
                    'search_query': search_query,
                    'sortBy': 'relevance',
                    'sortOrder': 'descending',
                    'max_results': max_results
                }
                
                if not self.session:
                    raise RuntimeError("HTTP session not initialized")
                
                async with self.session.get(config.api.api_base_url, params=params) as response:
                    response.raise_for_status()
                    content = await response.read()
                    
                    feed = feedparser.parse(content)
                    articles = []
                    
                    for entry in feed.entries:
                        try:
                            article = self._parse_article_entry(entry)
                            articles.append(article)
                        except Exception as e:
                            logger.warning(f"Failed to parse article during search: {e}")
                    
                    # Cache the results
                    if self.cache and config.enable_caching:
                        await self.cache.set(cache_key, articles)
                    
                    logger.info(f"Search for '{query}' returned {len(articles)} results")
                    return articles
                    
        except Exception as e:
            logger.error(f"Error searching for articles: {e}")
            return []
