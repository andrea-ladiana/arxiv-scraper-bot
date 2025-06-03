FROM python:3.11-slim

LABEL maintainer="Your Name <your.email@example.com>"
LABEL version="3.0.0"
LABEL description="Enhanced ArXiv Scraper with async support, caching, and advanced features"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better cache utilization
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create directories for data
RUN mkdir -p /data/downloads /data/cache /data/logs

# Set environment variables for paths
ENV DEFAULT_DOWNLOAD_DIR=/data/downloads \
    DEFAULT_CACHE_DIR=/data/cache \
    DEFAULT_JSONL_PATH=/data/downloaded_ids.jsonl \
    LOG_FILE=/data/logs/arxiv_scraper.log \
    LOG_TO_FILE=true

# Create a non-root user
RUN groupadd -g 1000 arxivuser && \
    useradd -u 1000 -g arxivuser -s /bin/bash -m arxivuser && \
    chown -R arxivuser:arxivuser /app /data

# Switch to non-root user
USER arxivuser

# Make the entry point executable
RUN chmod +x /app/arxiv_scraper.py

# Set entry point
ENTRYPOINT ["python", "/app/arxiv_scraper.py"]

# Default command
CMD ["--help"]
