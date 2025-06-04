"""Configuration management for the ArXiv scraper."""

import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ScraperConfig(BaseModel):
    """Configuration model for the ArXiv scraper."""
    
    # Download settings
    download_dir: str = Field(default_factory=lambda: os.getenv('DEFAULT_DOWNLOAD_DIR', './downloads'))
    jsonl_path: str = Field(default_factory=lambda: os.getenv('DEFAULT_JSONL_PATH', './downloaded_ids.jsonl'))
    total_articles: int = Field(default_factory=lambda: int(os.getenv('DEFAULT_TOTAL_ARTICLES', '100')))
    batch_size: int = Field(default_factory=lambda: int(os.getenv('DEFAULT_BATCH_SIZE', '10')))
    save_threshold: int = Field(default_factory=lambda: int(os.getenv('DEFAULT_SAVE_THRESHOLD', '50')))
    max_retries: int = Field(default_factory=lambda: int(os.getenv('DEFAULT_MAX_RETRIES', '3')))
    retry_delay: float = Field(default_factory=lambda: float(os.getenv('DEFAULT_RETRY_DELAY', '5.0')))
    
    # API settings
    api_base_url: str = Field(default_factory=lambda: os.getenv('ARXIV_API_BASE_URL', 'http://export.arxiv.org/api/query'))
    source_base_url: str = Field(default_factory=lambda: os.getenv('ARXIV_SOURCE_BASE_URL', 'https://arxiv.org/e-print'))
    rate_limit: float = Field(default_factory=lambda: float(os.getenv('API_RATE_LIMIT', '3.0')))
    
    # Logging
    log_level: str = Field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    log_format: str = Field(default_factory=lambda: os.getenv('LOG_FORMAT', 
                                                           '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # ArXiv categories
    math_categories: List[str] = Field(default_factory=lambda: [
        'math.RT', 'math.GN', 'math.HO', 'math.QA', 'math.CV', 'math.AP', 'math.IT',
        'math.GR', 'math.NA', 'math.SG', 'math.OC', 'math.CO', 'math.PR',
        'math.CT', 'math.RA', 'math.AG', 'math.KT', 'math.GT', 'math.GM', 'math.AC', 
        'math.MP', 'math.SP', 'math.MG', 'math.FA', 'math.LO', 'math.AT', 'math.NT', 
        'math.DS', 'math.CA', 'math.ST', 'math.DG', 'math.OA'
    ])
    
    cs_categories: List[str] = Field(default_factory=lambda: [
        'cs.AI', 'cs.CL', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.GT', 'cs.CV', 'cs.CY',
        'cs.CR', 'cs.DS', 'cs.DB', 'cs.DL', 'cs.DM', 'cs.DC', 'cs.ET', 'cs.FL',
        'cs.GL', 'cs.GR', 'cs.AR', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO',
        'cs.MS', 'cs.MA', 'cs.MM', 'cs.NI', 'cs.NE', 'cs.NA', 'cs.OS', 'cs.OH',
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
    
    def get_categories_by_field(self, field: str) -> List[str]:
        """Get categories by field name."""
        field_mapping = {
            'math': self.math_categories,
            'cs': self.cs_categories,
            'physics': self.physics_categories
        }
        return field_mapping.get(field.lower(), [])
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        return self.math_categories + self.cs_categories + self.physics_categories


# Global configuration instance
config = ScraperConfig()
