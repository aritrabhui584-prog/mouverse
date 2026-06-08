#!/usr/bin/env python3
"""
Movie Poster URL Enrichment Script

Reads movies.csv and enriches it with poster URLs from TMDB.
Features:
- Caches results to avoid repeated TMDB searches
- Skips duplicate titles
- Logs failures
- Uses null for movies without posters
"""

import csv
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
INPUT_CSV = "database/movies.csv"
OUTPUT_CSV = "database/movies_enriched.csv"
CACHE_FILE = "database/tmdb_cache.json"
LOG_FILE = "database/poster_enrichment.log"
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if TMDB_API_KEY == "your_tmdb_api_key_here" or not TMDB_API_KEY:
    TMDB_API_KEY = None
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
if OMDB_API_KEY == "your_omdb_api_key_here" or not OMDB_API_KEY:
    OMDB_API_KEY = None
    logger.warning("OMDB_API_KEY not configured. Poster enrichment will be skipped.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TMDBCache:
    """Cache for TMDB search results to avoid repeated API calls."""
    
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from file if it exists."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached entries from {self.cache_file}")
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
                self.cache = {}
    
    def save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.cache)} entries to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get(self, title: str) -> Optional[Dict[str, Any]]:
        """Get cached result for a movie title."""
        return self.cache.get(title)
    
    def set(self, title: str, data: Dict[str, Any]):
        """Cache result for a movie title."""
        self.cache[title] = data


