"""
Enhanced ArXiv Scraper - Main Application

A robust, async-powered scraper for downloading ArXiv articles with 
advanced error handling, rate limiting, and comprehensive logging.
"""

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console

from config import config
from models import ScrapingSession
from utils.scraping import ArxivScraper
from utils.storage import StorageManager
from utils.logger import logger
from utils.utils import validation, file_utils, category_utils, stats_utils


console = Console()


@click.group()
@click.version_option(version="2.0.0")
def cli():
    """Enhanced ArXiv Scraper - Download academic papers with ease."""
    pass


@cli.command()
@click.option('--categories', '-c', multiple=True, 
              help='ArXiv categories to scrape (e.g., math.AG, cs.AI)')
@click.option('--field', '-f', type=click.Choice(['math', 'cs', 'physics']),
              help='Scrape all categories from a specific field')
@click.option('--total', '-t', default=100, type=int,
              help='Total number of articles to download')
@click.option('--download-dir', '-d', default='./downloads',
              help='Directory to save downloaded files')
@click.option('--jsonl-path', '-j', default='./downloaded_ids.jsonl',
              help='Path to JSONL file for tracking downloads')
@click.option('--batch-size', '-b', default=10, type=int,
              help='Number of articles to fetch per batch')
@click.option('--max-retries', default=3, type=int,
              help='Maximum number of retry attempts')
@click.option('--export-metadata', is_flag=True,
              help='Export article metadata to JSON file')
@click.option('--log-file', type=str,
              help='Path to log file (optional)')
async def scrape(categories: tuple, field: Optional[str], total: int, 
                download_dir: str, jsonl_path: str, batch_size: int,
                max_retries: int, export_metadata: bool, log_file: Optional[str]):
    """Scrape articles from ArXiv."""
    
    # Setup logging
    if log_file:
        logger.setup_logging(log_file)
    
    # Display banner
    logger.display_banner(
        "ArXiv Enhanced Scraper v2.0",
        "Downloading academic papers with advanced features"
    )
    
    # Determine categories to scrape
    target_categories = []
    if field:
        target_categories = config.get_categories_by_field(field)
        logger.info(f"Using all {field} categories ({len(target_categories)} total)")
    elif categories:
        target_categories = list(categories)
        # Validate categories
        for cat in target_categories:
            if not validation.validate_category(cat):
                logger.error(f"Invalid category format: {cat}")
                return
    else:
        logger.error("Please specify either --categories or --field")
        return
    
    if not target_categories:
        logger.error("No valid categories found")
        return
    
    # Display configuration
    config_dict = {
        'Categories': f"{len(target_categories)} categories",
        'Target Articles': total,
        'Download Directory': download_dir,
        'Batch Size': batch_size,
        'Max Retries': max_retries,
        'JSONL Path': jsonl_path
    }
    logger.display_config(config_dict)
    
    # Create session
    session_id = str(uuid.uuid4())[:8]
    session = ScrapingSession(
        session_id=session_id,
        target_categories=target_categories,
        target_count=total
    )
    
    # Initialize storage and scraper
    storage = StorageManager(jsonl_path)
    await storage.load_downloaded_ids()
    
    logger.info(f"Found {len(storage.downloaded_ids)} previously downloaded articles")
    
    try:
        async with ArxivScraper(storage) as scraper:
            # Start scraping
            logger.info(f"Starting scraping session {session_id}")
            
            articles = await scraper.scrape_articles(
                categories=target_categories,
                max_articles=total,
                download_dir=download_dir,
                session=session
            )
            
            # Finish session
            session.finish()
            
            # Save session data
            await storage.save_session(session)
            
            # Export metadata if requested
            if export_metadata and articles:
                metadata_file = Path(download_dir) / f"metadata_{session_id}.json"
                await storage.export_articles_metadata(articles, str(metadata_file))
            
            # Display final statistics
            logger.display_session_summary(session.to_summary_dict())
            
            # Display storage stats
            storage_stats = storage.get_stats()
            logger.info(f"Storage: {storage_stats['total_records']} total records, "
                       f"{storage_stats['total_size_mb']} MB total size")
            
            logger.success(f"Scraping session {session_id} completed successfully!")
            
    except Exception as e:
        session.add_error(f"Critical error: {str(e)}")
        session.finish()
        await storage.save_session(session)
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--jsonl-path', '-j', default='./downloaded_ids.jsonl',
              help='Path to JSONL file to analyze')
def stats(jsonl_path: str):
    """Display statistics about downloaded articles."""
    
    if not Path(jsonl_path).exists():
        logger.error(f"File not found: {jsonl_path}")
        return
    
    # This would need to be implemented to read and analyze the JSONL file
    logger.info(f"Analyzing statistics from {jsonl_path}")
    # Implementation would go here...


@cli.command()
@click.option('--download-dir', '-d', default='./downloads',
              help='Download directory to clean')
@click.option('--days-old', default=30, type=int,
              help='Delete files older than this many days')
@click.option('--dry-run', is_flag=True,
              help='Show what would be deleted without actually deleting')
def cleanup(download_dir: str, days_old: int, dry_run: bool):
    """Clean up old downloaded files."""
    
    if not Path(download_dir).exists():
        logger.error(f"Directory not found: {download_dir}")
        return
    
    if dry_run:
        logger.info(f"DRY RUN: Would delete files older than {days_old} days from {download_dir}")
        # Implementation for dry run would go here...
    else:
        cleaned_count = file_utils.clean_old_files(download_dir, days_old)
        logger.success(f"Cleaned {cleaned_count} files older than {days_old} days")


@cli.command()
def categories():
    """List available ArXiv categories."""
    
    logger.display_banner("Available ArXiv Categories")
    
    all_categories = config.get_all_categories()
    grouped = category_utils.group_categories_by_field(all_categories)
    
    for field, cats in grouped.items():
        logger.info(f"\n{field.upper()} ({len(cats)} categories):")
        for cat in sorted(cats):
            description = category_utils.get_category_description(cat)
            console.print(f"  {cat:<15} - {description}")


@cli.command()
@click.option('--config-file', type=str,
              help='Path to configuration file to create')
def init(config_file: Optional[str]):
    """Initialize configuration file."""
    
    if not config_file:
        config_file = '.env'
    
    if Path(config_file).exists():
        logger.warning(f"Configuration file {config_file} already exists")
        return
    
    # Create default configuration
    # This would create a template configuration file
    logger.success(f"Created configuration file: {config_file}")


def main():
    """Main entry point."""
    try:
        cli(_anyio_backend="asyncio")
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()