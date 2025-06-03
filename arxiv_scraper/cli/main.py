"""
Command-line interface for the ArXiv scraper.

This module provides the CLI commands and entry points for the scraper,
including commands for scraping, listing categories, and viewing statistics.
"""

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple, Dict, Any

import click
from rich.progress import Progress
from rich.console import Console

from arxiv_scraper.core.config import config
from arxiv_scraper.core.models import ScrapingSession, FileFormat
from arxiv_scraper.core.scraping import ArxivScraper
from arxiv_scraper.core.storage import StorageManager
from arxiv_scraper.utils.logger import logger


CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
    'auto_envvar_prefix': 'ARXIV_SCRAPER'
}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=config.version)
def cli():
    """ArXiv Enhanced Scraper - Download academic papers with advanced features."""
    pass


@cli.command()
@click.option('--categories', '-c', multiple=True, 
              help='ArXiv categories to scrape (e.g., math.AG, cs.AI)')
@click.option('--field', '-f', type=click.Choice(['math', 'cs', 'physics', 'biology']),
              help='Scrape all categories from a specific field')
@click.option('--total', '-t', default=config.download.total_articles, type=int,
              help='Total number of articles to download')
@click.option('--download-dir', '-d', default=str(config.download.download_dir),
              help='Directory to save downloaded files')
@click.option('--jsonl-path', '-j', default=str(config.download.jsonl_path),
              help='Path to JSONL file for tracking downloads')
@click.option('--batch-size', '-b', default=config.download.batch_size, type=int,
              help='Number of articles to fetch per batch')
@click.option('--max-retries', default=config.download.max_retries, type=int,
              help='Maximum number of retry attempts')
@click.option('--max-concurrent', default=config.download.max_concurrent_downloads, type=int,
              help='Maximum number of concurrent downloads')
@click.option('--export-metadata', is_flag=True,
              help='Export article metadata to JSON file')
@click.option('--export-bibtex', is_flag=True,
              help='Export article metadata to BibTeX file')
@click.option('--format', type=click.Choice(['source', 'pdf', 'both']), default='source',
              help='Download format (source = tar.gz, pdf = PDF file, both = both formats)')
@click.option('--log-file', type=str,
              help='Path to log file (optional)')
@click.option('--quiet', '-q', is_flag=True,
              help='Suppress informational output')
@click.option('--debug', is_flag=True,
              help='Enable debug logging')
def scrape(categories: Tuple[str], field: Optional[str], total: int, 
               download_dir: str, jsonl_path: str, batch_size: int,
               max_retries: int, max_concurrent: int, export_metadata: bool,
               export_bibtex: bool, format: str, log_file: Optional[str],
               quiet: bool, debug: bool):
    """Scrape articles from ArXiv."""
    import asyncio
    asyncio.run(_scrape(categories, field, total, download_dir, jsonl_path, batch_size,
               max_retries, max_concurrent, export_metadata, export_bibtex, format,
               log_file, quiet, debug))

