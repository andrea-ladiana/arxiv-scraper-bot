"""
Enhanced logging utilities for the ArXiv scraper.

This module provides a rich logging system with console output,
file logging, and fancy formatting using the rich library.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Import from core after it's fully loaded
# (to avoid circular imports)
from arxiv_scraper.core.config import config


class ScraperLogger:
    """Enhanced logger for the ArXiv scraper with rich formatting."""
    
    def __init__(self, name: str = "arxiv_scraper"):
        """Initialize the logger."""
        self.logger = logging.getLogger(name)
        
        # Setup rich console with a custom theme
        theme = Theme({
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "title": "bold blue",
            "progress.percentage": "cyan",
            "progress.remaining": "green",
            "progress.download": "cyan",
            "progress.complete": "bold green",
        })
        
        self.console = Console(theme=theme)
        self.setup_logging()
    
    def setup_logging(self, log_file: Optional[Path] = None) -> None:
        """Setup logging configuration."""
        if not log_file and config.logging.log_file:
            log_file = config.logging.log_file
            
        # Set log level from config
        log_level = getattr(logging, config.logging.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler with rich formatting
        if config.logging.log_to_console:
            console_handler = RichHandler(
                console=self.console,
                show_path=False,
                rich_tracebacks=config.logging.rich_traceback,
                tracebacks_show_locals=config.logging.rich_traceback,
                markup=True
            )
            console_handler.setFormatter(logging.Formatter("%(message)s"))
            console_handler.setLevel(log_level)
            self.logger.addHandler(console_handler)
        
        # File handler if requested
        if config.logging.log_to_file and log_file:
            # Ensure directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(config.logging.log_format))
            file_handler.setLevel(log_level)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)
    
    def success(self, message: str) -> None:
        """Log success message with green color."""
        self.console.print(f"✓ {message}", style="success")
    
    def failure(self, message: str) -> None:
        """Log failure message with red color."""
        self.console.print(f"✗ {message}", style="error")
    
    def display_article(self, article_dict: Dict[str, Any], number: int = None) -> None:
        """Display article information in a formatted way."""
        title = Text(article_dict['title'], style="bold blue")
        
        # Format number if provided
        num_prefix = f"{number}. " if number is not None else ""
        
        authors = ", ".join(article_dict['authors']) if article_dict.get('authors') else "Unknown"
        date = article_dict.get('published_date', 'N/A')
        categories = " | ".join(article_dict.get('categories', [])) if article_dict.get('categories') else "Uncategorized"
        
        self.console.print(f"\n{num_prefix}{title}")
        self.console.print(f"   Authors: {authors}", style="dim")
        self.console.print(f"   Date: {date}", style="dim")
        self.console.print(f"   Categories: {categories}", style="dim")
        if article_dict.get('link'):
            self.console.print(f"   Link: {article_dict['link']}", style="dim blue")
    
    def display_session_summary(self, session_data: Dict[str, Any]) -> None:
        """Display session summary in a formatted table."""
        table = Table(title="Scraping Session Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        # Add rows for each metric
        for key, value in session_data.items():
            # Format specific fields
            if key == 'duration' and value is not None:
                value = f"{value:.2f}s"
            elif key == 'categories' and isinstance(value, list):
                if len(value) > 3:
                    value = f"{len(value)} categories"
                else:
                    value = " | ".join(value)
                    
            # Format field name
            display_key = key.replace('_', ' ').title()
            table.add_row(display_key, str(value))
        
        self.console.print(table)
        
        # Add error summary if there are any
        if session_data.get('errors', 0) > 0:
            self.console.print(f"\n[bold red]Errors: {session_data['errors']}[/bold red]")
            self.console.print("Run 'arxiv-scraper session errors <session_id>' for details")
    
    def display_detailed_session(self, session: Any) -> None:
        """Display detailed session information."""
        # This will be implemented with the actual session object
        self.console.print(Panel(
            f"[bold]Session ID:[/bold] {session.session_id}\n"
            f"[bold]Start Time:[/bold] {session.start_time.isoformat()}\n"
            f"[bold]End Time:[/bold] {session.end_time.isoformat() if session.end_time else 'Not finished'}\n"
            f"[bold]Duration:[/bold] {session.duration:.2f}s\n" if session.duration else "",
            title="Session Details",
            border_style="blue"
        ))
        
        # Display targets
        self.console.print("\n[bold]Targets:[/bold]")
        self.console.print(f"  Categories: {len(session.target_categories)} categories")
        self.console.print(f"  Target Count: {session.target_count} articles")
        
        # Display results
        self.console.print("\n[bold]Results:[/bold]")
        self.console.print(f"  Articles Found: {session.articles_found}")
        self.console.print(f"  Articles Downloaded: {session.articles_downloaded}")
        self.console.print(f"  Articles Skipped: {session.articles_skipped}")
        self.console.print(f"  Success Rate: {session.success_rate:.1f}%")
        
        # Display errors if any
        if session.errors:
            self.console.print("\n[bold red]Errors:[/bold red]")
            for i, error in enumerate(session.errors, 1):
                self.console.print(f"  {i}. {error}", style="red")
    
    def create_progress_bar(self, description: str = "Processing") -> Progress:
        """Create a rich progress bar."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            "{task.completed}/{task.total}",
            console=self.console
        )
    
    def display_banner(self, title: str, subtitle: str = "") -> None:
        """Display a banner with title and subtitle."""
        content = f"[title]{title}[/title]"
        if subtitle:
            content += f"\n[dim]{subtitle}[/dim]"
        
        panel = Panel(
            content,
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def display_config(self, config_dict: Dict[str, Any]) -> None:
        """Display configuration in a formatted way."""
        table = Table(title="Configuration", show_header=True, header_style="bold yellow")
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        
        for key, value in config_dict.items():
            if isinstance(value, list):
                value = f"{len(value)} items"
            elif isinstance(value, dict):
                value = f"{len(value)} entries"
                
            display_key = key.replace('_', ' ').title()
            table.add_row(display_key, str(value))
        
        self.console.print(table)
    
    def display_error_log(self, errors: List[str]) -> None:
        """Display a list of errors."""
        if not errors:
            self.console.print("[green]No errors recorded.[/green]")
            return
            
        self.console.print(f"[bold red]Errors ({len(errors)}):[/bold red]")
        for i, error in enumerate(errors, 1):
            self.console.print(f"{i}. {error}", style="red")
    
    def display_storage_stats(self, stats: Dict[str, Any]) -> None:
        """Display storage statistics."""
        table = Table(title="Storage Statistics", show_header=True, header_style="bold yellow")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        
        for key, value in stats.items():
            if key == 'formats' and isinstance(value, dict):
                formats_str = ", ".join(f"{k}: {v}" for k, v in value.items())
                table.add_row("Formats", formats_str)
            else:
                display_key = key.replace('_', ' ').title()
                table.add_row(display_key, str(value))
                
        self.console.print(table)


# Global logger instance
logger = ScraperLogger()
