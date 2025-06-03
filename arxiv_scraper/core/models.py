"""
Data models for the ArXiv scraper.

This module contains Pydantic models for representing ArXiv articles, 
download results, and scraping sessions.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


class FileFormat(str, Enum):
    """File formats for downloaded articles."""
    
    SOURCE = "source"  # Source files (.tar.gz)
    PDF = "pdf"        # PDF document
    LATEX = "latex"    # LaTeX source
    HTML = "html"      # HTML version
    
    def get_extension(self) -> str:
        """Get the file extension for the format."""
        extensions = {
            FileFormat.SOURCE: ".tar.gz",
            FileFormat.PDF: ".pdf",
            FileFormat.LATEX: ".tex",
            FileFormat.HTML: ".html"
        }
        return extensions.get(self, ".unknown")


class Author(BaseModel):
    """Model for article author."""
    
    name: str = Field(
        ..., 
        description="Author's full name"
    )
    affiliation: Optional[str] = Field(
        None, 
        description="Author's affiliation/institution"
    )
    
    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate and normalize author name."""
        if not v or not v.strip():
            raise ValueError("Author name cannot be empty")
        return v.strip()
    
    def __str__(self) -> str:
        """String representation with affiliation if available."""
        if self.affiliation:
            return f"{self.name} ({self.affiliation})"
        return self.name


class ArxivArticle(BaseModel):
    """Model for an ArXiv article."""
    
    arxiv_id: str = Field(
        ..., 
        description="ArXiv ID of the article"
    )
    title: str = Field(
        ..., 
        description="Title of the article"
    )
    authors: List[Author] = Field(
        default_factory=list, 
        description="List of article authors"
    )
    abstract: Optional[str] = Field(
        None, 
        description="Abstract of the article"
    )
    categories: List[str] = Field(
        default_factory=list, 
        description="ArXiv categories"
    )
    primary_category: Optional[str] = Field(
        None, 
        description="Primary category"
    )
    published_date: Optional[datetime] = Field(
        None, 
        description="Publication date"
    )
    updated_date: Optional[datetime] = Field(
        None, 
        description="Last update date"
    )
    doi: Optional[str] = Field(
        None, 
        description="Digital Object Identifier"
    )
    journal_ref: Optional[str] = Field(
        None, 
        description="Journal reference"
    )
    link: Optional[str] = Field(
        None, 
        description="ArXiv link"
    )
    pdf_link: Optional[str] = Field(
        None, 
        description="PDF link"
    )
    source_link: Optional[str] = Field(
        None, 
        description="Source code link"
    )
    comment: Optional[str] = Field(
        None, 
        description="Author comment"
    )
    
    @field_validator('arxiv_id')
    def validate_arxiv_id(cls, v: str) -> str:
        """Validate ArXiv ID format and normalize it."""
        if not v:
            raise ValueError("ArXiv ID cannot be empty")
            
        # Remove any URL prefix if present
        if '/' in v:
            v = v.split('/')[-1]
            
        # Remove version suffix if present (e.g., v1, v2)
        if 'v' in v and v.rindex('v') > 0:
            try:
                v_index = v.rindex('v')
                # Only remove if what follows is a number
                if v[v_index+1:].isdigit():
                    v = v[:v_index]
            except ValueError:
                pass
                
        return v.strip()
    
    @field_validator('title')
    def clean_title(cls, v: Optional[str]) -> str:
        """Clean title by removing extra whitespace and newlines."""
        if not v:
            raise ValueError("Title cannot be empty")
        return v.replace('\n', ' ').replace('  ', ' ').strip()
    
    @field_validator('categories')
    def parse_categories(cls, v: Union[str, List]) -> List[str]:
        """Parse categories from various formats."""
        if isinstance(v, str):
            return [cat.strip() for cat in v.split() if cat.strip()]
        elif isinstance(v, list):
            return [str(cat).strip() for cat in v if str(cat).strip()]
        return []
    
    def get_download_filename(self, format: FileFormat = FileFormat.SOURCE) -> str:
        """Generate a standardized filename for this article."""
        extension = format.get_extension()
        return f"{self.arxiv_id}{extension}"
    
    def get_short_authors(self, max_authors: int = 3) -> List[str]:
        """Get shortened author list with 'et al.' if needed."""
        author_names = [author.name for author in self.authors]
        
        if len(author_names) <= max_authors:
            return author_names
        else:
            return author_names[:max_authors-1] + ['et al.']
    
    def get_citation_key(self) -> str:
        """Generate a citation key for BibTeX."""
        # Basic format: FirstAuthorLastName_Year_ShortTitle
        year = self.published_date.year if self.published_date else "XXXX"
        
        # Get first author's last name
        first_author = "Unknown"
        if self.authors:
            name_parts = self.authors[0].name.split()
            if name_parts:
                first_author = name_parts[-1]
        
        # Get short title (first word or two)
        if self.title:
            title_words = self.title.split()[:2]
            short_title = "".join([w[0].upper() + w[1:].lower() for w in title_words if w])
        else:
            short_title = "Article"
        
        return f"{first_author}_{year}_{short_title}"
    
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
    
    def to_bibtex(self) -> str:
        """Generate BibTeX entry for the article."""
        cite_key = self.get_citation_key()
        
        authors = " and ".join([author.name for author in self.authors])
        year = self.published_date.year if self.published_date else ""
        month = self.published_date.strftime("%b").lower() if self.published_date else ""
        
        return (
            f"@article{{{cite_key},\n"
            f"  author = {{{authors}}},\n"
            f"  title = {{{self.title}}},\n"
            f"  journal = {{arXiv preprint}},\n"
            f"  year = {{{year}}},\n"
            f"  month = {{{month}}},\n"
            f"  archivePrefix = {{arXiv}},\n"
            f"  primaryClass = {{{self.primary_category or ''}}},\n"
            f"  eprint = {{{self.arxiv_id}}},\n"
            f"  url = {{{self.link or ''}}},\n"
            f"  abstract = {{{self.abstract or ''}}},\n"
            f"  doi = {{{self.doi or ''}}},\n"
            f"}}"
        )


