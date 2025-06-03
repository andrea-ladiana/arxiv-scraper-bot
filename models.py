"""Data models for the ArXiv scraper."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import time


class Author(BaseModel):
    """Model for article author."""
    name: str
    affiliation: Optional[str] = None


class ArxivArticle(BaseModel):
    """Model for an ArXiv article."""
    
    arxiv_id: str = Field(..., description="ArXiv ID of the article")
    title: str = Field(..., description="Title of the article")
    authors: List[Author] = Field(default_factory=list, description="List of authors")
    abstract: Optional[str] = Field(None, description="Abstract of the article")
    categories: List[str] = Field(default_factory=list, description="ArXiv categories")
    primary_category: Optional[str] = Field(None, description="Primary category")
    published_date: Optional[datetime] = Field(None, description="Publication date")
    updated_date: Optional[datetime] = Field(None, description="Last update date")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    journal_ref: Optional[str] = Field(None, description="Journal reference")
    link: Optional[str] = Field(None, description="ArXiv link")
    pdf_link: Optional[str] = Field(None, description="PDF link")
    source_link: Optional[str] = Field(None, description="Source code link")
    comment: Optional[str] = Field(None, description="Author comment")
    
    @validator('arxiv_id')
    def validate_arxiv_id(cls, v):
        """Validate ArXiv ID format."""
        if not v:
            raise ValueError("ArXiv ID cannot be empty")
        # Remove any URL prefix if present
        if '/' in v:
            v = v.split('/')[-1]
        return v
    
    @validator('title')
    def clean_title(cls, v):
        """Clean title by removing extra whitespace and newlines."""
        if v:
            return v.replace('\n', ' ').replace('  ', ' ').strip()
        return v
    
    @validator('categories', pre=True)
    def parse_categories(cls, v):
        """Parse categories from various formats."""
        if isinstance(v, str):
            return [cat.strip() for cat in v.split() if cat.strip()]
        elif isinstance(v, list):
            return [str(cat).strip() for cat in v if str(cat).strip()]
        return []
    
    def get_short_authors(self, max_authors: int = 5) -> List[str]:
        """Get shortened author list with 'et al.' if needed."""
        author_names = [author.name if isinstance(author, Author) else str(author) 
                       for author in self.authors]
        
        if len(author_names) <= max_authors:
            return author_names
        else:
            return author_names[:max_authors-1] + ['et al.']
    
    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display purposes."""
        return {
            'arxiv_id': self.arxiv_id,
            'title': self.title,
            'authors': self.get_short_authors(),
            'categories': self.categories,
            'published_date': self.published_date.strftime('%Y-%m-%d') if self.published_date else None,
            'link': self.link
        }


class DownloadResult(BaseModel):
    """Model for download operation result."""
    
    arxiv_id: str
    success: bool
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    download_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        if self.success:
            return f"✓ {self.arxiv_id} -> {self.file_path} ({self.file_size} bytes)"
        else:
            return f"✗ {self.arxiv_id}: {self.error_message}"


class ScrapingSession(BaseModel):
    """Model for a scraping session."""
    
    session_id: str = Field(..., description="Unique session identifier")
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    target_categories: List[str] = Field(default_factory=list)
    target_count: int = 0
    articles_found: int = 0
    articles_downloaded: int = 0
    articles_skipped: int = 0
    errors: List[str] = Field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """Get session duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.articles_found == 0:
            return 0.0
        return (self.articles_downloaded / self.articles_found) * 100
    
    def add_error(self, error: str) -> None:
        """Add an error to the session."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")
    
    def finish(self) -> None:
        """Mark session as finished."""
        self.end_time = datetime.now()
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary."""
        return {
            'session_id': self.session_id,
            'duration': self.duration,
            'categories': self.target_categories,
            'target_count': self.target_count,
            'found': self.articles_found,
            'downloaded': self.articles_downloaded,
            'skipped': self.articles_skipped,
            'success_rate': f"{self.success_rate:.1f}%",
            'errors': len(self.errors)
        }
