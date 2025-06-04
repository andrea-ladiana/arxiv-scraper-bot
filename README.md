# ArXiv Enhanced Scraper

A robust, async-powered scraper for downloading ArXiv articles with advanced error handling, rate limiting, and comprehensive logging.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-3.0.0-orange)

## Features

- **Asynchronous Processing**: Utilizes Python's asyncio for efficient, concurrent downloads
- **Multiple Download Formats**: Download papers in both PDF and source (tar.gz) formats
- **Robust Error Handling**: Comprehensive error handling with automatic retries and exponential backoff
- **Rate Limiting**: Respects ArXiv's rate limits to avoid being blocked
- **Comprehensive Logging**: Detailed logs with rich terminal output
- **Caching System**: Local cache for API responses to improve performance and reduce API load
- **Command-Line Interface**: Intuitive CLI with numerous options
- **Category Filtering**: Filter articles by field or specific categories
- **Session Management**: Track and resume download sessions
- **Metadata Export**: Export article metadata in JSON or BibTeX formats
- **Docker Support**: Easy deployment with Docker

## Installation

### From PyPI

```bash
pip install arxiv-scraper
```

### From Source

```bash
git clone https://github.com/yourusername/arxiv-scraper.git
cd arxiv-scraper
pip install -e .
```

### Build Package

Create the source distribution and wheel for publishing to PyPI:

```bash
python -m build
```

### Using Docker

```bash
docker pull yourusername/arxiv-scraper
```

Or build from source:

```bash
git clone https://github.com/yourusername/arxiv-scraper.git
cd arxiv-scraper
docker-compose build
```

## Configuration

ArXiv Scraper can be configured via environment variables, command-line options, or a .env file. Here are the main configuration options:

### Environment Variables

```
# Download settings
DEFAULT_DOWNLOAD_DIR=./downloads
DEFAULT_JSONL_PATH=./downloaded_ids.jsonl
DEFAULT_CACHE_DIR=./cache
DEFAULT_TOTAL_ARTICLES=100
DEFAULT_BATCH_SIZE=10
MAX_CONCURRENT_DOWNLOADS=5

# API settings
ARXIV_API_BASE_URL=http://export.arxiv.org/api/query
ARXIV_SOURCE_BASE_URL=https://arxiv.org/e-print
ARXIV_PDF_BASE_URL=https://arxiv.org/pdf
API_RATE_LIMIT=3.0

# Logging
LOG_LEVEL=INFO
LOG_TO_CONSOLE=true
LOG_TO_FILE=false
LOG_FILE=./logs/arxiv_scraper.log
```

## Usage

### Basic Usage

```bash
# Download 10 PDF articles from CS categories
arxiv-scraper scrape --field cs --total 10 --format pdf

# Download 5 articles from specific categories
arxiv-scraper scrape --categories cs.AI math.CO --total 5

# Search for articles and download them
arxiv-scraper search "quantum computing" --max-results 5 --download
```

### Advanced Usage

```bash
# Download articles with custom settings
arxiv-scraper scrape --field physics --total 20 --download-dir ./physics_papers --format both --max-concurrent 8

# Export metadata to JSON and BibTeX
arxiv-scraper scrape --field math --total 15 --export-metadata --export-bibtex

# View and manage sessions
arxiv-scraper session --list
arxiv-scraper session SESSION_ID --errors

# Clean up old downloads
arxiv-scraper cleanup --days-old 30
```

### Docker Usage

```bash
docker run -v "$(pwd)/data:/data" yourusername/arxiv-scraper scrape --field cs --total 10

# Or with docker-compose
docker-compose up
```

### GUI Application

The project also includes a PyQt6-based graphical interface that exposes all CLI
features. After installing the package with GUI dependencies, launch it with:

```bash
arxiv-scraper-gui
```

The GUI allows you to run scrape, search and other commands through an easy-to-
use interface and view the log output directly in the window.

## Command Reference

- `arxiv-scraper scrape`: Download articles from ArXiv
- `arxiv-scraper search`: Search for articles
- `arxiv-scraper categories`: List available ArXiv categories
- `arxiv-scraper session`: View session information
- `arxiv-scraper stats`: Display statistics about downloaded articles
- `arxiv-scraper cleanup`: Clean up old downloaded files
- `arxiv-scraper cache`: Manage the cache
- `arxiv-scraper info`: Display information about the scraper

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/arxiv-scraper.git
cd arxiv-scraper

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Testing

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Linting

```bash
ruff check .
mypy .
```

## Project Structure

```
arxiv_scraper/
├── core/                 # Core functionality
│   ├── config.py         # Configuration management
│   ├── models.py         # Data models
│   ├── scraping.py       # Scraping functionality
│   └── storage.py        # Storage management
├── cli/                  # Command-line interface
│   └── main.py           # CLI commands
└── utils/                # Utility modules
    ├── cache.py          # Caching system
    └── logger.py         # Logging utilities
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The ArXiv API for providing access to the articles
- All the contributors who have helped to improve this project