class DownloadResult(BaseModel):
    """Model for download operation result."""
    
    arxiv_id: str
    success: bool
    file_path: Optional[Union[str, Path]] = None
    file_size: Optional[int] = None
    file_format: FileFormat = FileFormat.SOURCE
    error_message: Optional[str] = None
    download_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation showing success or failure."""
        if self.success:
            file_path = Path(self.file_path) if self.file_path else None
            filename = file_path.name if file_path else "unknown"
            size = f"{self.file_size / 1024:.1f} KB" if self.file_size else "unknown size"
            return f"✓ {self.arxiv_id} → {filename} ({size})"
        else:
            return f"✗ {self.arxiv_id}: {self.error_message or 'unknown error'}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result = {
            'arxiv_id': self.arxiv_id,
            'success': self.success,
            'file_format': self.file_format.value,
            'timestamp': self.timestamp.isoformat(),
        }
        
        if self.file_path:
            result['file_path'] = str(self.file_path)
        
        if self.file_size:
            result['file_size'] = self.file_size
            
        if self.error_message:
            result['error_message'] = self.error_message
            
        if self.download_time:
            result['download_time'] = self.download_time
            
        if self.metadata:
            result['metadata'] = self.metadata
            
        return result


class ScrapingSession(BaseModel):
    """Model for a scraping session."""
    
    session_id: str = Field(
        ..., 
        description="Unique session identifier"
    )
    start_time: datetime = Field(
        default_factory=datetime.now,
        description="Session start time"
    )
    end_time: Optional[datetime] = Field(
        None,
        description="Session end time"
    )
    target_categories: List[str] = Field(
        default_factory=list,
        description="Categories to scrape"
    )
    target_count: int = Field(
        0,
        description="Target number of articles to download"
    )
    articles_found: int = Field(
        0,
        description="Number of articles found"
    )
    articles_downloaded: int = Field(
        0,
        description="Number of articles successfully downloaded"
    )
    articles_skipped: int = Field(
        0,
        description="Number of articles skipped"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages"
    )
    download_formats: Set[FileFormat] = Field(
        default_factory=lambda: {FileFormat.SOURCE},
        description="File formats to download"
    )
    
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
    
    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.end_time is not None
    
    def add_error(self, error: str) -> None:
        """Add an error to the session."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")
    
    def finish(self) -> None:
        """Mark session as finished."""
        if not self.end_time:
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
            'errors': len(self.errors),
            'formats': [fmt.value for fmt in self.download_formats]
        }
