"""Enhanced utility functions for the ArXiv scraper."""

import os
import asyncio
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import ArxivArticle
from utils.logger import logger


class ValidationUtils:
    """Utility class for validation operations."""
    
    @staticmethod
    def validate_arxiv_id(arxiv_id: str) -> bool:
        """Validate ArXiv ID format (both old and new styles)."""
        if not arxiv_id:
            return False

        # Strip common URL prefixes
        if arxiv_id.startswith("http"):
            arxiv_id = arxiv_id.rsplit('/', 1)[-1]

        # Accept IDs like "1234.56789" or "math-ph/0123456"
        if '.' in arxiv_id or '/' in arxiv_id:
            return True

        return False
    
    @staticmethod
    def validate_category(category: str) -> bool:
        """Validate ArXiv category format."""
        if not category:
            return False
        return '.' in category and len(category.split('.')) == 2
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file system usage."""
        # Remove/replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename.strip()


class FileUtils:
    """Utility class for file operations."""
    
    @staticmethod
    def ensure_directory(path: str) -> Path:
        """Ensure directory exists, create if necessary."""
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = 'md5') -> Optional[str]:
        """Calculate file hash."""
        try:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    @staticmethod
    def get_directory_size(path: str) -> int:
        """Get total size of directory in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error calculating directory size for {path}: {e}")
        return total_size
    
    @staticmethod
    def clean_old_files(directory: str, days_old: int = 7) -> int:
        """Clean files older than specified days."""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return 0
            
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
            cleaned_count = 0
            
            for file_path in dir_path.rglob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")
            return 0


class CategoryUtils:
    """Utility class for ArXiv category operations."""
    
    CATEGORY_DESCRIPTIONS = {
        # Mathematics
        'math.AG': 'Algebraic Geometry',
        'math.AT': 'Algebraic Topology',
        'math.AP': 'Analysis of PDEs',
        'math.CT': 'Category Theory',
        'math.CA': 'Classical Analysis and ODEs',
        'math.CO': 'Combinatorics',
        'math.AC': 'Commutative Algebra',
        'math.CV': 'Complex Variables',
        'math.DG': 'Differential Geometry',
        'math.DS': 'Dynamical Systems',
        'math.FA': 'Functional Analysis',
        'math.GM': 'General Mathematics',
        'math.GN': 'General Topology',
        'math.GT': 'Geometric Topology',
        'math.GR': 'Group Theory',
        'math.HO': 'History and Overview',
        'math.IT': 'Information Theory',
        'math.KT': 'K-Theory and Homology',
        'math.LO': 'Logic',
        'math.MP': 'Mathematical Physics',
        'math.MG': 'Metric Geometry',
        'math.NT': 'Number Theory',
        'math.NA': 'Numerical Analysis',
        'math.OA': 'Operator Algebras',
        'math.OC': 'Optimization and Control',
        'math.PR': 'Probability',
        'math.QA': 'Quantum Algebra',
        'math.RT': 'Representation Theory',
        'math.RA': 'Rings and Algebras',
        'math.SP': 'Spectral Theory',
        'math.ST': 'Statistics Theory',
        'math.SG': 'Symplectic Geometry',
        
        # Computer Science
        'cs.AI': 'Artificial Intelligence',
        'cs.CL': 'Computation and Language',
        'cs.CC': 'Computational Complexity',
        'cs.CE': 'Computational Engineering, Finance, and Science',
        'cs.CG': 'Computational Geometry',
        'cs.GT': 'Computer Science and Game Theory',
        'cs.CV': 'Computer Vision and Pattern Recognition',
        'cs.CY': 'Computers and Society',
        'cs.CR': 'Cryptography and Security',
        'cs.DS': 'Data Structures and Algorithms',
        'cs.DB': 'Databases',
        'cs.DL': 'Digital Libraries',
        'cs.DM': 'Discrete Mathematics',
        'cs.DC': 'Distributed, Parallel, and Cluster Computing',
        'cs.ET': 'Emerging Technologies',
        'cs.FL': 'Formal Languages and Automata Theory',
        'cs.GL': 'General Literature',
        'cs.GR': 'Graphics',
        'cs.AR': 'Hardware Architecture',
        'cs.HC': 'Human-Computer Interaction',
        'cs.IR': 'Information Retrieval',
        'cs.IT': 'Information Theory',
        'cs.LG': 'Machine Learning',
        'cs.LO': 'Logic in Computer Science',
        'cs.MS': 'Mathematical Software',
        'cs.MA': 'Multiagent Systems',
        'cs.MM': 'Multimedia',
        'cs.NI': 'Networking and Internet Architecture',
        'cs.NE': 'Neural and Evolutionary Computing',
        'cs.NA': 'Numerical Analysis',
        'cs.OS': 'Operating Systems',
        'cs.OH': 'Other Computer Science',
        'cs.PF': 'Performance',
        'cs.PL': 'Programming Languages',
        'cs.RO': 'Robotics',
        'cs.SI': 'Social and Information Networks',
        'cs.SE': 'Software Engineering',
        'cs.SD': 'Sound',
        'cs.SC': 'Symbolic Computation',
        'cs.SY': 'Systems and Control'
    }
    
    @classmethod
    def get_category_description(cls, category: str) -> str:
        """Get human-readable description for a category."""
        return cls.CATEGORY_DESCRIPTIONS.get(category, category)
    
    @classmethod
    def get_field_from_category(cls, category: str) -> str:
        """Extract field name from category."""
        if '.' in category:
            return category.split('.')[0]
        return category
    
    @classmethod
    def group_categories_by_field(cls, categories: List[str]) -> Dict[str, List[str]]:
        """Group categories by their field."""
        grouped = {}
        for category in categories:
            field = cls.get_field_from_category(category)
            if field not in grouped:
                grouped[field] = []
            grouped[field].append(category)
        return grouped


class StatsUtils:
    """Utility class for statistics calculations."""
    
    @staticmethod
    def calculate_download_stats(results: List[Any]) -> Dict[str, Any]:
        """Calculate download statistics."""
        if not results:
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'total_size_mb': 0.0,
                'avg_file_size_mb': 0.0
            }
        
        successful = sum(1 for r in results if hasattr(r, 'success') and r.success)
        failed = len(results) - successful
        
        total_size = sum(getattr(r, 'file_size', 0) for r in results 
                        if hasattr(r, 'success') and r.success and hasattr(r, 'file_size'))
        
        return {
            'total': len(results),
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / len(results)) * 100,
            'total_size_mb': total_size / (1024 * 1024),
            'avg_file_size_mb': (total_size / successful / (1024 * 1024)) if successful > 0 else 0
        }
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"


# Utility instances for easy access
validation = ValidationUtils()
file_utils = FileUtils()
category_utils = CategoryUtils()
stats_utils = StatsUtils()
