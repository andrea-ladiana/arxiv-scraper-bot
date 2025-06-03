"""Logging utilities for the ArXiv scraper."""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from config import config


class ScraperLogger:
    """Enhanced logger for the ArXiv scraper with rich formatting."""
    
    def __init__(self, name: str = "arxiv_scraper", log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.console = Console()
        self.setup_logging(log_file)
    
    def setup_logging(self, log_file: Optional[str] = None) -> None:
        """Setup logging configuration."""
        self.logger.setLevel(getattr(logging, config.log_level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Rich console handler
        console_handler = RichHandler(
            console=self.console,
            show_path=False,
            rich_tracebacks=True
        )
        console_handler.setFormatter(logging.Formatter(fmt="%(message)s"))
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(config.log_format))
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
    
    def success(self, message: str) -> None:
        """Log success message with green color."""
        self.console.print(f"✓ {message}", style="bold green")
    
    def failure(self, message: str) -> None:
        """Log failure message with red color."""
        self.console.print(f"✗ {message}", style="bold red")
    
    def display_article(self, article_dict: dict, number: int) -> None:
        """Display article information in a formatted way."""
        title = Text(article_dict['title'], style="bold blue")
        authors = ", ".join(article_dict['authors'])
        date = article_dict.get('published_date', 'N/A')
        categories = " | ".join(article_dict.get('categories', []))
        
        self.console.print(f"\n{number}. {title}")
        self.console.print(f"   Authors: {authors}", style="dim")
        self.console.print(f"   Date: {date}", style="dim")
        self.console.print(f"   Categories: {categories}", style="dim")
        if article_dict.get('link'):
            self.console.print(f"   Link: {article_dict['link']}", style="dim blue")
    
    def display_session_summary(self, session_data: dict) -> None:
        """Display session summary in a formatted table."""
        table = Table(title="Scraping Session Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        table.add_row("Session ID", session_data['session_id'])
        table.add_row("Duration", f"{session_data['duration']:.2f}s" if session_data['duration'] else "N/A")
        table.add_row("Categories", " | ".join(session_data['categories']))
        table.add_row("Target Count", str(session_data['target_count']))
        table.add_row("Articles Found", str(session_data['found']))
        table.add_row("Articles Downloaded", str(session_data['downloaded']))
        table.add_row("Articles Skipped", str(session_data['skipped']))
        table.add_row("Success Rate", session_data['success_rate'])
        table.add_row("Errors", str(session_data['errors']))
        
        self.console.print(table)
    
    def create_progress_bar(self, description: str = "Processing") -> Progress:
        """Create a rich progress bar."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
    
    def display_banner(self, title: str, subtitle: str = "") -> None:
        """Display a banner with title and subtitle."""
        content = f"[bold blue]{title}[/bold blue]"
        if subtitle:
            content += f"\n[dim]{subtitle}[/dim]"
        
        panel = Panel(
            content,
            style="bold blue",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def display_config(self, config_dict: dict) -> None:
        """Display configuration in a formatted way."""
        table = Table(title="Configuration", show_header=True, header_style="bold yellow")
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        
        for key, value in config_dict.items():
            if isinstance(value, list):
                value = f"{len(value)} items"
            table.add_row(key.replace('_', ' ').title(), str(value))
        
        self.console.print(table)


# Global logger instance
logger = ScraperLogger()
