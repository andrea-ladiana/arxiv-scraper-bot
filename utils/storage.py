"""Storage management for the ArXiv scraper."""

import json
import os
import aiofiles
from pathlib import Path
from typing import Set, List, Dict, Any, Optional
from datetime import datetime

from models import ArxivArticle, DownloadResult, ScrapingSession
from utils.logger import logger


class StorageManager:
    """Manages storage operations for the scraper."""
    
    def __init__(self, jsonl_path: str):
        self.jsonl_path = Path(jsonl_path)
        self.downloaded_ids: Set[str] = set()
        self.download_results: List[DownloadResult] = []
        
        # Create parent directory if it doesn't exist
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def load_downloaded_ids(self) -> None:
        """Load previously downloaded article IDs from JSONL file."""
        if not self.jsonl_path.exists():
            logger.info(f"No existing download record found at {self.jsonl_path}")
            return
        
        try:
            async with aiofiles.open(self.jsonl_path, 'r', encoding='utf-8') as file:
                line_count = 0
                async for line in file:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            arxiv_id = data.get('arxiv_id', line)
                            self.downloaded_ids.add(arxiv_id)
                            line_count += 1
                        except json.JSONDecodeError:
                            # Fallback: treat line as plain ID
                            self.downloaded_ids.add(line)
                            line_count += 1
                
                logger.info(f"Loaded {line_count} previously downloaded article IDs")
        
        except Exception as e:
            logger.error(f"Error loading downloaded IDs: {e}")
    
    async def save_download_result(self, result: DownloadResult) -> None:
        """Save a download result to the JSONL file."""
        try:
            # Add to memory
            self.downloaded_ids.add(result.arxiv_id)
            self.download_results.append(result)
            
            # Save to file
            record = {
                'arxiv_id': result.arxiv_id,
                'success': result.success,
                'file_path': result.file_path,
                'file_size': result.file_size,
                'error_message': result.error_message,
                'download_time': result.download_time,
                'timestamp': result.timestamp.isoformat()
            }
            
            async with aiofiles.open(self.jsonl_path, 'a', encoding='utf-8') as file:
                await file.write(json.dumps(record, ensure_ascii=False) + '\n')
            
        except Exception as e:
            logger.error(f"Error saving download result for {result.arxiv_id}: {e}")
    
    async def bulk_save_results(self, results: List[DownloadResult]) -> None:
        """Save multiple download results in bulk."""
        if not results:
            return
        
        try:
            async with aiofiles.open(self.jsonl_path, 'a', encoding='utf-8') as file:
                for result in results:
                    self.downloaded_ids.add(result.arxiv_id)
                    
                    record = {
                        'arxiv_id': result.arxiv_id,
                        'success': result.success,
                        'file_path': result.file_path,
                        'file_size': result.file_size,
                        'error_message': result.error_message,
                        'download_time': result.download_time,
                        'timestamp': result.timestamp.isoformat()
                    }
                    
                    await file.write(json.dumps(record, ensure_ascii=False) + '\n')
            
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
        
        total_size = sum(r.file_size for r in self.download_results 
                        if r.success and r.file_size)
        
        return {
            'total_records': len(self.downloaded_ids),
            'successful_downloads': successful_downloads,
            'failed_downloads': failed_downloads,
            'total_size_mb': round(total_size / (1024 * 1024), 2) if total_size else 0,
            'storage_file': str(self.jsonl_path)
        }
    
    async def save_session(self, session: ScrapingSession, 
                          session_file: Optional[str] = None) -> None:
        """Save scraping session data."""
        if not session_file:
            session_file = self.jsonl_path.parent / f"session_{session.session_id}.json"
        
        try:
            session_data = session.dict()
            
            async with aiofiles.open(session_file, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(session_data, 
                                          default=str, 
                                          indent=2, 
                                          ensure_ascii=False))
            
            logger.info(f"Session data saved to {session_file}")
            
        except Exception as e:
            logger.error(f"Error saving session data: {e}")
    
    async def export_articles_metadata(self, articles: List[ArxivArticle], 
                                     export_file: str) -> None:
        """Export articles metadata to JSON file."""
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            articles_data = [article.dict() for article in articles]
            
            async with aiofiles.open(export_path, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(articles_data, 
                                          default=str, 
                                          indent=2, 
                                          ensure_ascii=False))
            
            logger.success(f"Exported {len(articles)} articles metadata to {export_file}")
            
        except Exception as e:
            logger.error(f"Error exporting articles metadata: {e}")
    
    def cleanup_old_files(self, download_dir: str, days_old: int = 30) -> None:
        """Clean up old downloaded files."""
        try:
            download_path = Path(download_dir)
            if not download_path.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
            cleaned_count = 0
            
            for file_path in download_path.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old files (>{days_old} days)")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
