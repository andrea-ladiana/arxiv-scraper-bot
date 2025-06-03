"""
Storage management for the ArXiv scraper.

This module provides utilities for managing the storage of downloaded articles,
metadata, and session information.
"""

import json
import asyncio
import hashlib
from pathlib import Path
from typing import Set, List, Dict, Any, Optional, Union, Iterator
from datetime import datetime
import aiofiles
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from arxiv_scraper.core.models import ArxivArticle, DownloadResult, ScrapingSession
from arxiv_scraper.core.config import config
from arxiv_scraper.utils.logger import logger


class StorageManager:
    """Manages storage operations for the scraper."""
    
    def __init__(self, jsonl_path: Optional[Path] = None):
        """Initialize the storage manager."""
        self.jsonl_path = jsonl_path or config.download.jsonl_path
        self.downloaded_ids: Set[str] = set()
        self.download_results: List[DownloadResult] = []
        self._lock = asyncio.Lock()  # For thread-safe operations
        
        # Create parent directory if it doesn't exist
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup session storage
        self.session_dir = self.jsonl_path.parent / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    async def load_downloaded_ids(self) -> None:
        """Load previously downloaded article IDs from JSONL file."""
        if not self.jsonl_path.exists():
            logger.info(f"No existing download record found at {self.jsonl_path}")
            return
        
        try:
            async with self._lock:
                async with aiofiles.open(self.jsonl_path, 'r', encoding='utf-8') as file:
                    line_count = 0
                    async for line in file:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                arxiv_id = data.get('arxiv_id', line)
                                self.downloaded_ids.add(arxiv_id)
                                
                                # Reconstruct DownloadResult if possible
                                if 'success' in data:
                                    try:
                                        result = DownloadResult.model_validate(data)
                                        self.download_results.append(result)
                                    except Exception:
                                        # Don't worry if we can't reconstruct the full result
                                        pass
                                
                                line_count += 1
                            except json.JSONDecodeError:
                                # Fallback: treat line as plain ID
                                self.downloaded_ids.add(line)
                                line_count += 1
                    
                    logger.info(f"Loaded {line_count} previously downloaded article IDs")
        
        except Exception as e:
            logger.error(f"Error loading downloaded IDs: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def save_download_result(self, result: DownloadResult) -> None:
        """Save a download result to the JSONL file with retries."""
        try:
            async with self._lock:
                # Add to memory
                self.downloaded_ids.add(result.arxiv_id)
                self.download_results.append(result)
                
                # Convert to serializable dict
                record = result.model_dump(mode='json')
                
                # Save to file
                async with aiofiles.open(self.jsonl_path, 'a', encoding='utf-8') as file:
                    await file.write(json.dumps(record) + '\n')
            
        except Exception as e:
            logger.error(f"Error saving download result for {result.arxiv_id}: {e}")
            raise
    
    async def bulk_save_results(self, results: List[DownloadResult]) -> None:
        """Save multiple download results in bulk."""
        if not results:
            return
        
        try:
            async with self._lock:
                async with aiofiles.open(self.jsonl_path, 'a', encoding='utf-8') as file:
                    for result in results:
                        self.downloaded_ids.add(result.arxiv_id)
                        
                        # Convert to serializable dict
                        record = result.model_dump(mode='json')
                        
                        await file.write(json.dumps(record) + '\n')
                
                self.download_results.extend(results)
                logger.info(f"Saved {len(results)} download results")
            
        except Exception as e:
            logger.error(f"Error bulk saving download results: {e}")
    
    def is_downloaded(self, arxiv_id: str) -> bool:
        """Check if an article has already been downloaded."""
        return arxiv_id in self.downloaded_ids
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        successful_downloads = sum(1 for r in self.download_results if r.success)
        failed_downloads = len(self.download_results) - successful_downloads
        
        total_size = sum(r.file_size or 0 for r in self.download_results 
                         if r.success and r.file_size is not None)
        
        formats = {}
        for result in self.download_results:
            if result.success and result.file_format:
                format_name = result.file_format.value
                formats[format_name] = formats.get(format_name, 0) + 1
        
        return {
            'total_records': len(self.downloaded_ids),
            'successful_downloads': successful_downloads,
            'failed_downloads': failed_downloads,
            'total_size_mb': round(total_size / (1024 * 1024), 2) if total_size else 0,
            'storage_file': str(self.jsonl_path),
            'formats': formats
        }
    
    async def save_session(self, session: ScrapingSession) -> Path:
        """Save scraping session data."""
        session_file = self.session_dir / f"session_{session.session_id}.json"
        
        try:
            # Convert to serializable dict
            session_data = session.model_dump(mode='json')
            
            async with aiofiles.open(session_file, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(session_data, indent=2))
            
            logger.info(f"Session data saved to {session_file}")
            return session_file
            
        except Exception as e:
            logger.error(f"Error saving session data: {e}")
            raise
    
    async def load_session(self, session_id: str) -> Optional[ScrapingSession]:
        """Load a session from storage."""
        session_file = self.session_dir / f"session_{session_id}.json"
        
        if not session_file.exists():
            logger.warning(f"Session file not found: {session_file}")
            return None
            
        try:
            async with aiofiles.open(session_file, 'r', encoding='utf-8') as file:
                content = await file.read()
                session_data = json.loads(content)
                return ScrapingSession.model_validate(session_data)
                
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions."""
        sessions = []
        
        for file_path in self.session_dir.glob('session_*.json'):
            try:
                session_id = file_path.stem.replace('session_', '')
                session = await self.load_session(session_id)
                if session:
                    sessions.append(session.to_summary_dict())
            except Exception as e:
                logger.error(f"Error loading session from {file_path}: {e}")
                
        return sessions
    
    async def export_articles_metadata(
        self, 
        articles: List[ArxivArticle], 
        export_file: Union[str, Path],
        format: str = 'json'
    ) -> Path:
        """Export articles metadata to a file."""
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == 'json':
                # Export to JSON
                articles_data = [article.model_dump(mode='json') for article in articles]
                
                async with aiofiles.open(export_path, 'w', encoding='utf-8') as file:
                    await file.write(json.dumps(articles_data, indent=2))
                    
            elif format.lower() == 'bibtex':
                # Export to BibTeX
                bibtex_entries = [article.to_bibtex() for article in articles]
                
                async with aiofiles.open(export_path, 'w', encoding='utf-8') as file:
                    await file.write('\n\n'.join(bibtex_entries))
                    
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.success(f"Exported {len(articles)} articles metadata to {export_file}")
            return export_path
            
        except Exception as e:
            logger.error(f"Error exporting articles metadata: {e}")
            raise
    
    async def backup_database(self, backup_path: Optional[Path] = None) -> Path:
        """Create a backup of the download database."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.jsonl_path.parent / f"backup_{timestamp}.jsonl"
            
        try:
            # Create parent directory if needed
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            async with aiofiles.open(self.jsonl_path, 'rb') as src:
                content = await src.read()
                
            async with aiofiles.open(backup_path, 'wb') as dst:
                await dst.write(content)
                
            logger.success(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
    
    async def restore_from_backup(self, backup_path: Path) -> bool:
        """Restore the download database from a backup."""
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
            
        try:
            # First create a backup of the current database
            await self.backup_database()
            
            # Then restore from the provided backup
            async with aiofiles.open(backup_path, 'rb') as src:
                content = await src.read()
                
            async with aiofiles.open(self.jsonl_path, 'wb') as dst:
                await dst.write(content)
                
            # Reload the IDs
            self.downloaded_ids.clear()
            self.download_results.clear()
            await self.load_downloaded_ids()
            
            logger.success(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False
    
    async def deduplicate_database(self) -> int:
        """Remove duplicate entries from the database."""
        try:
            # First create a backup
            await self.backup_database()
            
            # Read all entries
            entries = []
            seen_ids = set()
            
            async with aiofiles.open(self.jsonl_path, 'r', encoding='utf-8') as file:
                async for line in file:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        data = json.loads(line)
                        arxiv_id = data.get('arxiv_id')
                        if arxiv_id and arxiv_id not in seen_ids:
                            seen_ids.add(arxiv_id)
                            entries.append(line)
                    except json.JSONDecodeError:
                        # Keep the line if it's not valid JSON
                        entries.append(line)
            
            # Write back without duplicates
            async with aiofiles.open(self.jsonl_path, 'w', encoding='utf-8') as file:
                for entry in entries:
                    await file.write(entry + '\n')
                    
            removed_count = len(self.downloaded_ids) - len(seen_ids)
            
            # Reload the database
            self.downloaded_ids = seen_ids
            self.download_results.clear()
            await self.load_downloaded_ids()
            
            logger.success(f"Removed {removed_count} duplicate entries from the database")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error deduplicating database: {e}")
            return 0
    
    def cleanup_old_files(self, download_dir: Optional[Path] = None, days_old: int = 30) -> int:
        """Clean up old downloaded files."""
        dir_path = Path(download_dir) if download_dir else config.download.download_dir
        
        try:
            if not dir_path.exists():
                logger.warning(f"Directory not found: {dir_path}")
                return 0
            
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
            cleaned_count = 0
            
            for file_path in dir_path.glob('**/*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old files (>{days_old} days)")
            
            return cleaned_count
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0


class SearchIndex:
    """Simple search index for downloaded articles."""
    
    def __init__(self, index_dir: Optional[Path] = None):
        """Initialize the search index."""
        self.index_dir = index_dir or (config.download.cache_dir / "search_index")
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        
    async def index_article(self, article: ArxivArticle) -> None:
        """Add an article to the search index."""
        async with self._lock:
            # Create a simple index file with searchable content
            index_path = self.index_dir / f"{article.arxiv_id}.txt"
            
            # Combine searchable fields
            searchable_content = [
                article.title,
                article.abstract or "",
                " ".join(author.name for author in article.authors),
                " ".join(article.categories)
            ]
            
            content = "\n".join(searchable_content)
            
            async with aiofiles.open(index_path, 'w', encoding='utf-8') as f:
                await f.write(content)
                
    async def search(self, query: str, limit: int = 50) -> List[str]:
        """Search for articles matching the query and return article IDs."""
        if not query.strip():
            return []
            
        matches = []
        query_terms = query.lower().split()
        
        for index_file in self.index_dir.glob("*.txt"):
            if len(matches) >= limit:
                break
                
            arxiv_id = index_file.stem
            
            try:
                async with aiofiles.open(index_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    content_lower = content.lower()
                    
                    # Very basic search - check if all query terms are in the content
                    if all(term in content_lower for term in query_terms):
                        matches.append(arxiv_id)
            except Exception:
                continue
                
        return matches
        
    async def rebuild_index(self, articles: List[ArxivArticle]) -> int:
        """Rebuild the entire index."""
        # Clear existing index
        for file in self.index_dir.glob("*.txt"):
            file.unlink()
            
        # Add all articles
        for article in articles:
            await self.index_article(article)
            
        return len(articles)
