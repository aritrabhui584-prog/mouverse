import pandas as pd
import sqlite3
import os
import logging
from typing import List, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "mouverse.db")
EXTENDED_CSV = os.path.join(BASE_DIR, "database", "movies_extended.csv")

logger = logging.getLogger(__name__)

class ExtendedMovieDataset:
    """
    Extended movie dataset that provides access to the large MOUVERSE_2 dataset
    without interfering with the main curated dataset.
    """
    
    def __init__(self):
        self.extended_movies = None
        self._load_extended_dataset()
    
    def _load_extended_dataset(self):
        """Load the extended movie dataset from CSV"""
        try:
            if os.path.exists(EXTENDED_CSV):
                logger.info("Loading extended movie dataset...")
                self.extended_movies = pd.read_csv(EXTENDED_CSV)
                logger.info(f"Loaded {len(self.extended_movies)} movies from extended dataset")
            else:
                logger.warning(f"Extended dataset not found at {EXTENDED_CSV}")
                self.extended_movies = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading extended dataset: {e}")
            self.extended_movies = pd.DataFrame()
    
    def search_movies(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for movies in the extended dataset by title
        """
        if self.extended_movies.empty:
            return []
        
        try:
            # Simple title search
            mask = self.extended_movies['title'].str.contains(query, case=False, na=False)
            results = self.extended_movies[mask].head(limit)
            
            movies = []
            for _, row in results.iterrows():
                movies.append({
                    'title': row.get('title', ''),
                    'genres': row.get('genres', ''),
                    'movieId': row.get('movieId', ''),
                    'avg_rating': row.get('avg_rating', 0),
                    'rating_count': row.get('rating_count', 0),
                    'tags': row.get('tags', ''),
                    'source': 'extended'
                })
            
            return movies
        except Exception as e:
            logger.error(f"Error searching extended dataset: {e}")
            return []
    
    def get_movies_by_genre(self, genre: str, limit: int = 20) -> List[Dict]:
        """
        Get movies by genre from the extended dataset
        """
        if self.extended_movies.empty:
            return []
        
        try:
            mask = self.extended_movies['genres'].str.contains(genre, case=False, na=False)
            results = self.extended_movies[mask].head(limit)
            
            movies = []
            for _, row in results.iterrows():
                movies.append({
                    'title': row.get('title', ''),
                    'genres': row.get('genres', ''),
                    'movieId': row.get('movieId', ''),
                    'avg_rating': row.get('avg_rating', 0),
                    'rating_count': row.get('rating_count', 0),
                    'tags': row.get('tags', ''),
                    'source': 'extended'
                })
            
            return movies
        except Exception as e:
            logger.error(f"Error getting movies by genre: {e}")
            return []
    
    def get_top_rated(self, limit: int = 20, min_ratings: int = 1) -> List[Dict]:
        """
        Get top-rated movies from the extended dataset
        """
        if self.extended_movies.empty:
            return []
        
        try:
            # Filter by minimum rating count (lowered to 1 for better coverage) and valid titles
            filtered = self.extended_movies[
                (self.extended_movies['rating_count'] >= min_ratings) &
                (self.extended_movies['title'].notna()) &
                (self.extended_movies['title'] != '') &
                (self.extended_movies['avg_rating'] > 0)
            ]
            results = filtered.sort_values('avg_rating', ascending=False).head(limit)
            
            movies = []
            for _, row in results.iterrows():
                movies.append({
                    'title': row.get('title', ''),
                    'genres': row.get('genres', ''),
                    'movieId': row.get('movieId', ''),
                    'avg_rating': row.get('avg_rating', 0),
                    'rating_count': row.get('rating_count', 0),
                    'tags': row.get('tags', ''),
                    'source': 'extended'
                })
            
            return movies
        except Exception as e:
            logger.error(f"Error getting top rated movies: {e}")
            return []
    
    def convert_to_standard_format(self, movie: Dict) -> Dict:
        """
        Convert extended dataset movie format to match the main project format
        """
        # Parse genres from pipe-separated format
        genres_str = movie.get('genres', '')
        # Handle NaN values and non-string types
        if pd.isna(genres_str) or not isinstance(genres_str, str):
            genres = []
        else:
            genres = [g.strip() for g in genres_str.split('|')] if genres_str else []
        
        # Map to mood tags based on genres
        mood_tags = self._genres_to_mood_tags(genres)
        
        return {
            'title': movie.get('title', ''),
            'genre': genres,
            'language': 'English',  # Default since extended dataset doesn't have language
            'region': 'International',  # Default since extended dataset doesn't have region
            'runtime': 120,  # Default average
            'rating': movie.get('avg_rating', 0),
            'mood_tags': mood_tags,
            'poster': '/posters/default-poster.jpg',
            'overview': f"A movie with genres: {', '.join(genres)}",
            'source': 'extended'
        }
    
    def _genres_to_mood_tags(self, genres: List[str]) -> str:
        """
        Convert genres to mood tags (simplified mapping)
        """
        mood_mapping = {
            'Comedy': 'happy funny',
            'Drama': 'sad emotional',
            'Action': 'excited thrilling',
            'Thriller': 'thrilling dark',
            'Romance': 'romantic happy',
            'Horror': 'dark thrilling',
            'Sci-Fi': 'excited motivated',
            'Adventure': 'excited motivated',
            'Animation': 'happy excited',
            'Fantasy': 'happy excited',
            'Crime': 'dark thrilling',
            'Mystery': 'thrilling dark',
            'Children': 'happy funny',
            'Musical': 'happy excited',
            'War': 'dark motivated',
            'Western': 'dark motivated'
        }
        
        moods = []
        for genre in genres:
            if genre in mood_mapping:
                moods.append(mood_mapping[genre])
        
        return ' '.join(moods) if moods else 'excited motivated'

# Singleton instance
extended_dataset = ExtendedMovieDataset()
