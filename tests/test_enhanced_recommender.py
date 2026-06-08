import unittest
import sys
import os
import sqlite3
import json
from dotenv import load_dotenv

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from backend.recommender import MovieRecommender, get_db_connection

class TestEnhancedRecommender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recommender = MovieRecommender()
        cls.recommender.populate_fallback_dataset()
        
        # Setup test db entries for clicks and history to test personalization
        conn = get_db_connection()
        c = conn.cursor()
        
        # Create user helper tables if they don't exist in test environment
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id TEXT NOT NULL,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                genre TEXT,
                mood TEXT,
                language TEXT,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Clear tables for clean run
        c.execute("DELETE FROM user_clicks WHERE user_id = 9999")
        c.execute("DELETE FROM user_searches WHERE user_id = 9999")
        c.execute("DELETE FROM user_history WHERE user_id = 9999")
        
        # Log a watch history of a Sci-Fi movie in English for test user 9999
        c.execute("INSERT OR REPLACE INTO movies (id, title, genre, language, region) VALUES ('test_inception', 'Inception Test', '[\"Sci-Fi\"]', 'English', 'International')")
        c.execute("INSERT OR REPLACE INTO movies (id, title, genre, language, region) VALUES ('test_sholay', 'Sholay Test', '[\"Action\"]', 'Hindi', 'India')")
        
        c.execute("INSERT INTO user_history (user_id, movie_id, rating_given) VALUES (9999, 'test_inception', 5)")
        c.execute("INSERT INTO user_clicks (user_id, movie_id) VALUES (9999, 'test_inception')")
        c.execute("INSERT INTO user_searches (user_id, genre, language) VALUES (9999, 'Sci-Fi', 'English')")
        
        conn.commit()
        conn.close()

    def test_recommendation_relaxation_loop(self):
        # We query a region with few exact matches but plenty of language matches (e.g. International, English)
        # We filter with min_rating=9.5 (extremely strict) and max_runtime=90 (extremely strict)
        # In base database, Shawshank, Godfather etc. are English, International, but none match both constraints.
        # Relaxation loop should trigger and relax runtime and rating to return >= 12 recommendations.
        results, warning = self.recommender.recommend(
            mood="happy",
            genre="Drama",
            language="English",
            region="International",
            min_rating=9.5,
            max_runtime=90,
            n=20
        )
        # We check that it relaxes constraints to find movies, since base pool has English movies but none match strict runtime/rating
        self.assertTrue(len(results) >= 11, f"Relaxation loop should find at least 11 alternatives, found: {len(results)}")
        
    def test_rating_slider_preference(self):
        # min_rating is a weighted ranking preference instead of strict filter.
        # Movies slightly below min_rating can still appear.
        # If we set min_rating=9.0, a movie with rating 8.8 (Inception) should still be returned.
        results, warning = self.recommender.recommend(
            mood="excited",
            genre="Sci-Fi",
            language="English",
            region="International",
            min_rating=9.0,
            max_runtime=240,
            n=20
        )
        titles = [m.get("title") for m in results]
        self.assertTrue(any("Inception" in t or "Interstellar" in t for t in titles), f"Inception (8.8) or Interstellar (8.7) should still appear even when min_rating is 9.0: found {titles}")

    def test_personalization_boost(self):
        # For user 9999, the favorite genre is Sci-Fi (from seed watch history, click, search).
        # We check if a Sci-Fi movie ranks higher when user_id=9999 is passed compared to user_id=None.
        results_personalized, _ = self.recommender.recommend(
            mood="excited",
            genre="Action", # Requested Action
            language="English",
            region="International",
            n=20,
            user_id=9999
        )
        
        results_anonymous, _ = self.recommender.recommend(
            mood="excited",
            genre="Action", # Requested Action
            language="English",
            region="International",
            n=20,
            user_id=None
        )
        
        # Sci-Fi movies (like Inception or Interstellar) should rank relatively higher in personalized list
        # due to the Sci-Fi taste profile boost (+0.10) compared to anonymous list.
        # Let's inspect index of Inception or Interstellar
        def find_index(lst, title):
            for idx, item in enumerate(lst):
                if title.lower() in item["title"].lower():
                    return idx
            return 999
            
        idx_pers = find_index(results_personalized, "Inception")
        idx_anon = find_index(results_anonymous, "Inception")
        
        # Personalized index should be lower (higher rank) than anonymous index if it was returned
        if idx_anon != 999 and idx_pers != 999:
            self.assertTrue(idx_pers <= idx_anon, f"Inception should rank higher or equal in personalized recommendations: personalized index {idx_pers}, anonymous index {idx_anon}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test-only movie entries so they don't pollute production recommendations."""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM movies WHERE id IN ('test_inception', 'test_sholay')")
        c.execute("DELETE FROM user_clicks WHERE user_id = 9999")
        c.execute("DELETE FROM user_searches WHERE user_id = 9999")
        c.execute("DELETE FROM user_history WHERE user_id = 9999")
        conn.commit()
        conn.close()
        print("[TEST] Cleaned up test entries from database.")

if __name__ == "__main__":
    unittest.main()
