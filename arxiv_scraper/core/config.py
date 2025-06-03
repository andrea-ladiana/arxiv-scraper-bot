"""
Configuration management for the ArXiv scraper.

This module provides a centralized configuration system using Pydantic models
and environment variables through python-dotenv.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default locations
DEFAULT_CONFIG_DIR = Path.home() / ".arxiv-scraper"
DEFAULT_DOWNLOAD_DIR = DEFAULT_CONFIG_DIR / "downloads"
DEFAULT_CACHE_DIR = DEFAULT_CONFIG_DIR / "cache"
DEFAULT_JSONL_PATH = DEFAULT_CONFIG_DIR / "downloaded_ids.jsonl"


class ApiSettings(BaseModel):
    """API-related configuration settings."""
    
    api_base_url: str = Field(
        default_factory=lambda: os.getenv('ARXIV_API_BASE_URL', 'http://export.arxiv.org/api/query')
    )
    source_base_url: str = Field(
        default_factory=lambda: os.getenv('ARXIV_SOURCE_BASE_URL', 'https://arxiv.org/e-print')
    )
    pdf_base_url: str = Field(
        default_factory=lambda: os.getenv('ARXIV_PDF_BASE_URL', 'https://arxiv.org/pdf')
    )
    rate_limit: float = Field(
        default_factory=lambda: float(os.getenv('API_RATE_LIMIT', '3.0'))
    )
    timeout: float = Field(
        default_factory=lambda: float(os.getenv('API_TIMEOUT', '30.0'))
    )
    max_connections: int = Field(
        default_factory=lambda: int(os.getenv('API_MAX_CONNECTIONS', '10'))
    )
    user_agent: str = Field(
        default_factory=lambda: os.getenv(
            'API_USER_AGENT', 
            'ArXiv-Scraper/3.0 (Educational Purpose; https://github.com/yourusername/arxiv-scraper)'
        )
    )


class DownloadSettings(BaseModel):
    """Download-related configuration settings."""
    
    download_dir: Path = Field(
        default_factory=lambda: Path(os.getenv('DEFAULT_DOWNLOAD_DIR', str(DEFAULT_DOWNLOAD_DIR)))
    )
    jsonl_path: Path = Field(
        default_factory=lambda: Path(os.getenv('DEFAULT_JSONL_PATH', str(DEFAULT_JSONL_PATH)))
    )
    cache_dir: Path = Field(
        default_factory=lambda: Path(os.getenv('DEFAULT_CACHE_DIR', str(DEFAULT_CACHE_DIR)))
    )
    total_articles: int = Field(
        default_factory=lambda: int(os.getenv('DEFAULT_TOTAL_ARTICLES', '100'))
    )
    batch_size: int = Field(
        default_factory=lambda: int(os.getenv('DEFAULT_BATCH_SIZE', '10'))
    )
    save_threshold: int = Field(
        default_factory=lambda: int(os.getenv('DEFAULT_SAVE_THRESHOLD', '50'))
    )
    max_retries: int = Field(
        default_factory=lambda: int(os.getenv('DEFAULT_MAX_RETRIES', '3'))
    )
    retry_delay: float = Field(
        default_factory=lambda: float(os.getenv('DEFAULT_RETRY_DELAY', '5.0'))
    )
    max_concurrent_downloads: int = Field(
        default_factory=lambda: int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '5'))
    )
    prefer_pdf: bool = Field(
        default_factory=lambda: os.getenv('PREFER_PDF', 'false').lower() == 'true'
    )
    download_latest: bool = Field(
        default_factory=lambda: os.getenv('DOWNLOAD_LATEST', 'true').lower() == 'true'
    )
    
    @field_validator('download_dir', 'cache_dir', mode='after')
    def create_dirs(cls, v: Path) -> Path:
        """Create directories if they don't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v


