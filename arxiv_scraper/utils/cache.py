"""
Caching utilities for the ArXiv scraper.

This module provides a simple caching system for API responses and query results
to improve performance and reduce API load.
"""

import json
import hashlib
import asyncio
import pickle
from pathlib import Path
from typing import Any, Optional, Dict, Union, TypeVar
from datetime import datetime, timedelta
import aiofiles

from arxiv_scraper.utils.logger import logger

# Type variable for generic cache
T = TypeVar('T')


class Cache:
    """Simple file-based cache with TTL support."""
    
    def __init__(self, cache_dir: Path, ttl_days: int = 7):
        """Initialize the cache."""
        self.cache_dir = cache_dir
        self.ttl_days = ttl_days
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Create a hash of the key to use as filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[T]:
        """Get a value from the cache."""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            # Check if cache is expired
            mtime = cache_path.stat().st_mtime
            cache_time = datetime.fromtimestamp(mtime)
            if datetime.now() - cache_time > timedelta(days=self.ttl_days):
                logger.debug(f"Cache expired for key: {key}")
                await self.delete(key)
                return None
                
            async with aiofiles.open(cache_path, 'rb') as f:
                data = await f.read()
                return pickle.loads(data)
                
        except Exception as e:
            logger.debug(f"Cache error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any) -> bool:
        """Set a value in the cache."""
        cache_path = self._get_cache_path(key)
        
        try:
            async with self._lock:
                async with aiofiles.open(cache_path, 'wb') as f:
                    await f.write(pickle.dumps(value))
            return True
        except Exception as e:
            logger.debug(f"Error setting cache for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            try:
                async with self._lock:
                    cache_path.unlink()
                return True
            except Exception as e:
                logger.debug(f"Error deleting cache for key {key}: {e}")
        return False
    
    async def clear(self) -> int:
        """Clear all cached values."""
        count = 0
        async with self._lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                    count += 1
                except Exception:
                    pass
        return count
    
    async def clear_expired(self) -> int:
        """Clear only expired cache entries."""
        count = 0
        cutoff_time = datetime.now() - timedelta(days=self.ttl_days)
        
        async with self._lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    mtime = cache_file.stat().st_mtime
                    if datetime.fromtimestamp(mtime) < cutoff_time:
                        cache_file.unlink()
                        count += 1
                except Exception:
                    pass
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_files = 0
        total_size = 0
        oldest = datetime.now()
        newest = datetime(1970, 1, 1)
        
        for cache_file in self.cache_dir.glob("*.cache"):
            total_files += 1
            try:
                size = cache_file.stat().st_size
                total_size += size
                
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                oldest = min(oldest, mtime)
                newest = max(newest, mtime)
            except Exception:
                pass
        
        return {
            "total_entries": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
            "oldest_entry": oldest.isoformat() if total_files > 0 else None,
            "newest_entry": newest.isoformat() if total_files > 0 else None,
            "cache_dir": str(self.cache_dir),
            "ttl_days": self.ttl_days
        }