async def _scrape(categories: Tuple[str], field: Optional[str], total: int, 
               download_dir: str, jsonl_path: str, batch_size: int,
               max_retries: int, max_concurrent: int, export_metadata: bool,
               export_bibtex: bool, format: str, log_file: Optional[str],
               quiet: bool, debug: bool):
    """Scrape articles from ArXiv."""
    
    # Override config settings
    config.download.total_articles = total
    config.download.batch_size = batch_size
    config.download.max_retries = max_retries
    config.download.max_concurrent_downloads = max_concurrent
    config.download.download_dir = Path(download_dir)
    config.download.jsonl_path = Path(jsonl_path)
    
    # Set up logging
    if debug:
        config.logging.log_level = "DEBUG"
    elif quiet:
        config.logging.log_level = "WARNING"
    
    if log_file:
        config.logging.log_to_file = True
        config.logging.log_file = Path(log_file)
    
    logger.setup_logging()
    
    # Display banner
    if not quiet:
        logger.display_banner(
            f"ArXiv Enhanced Scraper v{config.version}",
            "Downloading academic papers with advanced features"
        )
    
    # Determine categories to scrape
    target_categories = []
    if field:
        target_categories = config.get_categories_by_field(field)
        logger.info(f"Using all {field} categories ({len(target_categories)} total)")
    elif categories:
        for cat in categories:
            # Validate category
            if '.' not in cat:
                logger.error(f"Invalid category format: {cat}")
                continue
            target_categories.append(cat)
    else:
        logger.error("Please specify either --categories or --field")
        sys.exit(1)
    
    if not target_categories:
        logger.error("No valid categories found")
        sys.exit(1)
    
    # Determine download formats
    download_formats = set()
    if format == 'source' or format == 'both':
        download_formats.add(FileFormat.SOURCE)
    if format == 'pdf' or format == 'both':
        download_formats.add(FileFormat.PDF)
    
    # Display configuration
    if not quiet:
        config_dict = {
            'Categories': f"{len(target_categories)} categories",
            'Target Articles': total,
            'Download Directory': download_dir,
            'Batch Size': batch_size,
            'Max Retries': max_retries,
            'Max Concurrent Downloads': max_concurrent,
            'JSONL Path': jsonl_path,
            'Formats': ", ".join([f.value for f in download_formats])
        }
        logger.display_config(config_dict)
    
    # Create session
    session_id = str(uuid.uuid4())[:8]
    session = ScrapingSession(
        session_id=session_id,
        target_categories=target_categories,
        target_count=total,
        download_formats=download_formats
    )
    
    # Initialize storage
    storage = StorageManager(Path(jsonl_path))
    await storage.load_downloaded_ids()
    
    logger.info(f"Found {len(storage.downloaded_ids)} previously downloaded articles")
    
    # Create progress for overall scraping
    progress = None
    if not quiet:
        progress = logger.create_progress_bar()
        
    try:
        # Start scraping
        logger.info(f"Starting scraping session {session_id}")
        
        async with ArxivScraper() as scraper:
            download_path = Path(download_dir)
            download_path.mkdir(parents=True, exist_ok=True)
            
            if progress:
                with progress:
                    # Add a task for overall scraping progress
                    scraper.progress = progress
                    
                    articles = await scraper.scrape_articles(
                        categories=target_categories,
                        max_articles=total,
                        download_dir=download_path,
                        session=session,
                        downloaded_ids=storage.downloaded_ids,
                        progress=progress
                    )
            else:
                articles = await scraper.scrape_articles(
                    categories=target_categories,
                    max_articles=total,
                    download_dir=download_path,
                    session=session,
                    downloaded_ids=storage.downloaded_ids
                )
            
            # Finish session
            session.finish()
            
            # Save session data
            await storage.save_session(session)
            
            # Export metadata if requested
            if export_metadata and articles:
                metadata_file = Path(download_dir) / f"metadata_{session_id}.json"
                await storage.export_articles_metadata(
                    articles, metadata_file, format='json'
                )
                logger.success(f"Exported JSON metadata to {metadata_file}")
            
            # Export BibTeX if requested
            if export_bibtex and articles:
                bibtex_file = Path(download_dir) / f"bibtex_{session_id}.bib"
                await storage.export_articles_metadata(
                    articles, bibtex_file, format='bibtex'
                )
                logger.success(f"Exported BibTeX citations to {bibtex_file}")
            
            # Display final statistics
            if not quiet:
                logger.display_session_summary(session.to_summary_dict())
                
                # Display storage stats
                storage_stats = storage.get_stats()
                logger.display_storage_stats(storage_stats)
            
            logger.success(f"Scraping session {session_id} completed successfully!")
            
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
        session.add_error("Interrupted by user")
        session.finish()
        await storage.save_session(session)
        sys.exit(130)  # Standard exit code for SIGINT
        
    except Exception as e:
        session.add_error(f"Critical error: {str(e)}")
        session.finish()
        await storage.save_session(session)
        logger.error(f"Scraping failed: {e}")
        if debug:
            logger.error("Debug traceback:", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option('--jsonl-path', '-j', default=str(config.download.jsonl_path),
              help='Path to JSONL file to analyze')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def stats(jsonl_path: str, format: str):
    """Display statistics about downloaded articles."""
    
    path = Path(jsonl_path)
    if not path.exists():
        logger.error(f"File not found: {jsonl_path}")
        sys.exit(1)
    
    logger.info(f"Analyzing statistics from {jsonl_path}")
    
    # Create storage manager and load data
    async def run():
        storage = StorageManager(path)
        await storage.load_downloaded_ids()
        
        stats = storage.get_stats()
        logger.display_storage_stats(stats)
    
    asyncio.run(run())


@cli.command()
@click.option('--download-dir', '-d', default=str(config.download.download_dir),
              help='Download directory to clean')
@click.option('--days-old', default=30, type=int,
              help='Delete files older than this many days')
@click.option('--dry-run', is_flag=True,
              help='Show what would be deleted without actually deleting')
def cleanup(download_dir: str, days_old: int, dry_run: bool):
    """Clean up old downloaded files."""
    
    dir_path = Path(download_dir)
    if not dir_path.exists():
        logger.error(f"Directory not found: {download_dir}")
        sys.exit(1)
    
    if dry_run:
        logger.info(f"DRY RUN: Would delete files older than {days_old} days from {download_dir}")
        
        # Count files that would be deleted
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
        would_delete_count = 0
        would_delete_size = 0
        
        for file_path in dir_path.glob('**/*'):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                would_delete_count += 1
                would_delete_size += file_path.stat().st_size
        
        if would_delete_count > 0:
            size_mb = round(would_delete_size / (1024 * 1024), 2)
            logger.info(f"Would delete {would_delete_count} files ({size_mb} MB)")
        else:
            logger.info("No files would be deleted")
    else:
        # Actually do the cleanup
        storage = StorageManager()
        cleaned_count = storage.cleanup_old_files(dir_path, days_old)
        logger.success(f"Cleaned {cleaned_count} files older than {days_old} days")


@cli.command(name="categories")
@click.option('--field', '-f', 
              help='Filter categories by field (math, cs, physics, biology)')
def list_categories(field: Optional[str]):
    """List available ArXiv categories."""
    
    logger.display_banner("Available ArXiv Categories")
    
    all_categories = {}
    
    if field:
        categories = config.get_categories_by_field(field.lower())
        all_categories[field] = categories
    else:
        all_categories = config.categories.group_categories_by_field()
    
    for field_name, cats in all_categories.items():
        logger.info(f"\n{field_name.upper()} ({len(cats)} categories):")
        
        # Create a table for better display
        console = Console()
        for cat in sorted(cats):
            description = config.categories.get_category_description(cat)
            console.print(f"  {cat:<15} - {description}")


@cli.command(name="info")
def show_info():
    """Display information about the scraper."""
    
    logger.display_banner(f"ArXiv Enhanced Scraper v{config.version}", 
                         "Author: Andrea Ladiana <ladianaandrea7@gmail.com>")
    
    logger.info("\n[bold]Configuration:[/bold]")
    
    # Display download settings
    logger.info("\n[bold]Download Settings:[/bold]")
    logger.info(f"Download Directory: {config.download.download_dir}")
    logger.info(f"Database Path: {config.download.jsonl_path}")
    logger.info(f"Cache Directory: {config.download.cache_dir}")
    logger.info(f"Default Articles: {config.download.total_articles}")
    logger.info(f"Max Concurrent Downloads: {config.download.max_concurrent_downloads}")
    
    # Display API settings
    logger.info("\n[bold]API Settings:[/bold]")
    logger.info(f"API Base URL: {config.api.api_base_url}")
    logger.info(f"Rate Limit: {config.api.rate_limit} seconds")
    
    # Display category counts
    logger.info("\n[bold]Available Categories:[/bold]")
    for field, cats in config.categories.group_categories_by_field().items():
        logger.info(f"  {field.title()}: {len(cats)} categories")
    logger.info("\nUse 'arxiv-scraper categories' to list all categories")


@cli.command(name="search")
@click.argument('query')
@click.option('--max-results', '-n', default=10, type=int,
              help='Maximum number of results to return')
@click.option('--categories', '-c', multiple=True,
              help='Filter by categories')
@click.option('--download', '-d', is_flag=True,
              help='Download the search results')
@click.option('--format', type=click.Choice(['source', 'pdf']), default='pdf',
              help='Download format (for use with --download)')
@click.option('--output-dir', default=str(config.download.download_dir),
              help='Directory for downloads (for use with --download)')
def search(query: str, max_results: int, categories: Tuple[str], 
               download: bool, format: str, output_dir: str):
    """Search for articles matching a query."""
    import asyncio
    asyncio.run(_search(query, max_results, categories, download, format, output_dir))

async def _search(query: str, max_results: int, categories: Tuple[str], 
               download: bool, format: str, output_dir: str):
    """Search for articles matching a query."""
    
    logger.info(f"Searching for articles matching: '{query}'")
    
    if categories:
        logger.info(f"Filtering by categories: {', '.join(categories)}")
    
    # Create scraper and search
    async with ArxivScraper() as scraper:
        articles = await scraper.search_articles(
            query=query,
            max_results=max_results,
            categories=list(categories) if categories else None
        )
        
        if not articles:
            logger.info("No matching articles found.")
            return
        
        logger.info(f"Found {len(articles)} matching articles:")
        
        # Display results
        for i, article in enumerate(articles, 1):
            logger.display_article(article.to_display_dict(), i)
        
        # Download if requested
        if download and articles:
            download_path = Path(output_dir)
            download_path.mkdir(parents=True, exist_ok=True)
            
            file_format = FileFormat.PDF if format == 'pdf' else FileFormat.SOURCE
            
            logger.info(f"\nDownloading {len(articles)} articles in {file_format.value} format to {download_path}...")
            
            storage = StorageManager()
            await storage.load_downloaded_ids()
            
            # Create a progress bar
            with logger.create_progress_bar() as progress:
                task_id = progress.add_task(
                    f"Downloading {len(articles)} articles", 
                    total=len(articles)
                )
                
                for i, article in enumerate(articles, 1):
                    result = await scraper.download_article(
                        article=article,
                        download_dir=download_path,
                        format=file_format,
                        downloaded_ids=storage.downloaded_ids
                    )
                    
                    if result.success:
                        await storage.save_download_result(result)
                        logger.success(f"Downloaded {article.arxiv_id}")
                    else:
                        logger.failure(f"Failed to download {article.arxiv_id}: {result.error_message}")
                    
                    progress.update(task_id, advance=1)
            
            logger.success(f"Download complete. Files saved to {download_path}")


@cli.command()
@click.argument('session_id', required=False)
@click.option('--list', 'list_sessions', is_flag=True,
              help='List all available sessions')
@click.option('--errors', is_flag=True,
              help='Show only errors from the session')
def session(session_id: Optional[str], list_sessions: bool, errors: bool):
    """View session information."""
    import asyncio
    asyncio.run(_session(session_id, list_sessions, errors))

async def _session(session_id: Optional[str], list_sessions: bool, errors: bool):
    """View session information."""
    
    storage = StorageManager()
    
    if list_sessions:
        # List all sessions
        sessions = await storage.list_sessions()
        
        if not sessions:
            logger.info("No sessions found.")
            return
            
        logger.info(f"Found {len(sessions)} sessions:")
        
        # Sort by date (newest first)
        sessions.sort(key=lambda s: s.get('duration', 0) or 0, reverse=True)
        
        for i, session_data in enumerate(sessions, 1):
            logger.info(f"\n[bold]{i}. Session {session_data['session_id']}[/bold]")
            logger.info(f"   Target: {session_data['target_count']} articles")
            logger.info(f"   Downloaded: {session_data['downloaded']} of {session_data['found']} found")
            logger.info(f"   Success Rate: {session_data['success_rate']}")
            if session_data.get('errors', 0) > 0:
                logger.info(f"   [bold red]Errors: {session_data['errors']}[/bold red]")
                
        return
    
    if not session_id:
        logger.error("Please specify a session ID or use --list to see all sessions")
        sys.exit(1)
    
    # Load specific session
    session = await storage.load_session(session_id)
    
    if not session:
        logger.error(f"Session not found: {session_id}")
        sys.exit(1)
    
    if errors:
        # Show only errors
        logger.display_error_log(session.errors)
    else:
        # Show full session details
        logger.display_detailed_session(session)


@cli.command()
@click.option('--days', '-d', default=7, type=int,
              help='Cache expiry in days')
def cache(days: int):
    """Manage the cache."""
    import asyncio
    asyncio.run(_cache(days))

async def _cache(days: int):
    """Manage the cache."""
    
    from arxiv_scraper.utils.cache import Cache
    
    cache = Cache(config.download.cache_dir, ttl_days=days)
    
    # Display cache stats
    stats = cache.get_stats()
    
    logger.info("[bold]Cache Statistics:[/bold]")
    logger.info(f"Total Entries: {stats['total_entries']}")
    logger.info(f"Total Size: {stats['total_size_mb']} MB")
    logger.info(f"Cache Directory: {stats['cache_dir']}")
    logger.info(f"TTL: {stats['ttl_days']} days")
    
    if stats['oldest_entry'] and stats['newest_entry']:
        logger.info(f"Oldest Entry: {stats['oldest_entry']}")
        logger.info(f"Newest Entry: {stats['newest_entry']}")
    
    # Clear expired entries
    if stats['total_entries'] > 0:
        if click.confirm("Clear expired cache entries?", default=True):
            cleared = await cache.clear_expired()
            logger.success(f"Cleared {cleared} expired cache entries")
            
            if cleared > 0 and click.confirm("Clear all remaining cache?", default=False):
                cleared = await cache.clear()
                logger.success(f"Cleared all {cleared} cache entries")


def main():
    """Main entry point."""
    try:
        # Set the asyncio event loop policy for Windows if needed
        if sys.platform == 'win32':
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        cli()  # Remove the anyio backend parameter
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        # Remove exc_info parameter which isn't supported
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