class LoggingSettings(BaseModel):
    """Logging-related configuration settings."""
    
    log_level: str = Field(
        default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO')
    )
    log_format: str = Field(
        default_factory=lambda: os.getenv(
            'LOG_FORMAT', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    log_file: Optional[Path] = Field(
        default_factory=lambda: Path(os.getenv('LOG_FILE')) if os.getenv('LOG_FILE') else None
    )
    log_to_console: bool = Field(
        default_factory=lambda: os.getenv('LOG_TO_CONSOLE', 'true').lower() == 'true'
    )
    log_to_file: bool = Field(
        default_factory=lambda: os.getenv('LOG_TO_FILE', 'false').lower() == 'true'
    )
    rich_traceback: bool = Field(
        default_factory=lambda: os.getenv('RICH_TRACEBACK', 'true').lower() == 'true'
    )


class ArxivCategories(BaseModel):
    """ArXiv category lists by field."""
    
    math_categories: List[str] = Field(default_factory=lambda: [
        'math.AG', 'math.AT', 'math.AP', 'math.AC', 'math.CT', 'math.CA', 'math.CO',
        'math.CV', 'math.DG', 'math.DS', 'math.FA', 'math.GM', 'math.GN', 'math.GT',
        'math.GR', 'math.HO', 'math.IT', 'math.KT', 'math.LO', 'math.MP', 'math.MG',
        'math.NT', 'math.NA', 'math.OA', 'math.OC', 'math.PR', 'math.QA', 'math.RT',
        'math.RA', 'math.SP', 'math.ST', 'math.SG', 'math-ph'
    ])
    
    cs_categories: List[str] = Field(default_factory=lambda: [
        'cs.AI', 'cs.AR', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.CL', 'cs.CR', 'cs.CV',
        'cs.CY', 'cs.DB', 'cs.DC', 'cs.DL', 'cs.DM', 'cs.DS', 'cs.ET', 'cs.FL',
        'cs.GL', 'cs.GR', 'cs.GT', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO',
        'cs.MA', 'cs.MS', 'cs.MM', 'cs.NI', 'cs.NE', 'cs.NA', 'cs.OS', 'cs.OH',
        'cs.PF', 'cs.PL', 'cs.RO', 'cs.SI', 'cs.SE', 'cs.SD', 'cs.SC', 'cs.SY'
    ])
    
    physics_categories: List[str] = Field(default_factory=lambda: [
        'physics.acc-ph', 'physics.ao-ph', 'physics.app-ph', 'physics.atm-clus',
        'physics.atom-ph', 'physics.bio-ph', 'physics.chem-ph', 'physics.class-ph',
        'physics.comp-ph', 'physics.data-an', 'physics.flu-dyn', 'physics.gen-ph',
        'physics.geo-ph', 'physics.hist-ph', 'physics.ins-det', 'physics.med-ph',
        'physics.optics', 'physics.ed-ph', 'physics.soc-ph', 'physics.plasm-ph',
        'physics.pop-ph', 'physics.space-ph'
    ])
    
    # Add more fields as needed
    biology_categories: List[str] = Field(default_factory=lambda: [
        'q-bio.BM', 'q-bio.CB', 'q-bio.GN', 'q-bio.MN', 'q-bio.NC', 'q-bio.OT',
        'q-bio.PE', 'q-bio.QM', 'q-bio.SC', 'q-bio.TO'
    ])
    
    # Category descriptions
    _category_descriptions: Dict[str, str] = {
        'math.AG': 'Algebraic Geometry',
        'math.AT': 'Algebraic Topology',
        'cs.AI': 'Artificial Intelligence',
        'cs.LG': 'Machine Learning',
        'physics.optics': 'Optics',
        # Add more descriptions as needed
    }
    
    def get_categories_by_field(self, field: str) -> List[str]:
        """Get categories by field name."""
        field_mapping = {
            'math': self.math_categories,
            'cs': self.cs_categories,
            'physics': self.physics_categories,
            'biology': self.biology_categories,
        }
        return field_mapping.get(field.lower(), [])
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        return (self.math_categories + self.cs_categories +
                self.physics_categories + self.biology_categories)
    
    def get_category_description(self, category: str) -> str:
        """Get the description for a category."""
        return self._category_descriptions.get(category, f"Category: {category}")
    
    def group_categories_by_field(self) -> Dict[str, List[str]]:
        """Group categories by field."""
        return {
            'math': self.math_categories,
            'cs': self.cs_categories,
            'physics': self.physics_categories,
            'biology': self.biology_categories,
        }


class ScraperConfig(BaseModel):
    """Main configuration model for the ArXiv scraper."""
    
    # Sub-configurations
    api: ApiSettings = Field(default_factory=ApiSettings)
    download: DownloadSettings = Field(default_factory=DownloadSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    categories: ArxivCategories = Field(default_factory=ArxivCategories)
    
    # Other settings
    version: str = "3.0.0"
    enable_caching: bool = Field(
        default_factory=lambda: os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
    )
    cache_expiry_days: int = Field(
        default_factory=lambda: int(os.getenv('CACHE_EXPIRY_DAYS', '7'))
    )
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "ScraperConfig":
        """Load configuration from a file."""
        # Implementation would depend on file format (.env, .json, .yaml)
        # For now, just return default config
        return cls()
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to a file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=2))
    
    def get_categories_by_field(self, field: str) -> List[str]:
        """Get categories by field name."""
        return self.categories.get_categories_by_field(field)
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        return self.categories.get_all_categories()
    
    def get_category_description(self, category: str) -> str:
        """Get the description for a category."""
        return self.categories.get_category_description(category)


# Global configuration instance
config = ScraperConfig()