def search_tmdb_movie(title: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Search TMDB for a movie by title.
    
    Returns:
        Dict with movie_id and poster_path if found, None otherwise.
    """
    try:
        url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            "api_key": api_key,
            "query": title,
            "language": "en-US",
            "page": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("results") and len(data["results"]) > 0:
            # Get the first result (most relevant)
            movie = data["results"][0]
            return {
                "movie_id": movie.get("id"),
                "poster_path": movie.get("poster_path"),
                "source": "tmdb"
            }
        else:
            logger.warning(f"No TMDB results found for: {title}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"TMDB API error for '{title}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching for '{title}': {e}")
        return None


def search_omdb_movie(title: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Search OMDB for a movie by title (fallback).
    
    Returns:
        Dict with poster_url if found, None otherwise.
    """
    try:
        url = f"http://www.omdbapi.com/"
        params = {
            "apikey": api_key,
            "t": title
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("Response") == "True":
            poster = data.get("Poster")
            if poster and poster != "N/A":
                return {
                    "movie_id": data.get("imdbID"),
                    "poster_path": poster,  # OMDB returns full URL
                    "source": "omdb"
                }
        else:
            logger.warning(f"No OMDB results found for: {title}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"OMDB API error for '{title}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching OMDB for '{title}': {e}")
        return None


def generate_poster_url(poster_path: Optional[str], source: str = "tmdb") -> Optional[str]:
    """
    Generate full poster URL from poster_path.
    
    Returns:
        Full URL if poster_path exists, None otherwise.
    """
    if not poster_path:
        return None
    
    if source == "omdb":
        # OMDB returns full URLs directly
        return poster_path
    else:
        # TMDB returns relative paths that need the base URL
        return f"{TMDB_IMAGE_BASE_URL}{poster_path}"


def read_movies_csv(csv_path: str) -> list:
    """Read movies from CSV file."""
    movies = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                movies.append(row)
        logger.info(f"Read {len(movies)} movies from {csv_path}")
        return movies
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        raise


def write_enriched_csv(csv_path: str, movies: list):
    """Write enriched movies to CSV file."""
    try:
        fieldnames = [
            "title", "genre", "language", "region", "runtime", 
            "rating", "mood_tags", "poster_url"
        ]
        
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(movies)
        
        logger.info(f"Wrote {len(movies)} movies to {csv_path}")
    except Exception as e:
        logger.error(f"Error writing CSV: {e}")
        raise


def enrich_movies():
    """Main enrichment function."""
    logger.info("=" * 60)
    logger.info("Starting movie poster enrichment")
    logger.info("=" * 60)
    
    # Log API status
    if TMDB_API_KEY:
        logger.info("TMDB API key: Available")
    else:
        logger.info("TMDB API key: Not available (will use OMDB fallback)")
    
    if OMDB_API_KEY:
        logger.info("OMDB API key: Available")
    else:
        logger.warning("OMDB API key: Not available")
    
    # Initialize cache
    cache = TMDBCache(CACHE_FILE)
    
    # Read input CSV
    movies = read_movies_csv(INPUT_CSV)
    
    # Track statistics
    stats = {
        "total": len(movies),
        "cached": 0,
        "found": 0,
        "not_found": 0,
        "errors": 0,
        "duplicates": 0
    }
    
    # Track processed titles to skip duplicates
    processed_titles = set()
    
    # Enrich each movie
    for i, movie in enumerate(movies, 1):
        title = movie["title"]
        
        # Skip duplicates
        if title in processed_titles:
            logger.info(f"[{i}/{stats['total']}] Skipping duplicate: {title}")
            stats["duplicates"] += 1
            movie["poster_url"] = None
            continue
        
        processed_titles.add(title)
        
        # Check cache first
        cached_result = cache.get(title)
        if cached_result:
            logger.info(f"[{i}/{stats['total']}] Cache hit for: {title}")
            source = cached_result.get("source", "tmdb")
            poster_url = generate_poster_url(cached_result.get("poster_path"), source)
            movie["poster_url"] = poster_url
            stats["cached"] += 1
            if poster_url:
                stats["found"] += 1
            else:
                stats["not_found"] += 1
            continue
        
        # Search TMDB first, then OMDB as fallback
        logger.info(f"[{i}/{stats['total']}] Searching for: {title}")
        
        tmdb_result = None
        omdb_result = None
        final_result = None
        
        # Try TMDB first if API key is available
        if TMDB_API_KEY:
            tmdb_result = search_tmdb_movie(title, TMDB_API_KEY)
            if tmdb_result:
                logger.info(f"  Found on TMDB")
                final_result = tmdb_result
            else:
                logger.info(f"  Not found on TMDB, trying OMDB...")
        
        # Fallback to OMDB if TMDB failed or not available
        if not final_result and OMDB_API_KEY:
            omdb_result = search_omdb_movie(title, OMDB_API_KEY)
            if omdb_result:
                logger.info(f"  Found on OMDB")
                final_result = omdb_result
        
        if final_result:
            # Cache the result
            cache.set(title, final_result)
            
            # Generate poster URL
            source = final_result.get("source", "tmdb")
            poster_url = generate_poster_url(final_result.get("poster_path"), source)
            movie["poster_url"] = poster_url
            
            if poster_url:
                logger.info(f"  Poster URL: {poster_url}")
                stats["found"] += 1
            else:
                logger.info(f"  Movie found but no poster available")
                stats["not_found"] += 1
        else:
            logger.warning(f"  No result found on TMDB or OMDB for: {title}")
            movie["poster_url"] = None
            stats["not_found"] += 1
            stats["errors"] += 1
            
            # Cache the failure to avoid repeated searches
            cache.set(title, {"movie_id": None, "poster_path": None, "source": "none"})
    
    # Save cache
    cache.save_cache()
    
    # Write enriched CSV
    write_enriched_csv(OUTPUT_CSV, movies)
    
    # Print statistics
    logger.info("=" * 60)
    logger.info("Enrichment complete")
    logger.info("=" * 60)
    logger.info(f"Total movies: {stats['total']}")
    logger.info(f"Cached results: {stats['cached']}")
    logger.info(f"Posters found: {stats['found']}")
    logger.info(f"Posters not found: {stats['not_found']}")
    logger.info(f"API errors: {stats['errors']}")
    logger.info(f"Duplicates skipped: {stats['duplicates']}")
    logger.info(f"Output file: {OUTPUT_CSV}")
    logger.info(f"Cache file: {CACHE_FILE}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("=" * 60)


if __name__ == "__main__":
    enrich_movies()
